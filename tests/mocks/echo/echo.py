import http.server
import json
import logging
from os import environ
import socketserver
from urllib.parse import parse_qs

ECHO_PORT = int(environ.get("ECHO_PORT", "80"))

Handler = http.server.BaseHTTPRequestHandler

ECHO_MESSAGE = environ.get("ECHO_MESSAGE", "Hello")


class H(Handler):
    protocol_version = "HTTP/1.0"
    rsp = {"method": None, "path": None, "headers": {}, "body": "", "message": ECHO_MESSAGE}

    def write_response(self):
        self.rsp["method"] = self.command.lower()
        if self.path.startswith("/redirect"):
            self.send_response(308)
            _, _, queries = self.path.partition("?")
            params = parse_qs(queries)
            self.send_header("location", params["location"][0])
        else:
            self.send_response(200)

        self.rsp["path"] = self.path
        self.rsp["headers"] = {k: v for k, v in self.headers.items()}
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length > 0:
            self.rsp["body"] = self.rfile.read(content_length).decode()
        b = json.dumps(self.rsp).encode("UTF-8")

        self.send_header("Content-Length", str(len(b)))
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(b)

    def do_GET(self):
        self.write_response()

    def do_POST(self):
        self.write_response()

    def do_PUT(self):
        self.write_response()

    def do_PATH(self):
        self.write_response()

    def do_DELETE(self):
        self.write_response()

    def do_OPTION(self):
        self.write_response()


if __name__ == "__main__":

    FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler()])
    logger = logging.getLogger(__name__)

    with socketserver.TCPServer(("", ECHO_PORT), H) as httpd:
        logger.info(f"EchoServer listening on port {ECHO_PORT}")
        httpd.serve_forever()
