"""SQLite connection management."""

import sqlite3

from backend.database.config import DatabaseSettings


def connect(settings: DatabaseSettings) -> sqlite3.Connection:
    settings.path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
