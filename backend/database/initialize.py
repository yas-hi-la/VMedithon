"""Explicit, repeatable database initialization."""

from pathlib import Path

from backend.database.config import DatabaseSettings
from backend.database.connection import connect

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
CURRENT_SCHEMA_VERSION = 2


def initialize_database(settings: DatabaseSettings) -> None:
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(settings) as connection:
        current_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if current_version > CURRENT_SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {current_version} is newer than "
                f"supported version {CURRENT_SCHEMA_VERSION}"
            )
        connection.executescript(schema)


def main() -> None:
    settings = DatabaseSettings.from_environment()
    initialize_database(settings)
    print(f"Database initialized at {settings.path}")


if __name__ == "__main__":
    main()
