import ssl
import socket
import threading
import queue
import sys
import time

SERVER_IP = "localhost"
SERVER_PORT = 3391
# SSL context setup (adjust paths to certfile and keyfile as necessary)
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile="server.crt", keyfile="server.key")

clients = {}  # Dictionary to store client connections and addresses
notification_queue = queue.Queue()  # Queue for sending notifications to the main thread
stop_event = threading.Event()

# Function to handle client communication
def handle_client(conn, addr, client_id, stop_event):
    notification_queue.put(f"[New Connection] Client {client_id} connected from {addr}")
    try: 
        with conn:
            while not stop_event.is_set():
                data = conn.recv(1024)
                if not data:
                    notification_queue.put(f"[Client Disconnected] Client {client_id} disconnected.")
                    break
                # Echo the received message back to the client
                notification_queue.put(f"[New Message] Client {client_id}: {data.decode('utf-8')}")
                conn.sendall(f"[SERVER] I got: {data.decode('utf-8')}".encode('utf-8'))
    except Exception as e:
        notification_queue.put(f"[Error Connection with Client {client_id} closed unexpectedly: {e}")
    finally:
        with open('debug.log','w') as f:
            f.write(repr(conn))
        # Remove the client from tracking
        with threading.Lock():
            if client_id in clients:
                try:
                    clients[client_id]['connection'].shutdown(socket.SHUT_RDWR)
                    clients[client_id]['connection'].close()
                except Exception as e:
                    pass
                finally:
                    try:
                        if not stop_event.is_set():
                            del clients[client_id] 
                    except Exception as e:
                        pass
        notification_queue.put(f"[Cleanup] Client {client_id} removed.")


# Function to handle server commands and notifications
def process_notifications(stop_event):
    while not stop_event.is_set():
        # Continuously check the notification queue and print messages if available
        if not notification_queue.empty():
            try:
                while not notification_queue.empty():
                    message = notification_queue.get_nowait()
                    # Print the notification and re-display the prompt
                    sys.stdout.write('\r\n' + message + '\r\n')
                    sys.stdout.write("> ")  # Redisplay the prompt
                    sys.stdout.flush()
            except queue.Empty:
                pass
        time.sleep(0.02)  # Small sleep to avoid high CPU usage
        
def notify_clients_of_shutdown():
    shutdown_message = "Server is shutting down"
    with threading.Lock():
        for client_id, client_session in clients.items():
            try:
                client_session['connection'].sendall(shutdown_message.encode('utf-8'))
            except Exception as e:
                notification_queue.put(f"[Error] Failed to send shutdown message to Client {client_id}: {e}")
            finally:
                try:
                    client_session['connection'].shutdown(socket.SHUT_RDWR)
                    client_session['connection'].close()
                except Exception as e:
                    pass


def send_message(cmd):
    parts = cmd.split(" ", 2)
    if len(parts) < 3:
        print("Invalid command format")
    else:
        command = parts[0]
        client_id = parts[1]
        message = parts[2]

    if client_id == "0":
        for client_session in clients.values():
            try:
                client_session['connection'].sendall(message.encode('utf-8'))
            except socket.error as e:
                print(f"Error sending to client {client_session['client_id']}: {e}")
    else:
        target_client_id = int(client_id)
        target_client_session = clients[target_client_id]['connection']
        target_client_session.sendall(("[SERVER] " + message).encode('utf-8'))

def server_console(stop_event):
    current_input = ""
    print("> ", end="", flush=True)
    
    while not stop_event.is_set():

        # Handle user input
        try:
            char = sys.stdin.read(1)
            if char == '\n':
                # Command entered
                cmd = current_input
                current_input = ""
                
                if cmd == "sessions" or cmd.startswith("sessio"):  # List all connected clients
                    print("[Connected Clients]:")
                    for client_id, info in clients.items():
                        print(f"Client {client_id}: {info['ip_address']}")
                elif cmd == "send" or cmd.startswith("send "): # Send messages
                    send_message(cmd)
                elif cmd == "exit" or cmd.startswith("ex"):  # Stop the server
                    print("Shutting down the server...")
                    stop_event.set()
                    notify_clients_of_shutdown() # Notify all clients of the shutdown
                    break
                elif cmd == "":
                    pass
                else:
                    print(f"Unknown command: {cmd}")
                
                # Reprint prompt after command execution
                sys.stdout.write("> ")
                sys.stdout.flush()
            else:
                # Add the character to the current input
                current_input += char
        
        except (KeyboardInterrupt, EOFError):  # Handle Ctrl+C or EOF to stop server gracefully
            print("\nShutting down the server...")
            stop_event.set()
            notify_clients_of_shutdown()
            break
    print(threading.current_thread())
    print("[C] Closing thread")

# Function to accept new connections
def accept_connections(secure_sock, stop_event):
    client_id = 1
    while not stop_event.is_set():
        try:
            conn, addr = secure_sock.accept()  # Accept a new client connection
            clients[client_id] = {'connection': conn, 'ip_address': addr, 'client_id': client_id, 'thread': None}  # Store the connection

            # Start a new thread for the client and track it
            client_thread = threading.Thread(target=handle_client, args=(conn, addr, client_id, stop_event), daemon=False)
            with threading.Lock():
                clients[client_id]['thread'] = client_thread
            client_thread.start()
            client_id += 1
        except socket.error:
            if stop_event.is_set():
                break
    for client_session in clients.values():
        client_session['thread'].join()


# Main server function
def start_server():
    global stop_event
    stop_event.clear()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
            sock.bind((SERVER_IP, SERVER_PORT))
            sock.listen(10)
            with context.wrap_socket(sock, server_side=True) as secure_sock:
                print(f"Server is running and accepting connections on ({SERVER_IP},{SERVER_PORT})...")

                # Start a thread for accepting connections
                accept_thread = threading.Thread(target=accept_connections, args=(secure_sock,stop_event,), daemon=False)
                accept_thread.start()

                # Start a thread for handling server commands
                console_thread = threading.Thread(target=server_console, args=(stop_event,), daemon=False)
                console_thread.start()

                # Start the server console for commands and notifications
                process_notifications(stop_event)

    except KeyboardInterrupt:
        print("\nServer interrupted by user!")
    finally:
        stop_event.set() # Signal to stop all threads

        # Ensuring all sockets are closed (some might not get closed automatically because their thread was abruptly closed)

        notify_clients_of_shutdown()

        # Ensuring all threads are joined into the main thread
        accept_thread.join()
        console_thread.join()

        sys.exit(0)
if __name__ == "__main__":
    start_server()