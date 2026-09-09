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
from backend.services.variant_service.persistence_service import persist_variant_evidence
from backend.services.variant_service.repository import get_variant_by_identity
from backend.services.variant_service.evidence_repository import get_evidence_for_variant


class EvidencePersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = DatabaseSettings(path=Path(self.temp_dir.name) / "test.db")
        initialize_database(self.settings)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def evidence(self, evidence_id: str) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=evidence_id,
            criterion=CriterionCode.PM2,
            strength=CriterionStrength.MODERATE,
            direction=EvidenceDirection.PATHOGENIC,
            source=EvidenceSource(name="test-source"),
            summary="Explicit test evidence",
        )

    def test_successful_batch_inserts_all_records_in_one_transaction(self) -> None:
        variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        evidence = (self.evidence("one"), self.evidence("two"))

        with connect(self.settings) as connection:
            persisted_variant, persisted_evidence = persist_variant_evidence(
                connection,
                variant,
                evidence,
            )

        self.assertIsNotNone(persisted_variant.id)
        self.assertEqual(persisted_evidence, evidence)
        with connect(self.settings) as connection:
            self.assertEqual(
                get_evidence_for_variant(connection, persisted_variant.id),
                evidence,
            )

    def test_failure_rolls_back_variant_and_complete_evidence_batch(self) -> None:
        variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        duplicate_evidence = self.evidence("duplicate")

        with self.assertRaises(sqlite3.IntegrityError):
            with connect(self.settings) as connection:
                persist_variant_evidence(
                    connection,
                    variant,
                    (duplicate_evidence, duplicate_evidence),
                )

        with connect(self.settings) as connection:
            self.assertIsNone(
                get_variant_by_identity(
                    connection,
                    variant.gene,
                    variant.hgvs_notation,
                )
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM variant_evidence"
                ).fetchone()[0],
                0,
            )


if __name__ == "__main__":
    unittest.main()
