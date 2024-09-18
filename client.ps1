# Define server address and port
$serverAddress = "localhost"
$serverPort = 3391

# Create an SSL TCP client
$sslStream = $null
$tcpClient = New-Object System.Net.Sockets.TcpClient

try {
    $tcpClient.Connect($serverAddress, $serverPort)
    Write-Host "Connected to server."

    # SSL stream creation
    $sslStream = New-Object System.Net.Security.SslStream($tcpClient.GetStream(), $false, 
        { param($sender, $certificate, $chain, $sslPolicyErrors) return $true }, $null)
    
    # Authenticate as client (make sure you have a valid server certificate)
    $sslStream.AuthenticateAsClient($serverAddress)

    # Send and receive data loop
    while ($true) {
		Write-Host "> " -NoNewLine
        $message = Read-Host
        $data = [System.Text.Encoding]::UTF8.GetBytes($message)
        
        if ($message -eq 'exit' -or $message -eq 'quit') {
            Write-Host "Closing connection."
            $exitMessage = [System.Text.Encoding]::UTF8.GetBytes("Client exiting.")
            $sslStream.Write($exitMessage, 0, $exitMessage.Length)
            break
        }

        # Write data to SSL stream
        $sslStream.Write($data, 0, $data.Length)

        # Read server's response
        $buffer = New-Object byte[] 1024
        $bytesRead = $sslStream.Read($buffer, 0, $buffer.Length)
        
        if ($bytesRead -gt 0) {
            $response = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $bytesRead)
            Write-Host "Received from server: $response"
            
            # Handle server shutdown message
            if ($response -match "Server is shutting down") {
                Write-Host "Server is shutting down. Closing connection."
                break
            }
        }
    }
} catch {
    Write-Host "Error: $_"
} finally {
    if ($sslStream -ne $null) {
        try {
            $sslStream.Close()
        } catch {
            Write-Host "Error closing SSL stream: $_"
        }
    }
    if ($tcpClient -ne $null) {
        try {
            $tcpClient.Close()
        } catch {
            Write-Host "Error closing TCP client: $_"
        }
    }
    Write-Host "Connection closed."
}
