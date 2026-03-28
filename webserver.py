import argparse
import http.server
import socketserver

parser = argparse.ArgumentParser()
parser.add_argument('--text', default='Default web server')
FLAGS = parser.parse_args()


class Handler(http.server.SimpleHTTPRequestHandler):
    # Disable reverse-DNS lookup in request logs.
    def address_string(self):
        return str(self.client_address[0])

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        body = f'<h1>{FLAGS.text}</h1>\n'.encode('utf-8')
        self.wfile.write(body)
        self.wfile.flush()


PORT = 80
socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(('', PORT), Handler)
httpd.serve_forever()
