import socket
import threading
import os
from sys import exit
import keyboard


# Add a dictionary to map file extensions to MIME types
MIME_TYPES = {
    ".html": "text/html",
    ".js": "application/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf"
}

# Server class to handle HTTP/2 and HTTP/1.1 communication
class Server:
    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port
        self.server_socket = None

    def start(self):
        """Starts the server and listens for incoming connections."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(0.1)
        print(f"HTTP/2 Server running on {self.host}:{self.port}")

        # Listen for client connections
        while True:
            if keyboard.is_pressed('esc'):
                self.server_socket.close()
                exit()
            try: 
                client_socket, client_address = self.server_socket.accept()
                print(f"New connection from {client_address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except socket.timeout:
                pass 


    def handle_client(self, client_socket):
        """Handles the communication with a single client."""
        # Read the first request (this could be either HTTP/2 or HTTP/1.1)
        data = client_socket.recv(4096)
        if not data:
            client_socket.close()
            return

        # Decode Request data
        request = data.decode(errors='ignore').splitlines()
        print(f"\ndata:")
        for item in request:
            print(f"{item}")
        
        # Parse the URL from the request to get the path
        url_path = self.parse_url(data)

        if url_path:  # If the path exists
            self.handle_request(client_socket, url_path)
        else:
            print("Unknown request format.")
            client_socket.close()

    def parse_url(self, data):
        """Extracts the path from the HTTP request (e.g., /index.html)."""
        try:
            request_line = data.decode(errors='ignore').splitlines()[0]  # e.g., "GET /index.html HTTP/1.1"
            method, path, _ = request_line.split()
            print(f"Request Path: {path}")

            # Direct empty path to index html file automatically
            if path == '/':
                path = '/index.html'
            
            return path
        
        except Exception as e:
            print(f"Error parsing URL: {e}")
            return None

    def get_mime_type(self, file_path):
        """Returns the MIME type based on the file extension."""
        _, ext = os.path.splitext(file_path)
        return MIME_TYPES.get(ext, "application/octet-stream")

    def handle_request(self, client_socket, url_path):
        """Handles the request based on the parsed URL path."""
        file_path = url_path[1:]  # Remove leading "/"
        if file_path == "":
            file_path = "index.html"

        if os.path.exists(file_path):
            # Read the file and determine its MIME type
            mime_type = self.get_mime_type(file_path)
            with open(file_path, "rb") as f:
                content = f.read()

            # Send the file with the correct headers
            response = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: {mime_type}\r\n"
                f"Content-Length: {len(content)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode() + content
        else:
            # Send a 404 error if the file is not found
            response = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/html\r\n\r\n"
                "<h1>404 Not Found</h1><p>The requested resource could not be found on this server.</p>"
            ).encode()

        try:
            client_socket.sendall(response)
        except Exception as e:
            print(f"Error sending response: {e}")
        finally:
            client_socket.close()

# Function to start the server
def start_server():
    addr = socket.gethostbyname(socket.gethostname())
    server = Server(addr)
    server.start()

# Start the server in a separate thread (so it runs asynchronously)
if __name__ == '__main__':
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    server_thread.join()