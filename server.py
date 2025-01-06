import socket
import threading
import os
import hashlib
from sys import exit
import keyboard
from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import RequestReceived, DataReceived, StreamEnded

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

def parse_url(data):
    try:
        request_line = data.decode(errors='ignore').splitlines()[0]
        method, path, _ = request_line.split()
        if path == '/badRequestPath':
            return None
        if path == '/':
            path = '/index.html'
        return path
    except Exception as e:
        print(f"Error parsing URL: {e}")
        return None

def get_mime_type(file_path):
    _, ext = os.path.splitext(file_path)
    return MIME_TYPES.get(ext, "application/octet-stream")

def get_last_modified(file_path):
    timestamp = os.path.getmtime(file_path)
    return f"{timestamp:.0f}"

def generate_etag(content):
    return hashlib.md5(content).hexdigest()

class Server:
    def __init__(self, host='127.0.0.1', port=80):
        self.host = host
        self.port = port
        self.server_socket = None
        self.file_cache = {}

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"HTTP Server running on {self.host}:{self.port}")

        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"New connection from {client_address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except Exception:
                pass

    def handle_client(self, client_socket):
        data = client_socket.recv(4096)
        if not data:
            client_socket.close()
            return

        if data.startswith(b"PRI * HTTP/2.0"):
            self.handle_http2(client_socket, data)
        else:
            self.handle_http1(client_socket, data)

    def handle_http1(self, client_socket, data):
        request = data.decode(errors='ignore').splitlines()
        print("\nHTTP/1.1 Request:")
        for item in request:
            print(item)

        request_type = request[0].split()[0]
        if request_type == 'GET':
            url_path = parse_url(data)
            if url_path:
                self.handle_http1_request(client_socket, url_path)
            else:
                self.send_http1_error(client_socket, 400, "Bad Request")

        elif request_type == 'POST':
            posted_data = request[-1].split("&")
            posted_data = [item.split("=") for item in posted_data]
            print(f"Received POST data: {posted_data}")
            self.send_http1_error(client_socket, 200, "Posted!")

    def handle_http1_request(self, client_socket, url_path):
        file_path = url_path.lstrip('/')

        if file_path in self.file_cache:
            error_code = "304 Not Modified"
            mime_type = get_mime_type(file_path)
            content, headers = self.file_cache[file_path]

            response = f"HTTP/1.1 {error_code}\r\n"
            response += f"Content-Type: {mime_type}\r\n"
            for key, value in headers.items():
                response += f"{key}: {value}\r\n"
            response += "Connection: close\r\n\r\n"
            client_socket.sendall(response.encode())

        elif os.path.exists(file_path):
            error_code = "200 OK"
            mime_type = get_mime_type(file_path)

            with open(file_path, 'rb') as f:
                content = f.read()
                headers = {
                    "Last-Modified": get_last_modified(file_path),
                    "ETag": generate_etag(content),
                }

                self.file_cache[file_path] = (content, headers)

            response = (
                f"HTTP/1.1 {error_code}\r\n"
                f"Content-Type: {mime_type}\r\n"
                f"Content-Length: {len(content)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode() + content
            client_socket.sendall(response)

        else:
            self.send_http1_error(client_socket, 404, "Not Found")

    def send_http1_error(self, client_socket, status_code, message):
        response = (
            f"HTTP/1.1 {status_code} {message}\r\n"
            f"Content-Type: text/plain\r\n"
            f"Connection: close\r\n\r\n"
            f"{message}"
        ).encode()
        client_socket.sendall(response)
        client_socket.close()

    def handle_http2(self, client_socket, initial_data):
        print("\nInitializing HTTP/2 Connection")
        config = H2Configuration(client_side=False)
        h2_connection = H2Connection(config=config)
        h2_connection.initiate_connection()
        client_socket.sendall(h2_connection.data_to_send())
        print("Sent HTTP/2 Preface")

        h2_connection.receive_data(initial_data)
        streams_data = {}

        while True:
            try:
                data = client_socket.recv(4096)
                if not data:
                    print("Client disconnected or no more data.")
                    break
                events = h2_connection.receive_data(data)
                for event in events:
                    if isinstance(event, RequestReceived):
                        print("\nHTTP/2 Request:")
                        headers = {k: v for k, v in event.headers}
                        path = headers.get(':path', '/')
                        method = headers.get(':method', 'GET')
                        priority = headers.get(':priority', None)
                        print(f"HTTP/2 Request Path: {path}")

                        if priority:
                            print(f"Stream Priority: {priority}")

                        if method == 'GET':
                            self.handle_http2_request(h2_connection, event.stream_id, path, method)
                        elif method == 'POST':
                            streams_data[event.stream_id] = b''

                    elif isinstance(event, DataReceived):
                        if event.stream_id in streams_data:
                            streams_data[event.stream_id] += event.data

                    elif isinstance(event, StreamEnded):
                        if event.stream_id in streams_data:
                            payload = streams_data.pop(event.stream_id)
                            path = headers.get(':path', '/')
                            self.handle_http2_request(h2_connection, event.stream_id, path, method='POST', payload=payload)

                self.manage_flow_control(h2_connection)

                to_send = h2_connection.data_to_send()
                if to_send:
                    print(f"Sending data to client: {len(to_send)} bytes")
                    client_socket.sendall(to_send)
            except Exception as e:
                print(f"Error in HTTP/2 connection: {e}")
                break

    def handle_http2_request(self, h2_connection, stream_id, path, method='GET', payload=None):
        if stream_id not in h2_connection.streams:
            print(f"Stream {stream_id} already closed or does not exist.")
            return

        if method == "POST":
            if payload is not None:
                print(f"Received POST data for {path}: {payload.decode('utf-8')}")
                response_body = f"Data received successfully for {path}".encode("utf-8")
                h2_connection.send_headers(
                    stream_id,
                    [
                        (":status", "200"),
                        ("content-type", "text/plain"),
                        ("content-length", str(len(response_body))),
                    ]
                )
                h2_connection.send_data(stream_id, response_body)
                h2_connection.end_stream(stream_id)
            else:
                self.send_http2_error(h2_connection, stream_id, 400, "Bad Request")
            return

        if path == '/':
            path = '/index.html'

        file_path = path.lstrip('/')
        if os.path.exists(file_path):
            mime_type = get_mime_type(file_path)
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()

                print(f"Sending headers for {path}")
                h2_connection.send_headers(
                    stream_id,
                    [
                        (":status", "200"),
                        ("content-type", mime_type),
                        ("content-length", str(len(content))),
                    ]
                )
                print(f"Sending data for {path}")
                h2_connection.send_data(stream_id, content)
                h2_connection.end_stream(stream_id)
                print(f"HTTP/2 Response sent for {path} on stream {stream_id}")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                self.send_http2_error(h2_connection, stream_id, 500, "Internal Server Error")
        else:
            print(f"File not found: {file_path}")
            self.send_http2_error(h2_connection, stream_id, 404, "Not Found")

    def manage_flow_control(self, h2_connection):
        for stream_id in h2_connection.streams:
            # Stream-level flow control
            window_size = h2_connection.local_flow_control_window(stream_id)
            connection_window = h2_connection.max_outbound_frame_size
            print(f"Flow control: Stream {stream_id} Window Size: {window_size}, Connection Window Size: {connection_window}")

            if window_size < 1024:
                h2_connection.increment_flow_control_window(65535, stream_id=stream_id)
            if connection_window < 1024:
                h2_connection.increment_flow_control_window(65535)

    def send_http2_error(self, h2_connection, stream_id, status_code, message):
        print(f"Sending HTTP/2 error {status_code}: {message}")
        h2_connection.send_headers(
            stream_id,
            [
                (":status", str(status_code)),
                ("content-type", "text/plain"),
                ("content-length", str(len(message))),
            ]
        )
        h2_connection.send_data(stream_id, message.encode())
        h2_connection.end_stream(stream_id)

if __name__ == '__main__':
    addr = socket.gethostbyname(socket.gethostname())
    server = Server(addr)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    server_thread.join()
