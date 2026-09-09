"""HTTP request handling for API routes."""

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import json

from backend.api.routes import resolve_route


class ApiRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._handle_request()

    def _handle_request(self) -> None:
        controller = resolve_route(self.command, self.path)
        if controller is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not Found"})
            return

        try:
            payload = controller()
        except Exception:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Internal Server Error"},
            )
            return

        self._send_json(HTTPStatus.OK, payload)

    def _send_json(self, status: HTTPStatus, payload: dict[str, str]) -> None:
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: object) -> None:
        return
