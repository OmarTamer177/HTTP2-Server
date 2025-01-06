import socket
from h2.config import H2Configuration
from h2.connection import H2Connection
import h2

def test_http2_server():
    # Replace with your server's address and port
    server_address = "192.168.1.7"
    server_port = 80

    # Establish a TCP connection with the server
    client_socket = socket.create_connection((server_address, server_port))
    print("Connected to the server.")

    # Set up the HTTP/2 connection
    config = H2Configuration(client_side=True)
    h2_connection = H2Connection(config=config)
    h2_connection.initiate_connection()

    # Send the HTTP/2 preface and settings
    client_socket.sendall(h2_connection.data_to_send())
    print("HTTP/2 connection initialized.")

    # Create payload data for the POST request
    payload = "This is the data being sent in the POST request."
    payload_bytes = payload.encode('utf-8')

    # Send an HTTP/2 POST request with a payload
    headers = [
        (':method', 'POST'),
        (':scheme', 'http'),
        (':authority', f'{server_address}:{server_port}'),
        (':path', '/post.html'),
        ('content-length', str(len(payload_bytes))),
        ('content-type', 'text/plain'),
    ]
    stream_id = h2_connection.get_next_available_stream_id()
    h2_connection.send_headers(stream_id, headers)
    h2_connection.send_data(stream_id, payload_bytes)
    client_socket.sendall(h2_connection.data_to_send())
    print("Sent POST request to /post.html with payload.")

    # Read and process responses from the server
    while True:
        data = client_socket.recv(4096)
        if not data:
            break

        events = h2_connection.receive_data(data)
        for event in events:
            print(f"Event: {event}")
            if isinstance(event, h2.events.ResponseReceived):
                print("Response Headers:")
                for name, value in event.headers:
                    print(f"{name.decode()}: {value.decode()}")
            elif isinstance(event, h2.events.DataReceived):
                print("Response Data:")
                print(event.data.decode())
                h2_connection.acknowledge_received_data(event.flow_controlled_length, stream_id)
            elif isinstance(event, h2.events.StreamEnded):
                print(f"Stream {stream_id} ended.")
                return  # Stop after receiving a complete response

        # Flush any pending data
        client_socket.sendall(h2_connection.data_to_send())

if __name__ == "__main__":
    test_http2_server()
