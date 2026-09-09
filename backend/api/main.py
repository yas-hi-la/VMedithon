"""Minimal HTTP entry point for the prototype backend."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os


class HealthHandler(BaseHTTPRequestHandler):
    """Serve the initial health-check endpoint."""

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404, "Not Found")
            return

        response = json.dumps({"status": "ok"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    server = HTTPServer((host, port), HealthHandler)
    print(f"Backend listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
