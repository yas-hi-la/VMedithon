from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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
from backend.services.variant_service.evidence_repository import insert_evidence
from backend.services.variant_service.read_service import (
    VariantNotFoundError,
    get_variant_with_evidence,
)
from backend.services.variant_service.repository import insert_variant


class VariantReadServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = DatabaseSettings(path=Path(self.temp_dir.name) / "test.db")
        initialize_database(self.settings)
        self.connection = connect(self.settings)
        self.variant = insert_variant(
            self.connection,
            Variant(gene="BRCA1", hgvs_notation="c.5266dupC"),
        )
        self.connection.commit()

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    def evidence(
        self,
        evidence_id: str,
        reference: str | None = "https://example.test/evidence",
    ) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=evidence_id,
            criterion=CriterionCode.PM2,
            strength=CriterionStrength.MODERATE,
            direction=EvidenceDirection.PATHOGENIC,
            source=EvidenceSource(name="test-source", reference=reference),
            summary="Explicit persisted evidence",
        )

    def test_existing_variant_is_retrieved_by_identity(self) -> None:
        result = get_variant_with_evidence(
            self.connection,
            "BRCA1",
            "c.5266dupC",
        )

        self.assertEqual(result.variant, self.variant)
        self.assertEqual(result.evidence, ())

    def test_multiple_evidence_records_are_returned_in_repository_order(self) -> None:
        first = self.evidence("first")
        second = self.evidence("second", reference=None)
        insert_evidence(self.connection, self.variant.id, first)
        insert_evidence(self.connection, self.variant.id, second)
        self.connection.commit()

        result = get_variant_with_evidence(
            self.connection,
            "BRCA1",
            "c.5266dupC",
        )

        self.assertEqual(result.evidence, (first, second))
        self.assertEqual(result.evidence[0].evidence_id, "first")
        self.assertEqual(result.evidence[1].source.reference, None)

    def test_missing_variant_raises_explicit_not_found_error(self) -> None:
        with self.assertRaises(VariantNotFoundError):
            get_variant_with_evidence(
                self.connection,
                "BRCA2",
                "c.5946delT",
            )

    def test_read_service_does_not_invoke_analysis_engine(self) -> None:
        with patch("backend.analysis.engine.analyze_variant") as analyze:
            get_variant_with_evidence(
                self.connection,
                "BRCA1",
                "c.5266dupC",
            )

        analyze.assert_not_called()


if __name__ == "__main__":
    unittest.main()
