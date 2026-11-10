"""Browser entry point for the Cornell Smart Parking product.

Serves one page: live parking status (a supplementary feature, outside UC.1), and a
Plan Your Trip popup that walks the
Cornell Driver through UC.1 up to the ranked recommendations, showing what
A1.1-A1.4 produce at each step. Every action goes through
cornell_driver_interface, like app.py. Standard library only, bound to
the local machine (docs/deployment.md). Requests are not logged, so a driver's
message stays out of the output.

Run with: python web_app.py
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cornell_driver_interface as driver_interface

HOST = "127.0.0.1"
PORT = 8000
PAGE_PATH = Path(__file__).parent / "web" / "index.html"
STORE_LOCK = threading.Lock()  # one request at a time reaches the data store


class DriverRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self._send(200, PAGE_PATH.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/live":
            with STORE_LOCK:
                status = driver_interface.get_live_parking_status()
            self._send_json(200, status)
        elif self.path == "/api/options":
            self._send_json(200, driver_interface.get_trip_form_options())
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except ValueError:
            self._send_json(400, {"error": "The request was not valid JSON."})
            return
        if self.path == "/api/interpret":  # UC.1.1 -> UC.1.2
            self._send_json(200, driver_interface.submit_trip_request(body["message"]))
        elif self.path == "/api/confirm":  # UC.1.3 -> UC.1.14
            with STORE_LOCK:
                result = driver_interface.confirm_trip_requirements(body["trip_request"])
            self._send_json(200, result)
        else:
            self._send_json(404, {"error": "not found"})

    def _send_json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

    def _send(self, status: int, content: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args) -> None:
        pass


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), DriverRequestHandler)
    print(f"Cornell Smart Parking: open http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
