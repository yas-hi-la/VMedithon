"""Application entry point for the prototype backend."""

from backend.api.server import create_server
from backend.config.settings import Settings


def main() -> None:
    settings = Settings.from_environment()
    server = create_server(settings)
    print(f"Backend listening on http://{settings.host}:{settings.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
