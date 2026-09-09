"""HTTP request handling for API routes."""

import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import json
import sqlite3
from urllib.parse import unquote

from backend.api.routes import resolve_route, route_exists
from backend.services.evidence_retrieval.clinvar import ClinVarRetrievalError
from backend.services.variant_service.read_service import VariantNotFoundError


class ApiRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._handle_request()

    def do_POST(self) -> None:
        self._handle_request()

    def do_PUT(self) -> None:
        self._handle_request()

    def do_PATCH(self) -> None:
        self._handle_request()

    def do_DELETE(self) -> None:
        self._handle_request()

    def _handle_request(self) -> None:
        path = self.path.split("?", 1)[0]
        controller = resolve_route(self.command, path)
        if controller is None:
            if route_exists(path):
                self._send_json(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    {"error": {"code": "method_not_allowed", "message": "Method Not Allowed"}},
                )
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not Found"})
            return

        try:
            if self.command == "POST":
                payload = controller(self._read_json_body())
            elif self.command == "GET" and path == "/analysis/variants":
                payload = controller(self._read_query_string())
            elif self.command == "GET" and path.startswith("/evidence/"):
                parts = [unquote(part) for part in path.split("/") if part]
                if len(parts) != 3:
                    raise ValueError("evidence path must include gene and hgvs notation")
                payload = controller(parts[1], parts[2])
            else:
                payload = controller()
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": {"code": "invalid_request", "message": str(error)}},
            )
            return
        except VariantNotFoundError:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "error": {
                        "code": "variant_not_found",
                        "message": "Variant not found",
                    }
                },
            )
            return
        except sqlite3.IntegrityError:
            self._send_json(
                HTTPStatus.CONFLICT,
                {
                    "error": {
                        "code": "persistence_conflict",
                        "message": "Submitted data conflicts with existing data",
                    }
                },
            )
            return
        except ClinVarRetrievalError as error:
            self._send_json(
                HTTPStatus(error.status_code),
                {"error": {"code": "external_evidence_unavailable", "message": str(error)}},
            )
            return
        except Exception:
            traceback.print_exc()
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "error": {
                        "code": "internal_server_error",
                        "message": "Internal Server Error",
                    }
                },
            )
            return

        self._send_json(HTTPStatus.OK, payload)

    def _read_json_body(self) -> object:
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            raise ValueError("request body is required")
        try:
            body_length = int(content_length)
        except ValueError as error:
            raise ValueError("invalid Content-Length") from error
        if body_length <= 0:
            raise ValueError("request body is required")
        try:
            body = self.rfile.read(body_length)
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("request body must contain valid JSON") from error

    def _read_query_string(self) -> str:
        return self.path.split("?", 1)[1] if "?" in self.path else ""

    def _send_json(self, status: HTTPStatus, payload: dict[str, str]) -> None:
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: object) -> None:
        return