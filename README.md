# HTTP/2 Server

## Prerequisites

1. **Python Version**: Ensure you have Python 3.8 or higher installed on your system.
2. **Command-Line Knowledge**: Basic familiarity with command-line usage.
3. **Required Python Libraries**:
   - `socket`
   - `threading`
   - `os`
   - `keyboard`
   - `h2` (for HTTP/2 support)
   - `hashlib`
   - `time`

   To install the `h2` library, run the following command in your terminal:
   ```bash
   pip install h2

## Starting the Server
1.	Open a terminal or command prompt.<br/>
2.	Navigate to the directory containing the server.py script.<br/>
3.	Run the server using:   <br/>
```bash
python server.py
```
4.	The server will start and display the following message:<br/>
```bash
==================================================
[INFO] HTTP Server running on <your-ip>:<port>
==================================================
```

## Accessing the Server
1.	Open a web browser or an HTTP client.
2.	Use the server's host and port in the URL.
3.	If HTTP/2 is enabled, the server will automatically detect and handle HTTP/2 requests.

###    !!! That’s it, the server should be working !!!
