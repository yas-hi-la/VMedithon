"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_environment(cls) -> "Settings":
        host = os.getenv("BACKEND_HOST", cls.host)
        port_value = os.getenv("BACKEND_PORT", str(cls.port))
        try:
            port = int(port_value)
        except ValueError as error:
            raise ValueError("BACKEND_PORT must be an integer") from error
        if not 1 <= port <= 65535:
            raise ValueError("BACKEND_PORT must be between 1 and 65535")
        return cls(host=host, port=port)
