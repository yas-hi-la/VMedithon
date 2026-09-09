from pathlib import Path
import sqlite3
import tempfile
import unittest

from backend.database.config import DatabaseSettings
from backend.database.connection import connect
from backend.database.initialize import initialize_database
from backend.models.variant import Variant
from backend.services.variant_service.repository import get_variant, insert_variant


class VariantRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = DatabaseSettings(path=Path(self.temp_dir.name) / "test.db")
        initialize_database(self.settings)
        self.connection = connect(self.settings)

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    def test_insert_and_retrieve_variant(self) -> None:
        variant = insert_variant(
            self.connection,
            Variant(gene="BRCA1", hgvs_notation="c.5266dupC"),
        )
        self.connection.commit()

        self.assertIsNotNone(variant.id)
        self.assertEqual(get_variant(self.connection, variant.id), variant)

    def test_missing_variant_returns_none(self) -> None:
        self.assertIsNone(get_variant(self.connection, 999))

    def test_database_rejects_duplicate_variant(self) -> None:
        variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        insert_variant(self.connection, variant)
        self.connection.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            insert_variant(self.connection, variant)

    def test_database_rejects_blank_required_fields(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO variants (gene, hgvs_notation) VALUES (?, ?)",
                ("", "c.5266dupC"),
            )

        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO variants (gene, hgvs_notation) VALUES (?, ?)",
                ("BRCA1", ""),
            )

    def test_model_rejects_blank_required_fields(self) -> None:
        with self.assertRaises(ValueError):
            Variant(gene=" ", hgvs_notation="c.5266dupC")

        with self.assertRaises(ValueError):
            Variant(gene="BRCA1", hgvs_notation=" ")


if __name__ == "__main__":
    unittest.main()
