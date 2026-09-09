"""Database connectivity and query health checks."""

from backend.database.config import DatabaseSettings
from backend.database.connection import connect


def check_database(settings: DatabaseSettings) -> bool:
    with connect(settings) as connection:
        connection.execute("SELECT 1").fetchone()
    return True


def main() -> None:
    settings = DatabaseSettings.from_environment()
    check_database(settings)
    print("Database health: ok")


if __name__ == "__main__":
    main()
