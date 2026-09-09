"""HTTP server construction and lifecycle."""

from http.server import HTTPServer

from backend.api.handler import ApiRequestHandler
from backend.config.settings import Settings


def create_server(settings: Settings) -> HTTPServer:
    return HTTPServer((settings.host, settings.port), ApiRequestHandler)
