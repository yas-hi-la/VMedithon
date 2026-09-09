"""Explicit, repeatable database initialization."""

from pathlib import Path

from backend.database.config import DatabaseSettings
from backend.database.connection import connect

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def initialize_database(settings: DatabaseSettings) -> None:
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(settings) as connection:
        connection.executescript(schema)


def main() -> None:
    settings = DatabaseSettings.from_environment()
    initialize_database(settings)
    print(f"Database initialized at {settings.path}")


if __name__ == "__main__":
    main()
