"""Database-specific configuration."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class DatabaseSettings:
    path: Path = Path("data/app.db")

    @classmethod
    def from_environment(cls) -> "DatabaseSettings":
        configured_path = os.getenv("DB_PATH", str(cls.path))
        if not configured_path.strip():
            raise ValueError("DB_PATH must not be empty")
        return cls(path=Path(configured_path).expanduser())
