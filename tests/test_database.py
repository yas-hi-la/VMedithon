import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backend.database.config import DatabaseSettings
from backend.database.connection import connect
from backend.database.health import check_database
from backend.database.initialize import initialize_database


class DatabaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.db"
        self.settings = DatabaseSettings(path=self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_configuration_reads_database_path_from_environment(self) -> None:
        with patch.dict(os.environ, {"DB_PATH": str(self.database_path)}):
            settings = DatabaseSettings.from_environment()

        self.assertEqual(settings.path, self.database_path)

    def test_configuration_rejects_empty_database_path(self) -> None:
        with patch.dict(os.environ, {"DB_PATH": "   "}):
            with self.assertRaises(ValueError):
                DatabaseSettings.from_environment()

    def test_initialization_creates_database_and_schema_version(self) -> None:
        initialize_database(self.settings)

        self.assertTrue(self.database_path.exists())
        with connect(self.settings) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]

        self.assertEqual(version, 1)

    def test_initialization_is_repeatable(self) -> None:
        initialize_database(self.settings)
        initialize_database(self.settings)

        self.assertTrue(check_database(self.settings))

    def test_health_check_executes_query(self) -> None:
        initialize_database(self.settings)

        self.assertTrue(check_database(self.settings))

    def test_connection_is_sqlite(self) -> None:
        with connect(self.settings) as connection:
            self.assertIsInstance(connection, sqlite3.Connection)


if __name__ == "__main__":
    unittest.main()
