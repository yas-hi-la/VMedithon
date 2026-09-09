from pathlib import Path
import sqlite3
import tempfile
import unittest

from backend.analysis.types import (
    CriterionCode,
    CriterionStrength,
    EvidenceDirection,
    EvidenceItem,
    EvidenceSource,
)
from backend.database.config import DatabaseSettings
from backend.database.connection import connect
from backend.database.initialize import initialize_database
from backend.models.variant import Variant
from backend.services.variant_service.evidence_repository import (
    get_evidence_for_variant,
    insert_evidence,
)
from backend.services.variant_service.repository import insert_variant


class EvidenceRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        settings = DatabaseSettings(path=Path(self.temp_dir.name) / "test.db")
        initialize_database(settings)
        self.connection = connect(settings)
        self.variant = insert_variant(
            self.connection,
            Variant(gene="BRCA1", hgvs_notation="c.5266dupC"),
        )
        self.other_variant = insert_variant(
            self.connection,
            Variant(gene="BRCA2", hgvs_notation="c.5946delT"),
        )
        self.connection.commit()

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    def evidence(
        self,
        evidence_id: str = "evidence-1",
        source_reference: str | None = "https://example.test/evidence-1",
    ) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=evidence_id,
            criterion=CriterionCode.PM2,
            strength=CriterionStrength.MODERATE,
            direction=EvidenceDirection.PATHOGENIC,
            source=EvidenceSource(
                name="test-source",
                reference=source_reference,
            ),
            summary="Explicit test evidence",
        )

    def insert_raw(self, **overrides: object) -> None:
        values = {
            "variant_id": self.variant.id,
            "evidence_id": "raw-evidence",
            "criterion": "PM2",
            "strength": "moderate",
            "direction": "pathogenic",
            "source_name": "test-source",
            "source_reference": None,
            "summary": "Raw evidence",
        }
        values.update(overrides)
        self.connection.execute(
            """
            INSERT INTO variant_evidence (
                variant_id, evidence_id, criterion, strength, direction,
                source_name, source_reference, summary
            ) VALUES (
                :variant_id, :evidence_id, :criterion, :strength, :direction,
                :source_name, :source_reference, :summary
            )
            """,
            values,
        )

    def test_valid_evidence_round_trips_all_fields(self) -> None:
        item = self.evidence()
        insert_evidence(self.connection, self.variant.id, item)
        self.connection.commit()

        self.assertEqual(
            get_evidence_for_variant(self.connection, self.variant.id),
            (item,),
        )

    def test_null_source_reference_round_trips(self) -> None:
        item = self.evidence(source_reference=None)
        insert_evidence(self.connection, self.variant.id, item)
        self.connection.commit()

        retrieved = get_evidence_for_variant(self.connection, self.variant.id)

        self.assertIsNone(retrieved[0].source.reference)

    def test_invalid_required_values_are_rejected(self) -> None:
        required_fields = {
            "evidence_id": "",
            "source_name": "",
            "summary": "",
        }
        for field, value in required_fields.items():
            with self.subTest(field=field):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.insert_raw(**{field: value})
                self.connection.rollback()

    def test_invalid_criterion_is_rejected(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_raw(criterion="NOT_ACMG")

    def test_invalid_strength_is_rejected(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_raw(strength="invalid")

    def test_invalid_direction_is_rejected(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_raw(direction="invalid")

    def test_unknown_variant_id_is_rejected(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert_raw(variant_id=999)

    def test_duplicate_variant_evidence_id_is_rejected(self) -> None:
        item = self.evidence()
        insert_evidence(self.connection, self.variant.id, item)
        self.connection.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            insert_evidence(self.connection, self.variant.id, item)

    def test_same_evidence_id_can_belong_to_different_variants(self) -> None:
        item = self.evidence()
        insert_evidence(self.connection, self.variant.id, item)
        insert_evidence(self.connection, self.other_variant.id, item)
        self.connection.commit()

        self.assertEqual(
            get_evidence_for_variant(self.connection, self.variant.id),
            (item,),
        )
        self.assertEqual(
            get_evidence_for_variant(self.connection, self.other_variant.id),
            (item,),
        )

    def test_retrieval_order_is_deterministic(self) -> None:
        first = self.evidence(evidence_id="first")
        second = self.evidence(evidence_id="second")
        insert_evidence(self.connection, self.variant.id, first)
        insert_evidence(self.connection, self.variant.id, second)
        self.connection.commit()

        self.assertEqual(
            tuple(item.evidence_id for item in get_evidence_for_variant(self.connection, self.variant.id)),
            ("first", "second"),
        )

    def test_variant_deletion_with_evidence_is_rejected(self) -> None:
        insert_evidence(self.connection, self.variant.id, self.evidence())
        self.connection.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "DELETE FROM variants WHERE id = ?",
                (self.variant.id,),
            )

        self.connection.rollback()
        self.assertIsNotNone(
            self.connection.execute(
                "SELECT id FROM variants WHERE id = ?",
                (self.variant.id,),
            ).fetchone()
        )


if __name__ == "__main__":
    unittest.main()
