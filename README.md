# Multi-threaded Client-Server

> George Tudor | 18/09/2024

----------------------------

## Overview

This small project is a **client-server** communication using **SSL encryption** with a custom generated key. It uses **TCP** communication over TLS with multi-threading capabilities - each new client will have assigned a separate thread to ensure non-blocking execution

The server is built in `python`, while the client uses `powershell` as the programming language.

## Installation

1. Generate your own certificate and private key:
```
openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes -subj "/CN=localhost"
```
Where:
- `newkey`: generates a new **RSA** key of 4096 bits
- `keyout`: specifies the output file for the generated key (this is the **private** key which you want to keep safe)
- `-out`: specifies the output file for the generated certificate (this is your **public** certificate which can be optionally sent to clients)
- `-days`: the validity of the certification in days
- `-nodes`:  specifies the host to not encrypt the key with a passphrase (useful when no prompts are needed in automation)
- `-subj`: the Subject as it will appear in the generated certificate

2. Run the server:
```bash
python3 server.py
```

3. Run clients (in separate terminals):
```powershell
powershell -ep bypass # Required in order to run powershell scripts
.\client.ps1
```

## Details

The server-client model supports message passing between one another with the following commands available on the server:
- `sessions`: shows active client sessions
- `send <client_id> <message>`: sends a message to the client having `client_id` identifier
