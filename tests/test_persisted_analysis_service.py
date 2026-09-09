from pathlib import Path
import sqlite3
import tempfile
import unittest

from backend.analysis.types import (
    AnalysisResult,
    Classification,
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
from backend.services.variant_service.evidence_repository import get_evidence_for_variant
from backend.services.variant_service.persisted_analysis_service import (
    persist_and_analyze_variant,
)
from backend.services.variant_service.repository import (
    get_variant_by_identity,
    insert_variant,
)


class PersistedAnalysisServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = DatabaseSettings(path=Path(self.temp_dir.name) / "test.db")

        initialize_database(self.settings)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def evidence(
        self,
        evidence_id: str,
        criterion: CriterionCode = CriterionCode.PM2,
        strength: CriterionStrength = CriterionStrength.MODERATE,
        direction: EvidenceDirection = EvidenceDirection.PATHOGENIC,
    ) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=evidence_id,
            criterion=criterion,
            strength=strength,
            direction=direction,
            source=EvidenceSource(name="test-source"),
            summary="Explicit test evidence",
        )

    def test_new_variant_evidence_is_persisted_and_analyzed(self) -> None:
        variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        evidence = (
            self.evidence(
                "functional",
                criterion=CriterionCode.PS3,
                strength=CriterionStrength.STRONG,
            ),
            self.evidence("population"),
        )

        with connect(self.settings) as connection:
            result = persist_and_analyze_variant(connection, variant, evidence)

        self.assertIsNotNone(result.variant.id)
        self.assertEqual(result.evidence_used, evidence)
        self.assertEqual(result.classification, Classification.LIKELY_PATHOGENIC)
        with connect(self.settings) as connection:
            self.assertEqual(
                get_evidence_for_variant(connection, result.variant.id), evidence
            )

    def test_existing_variant_is_reused(self) -> None:
        variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        with connect(self.settings) as connection:
            existing = insert_variant(connection, variant)
            connection.commit()

        evidence = (self.evidence("new-evidence"),)
        with connect(self.settings) as connection:
            result = persist_and_analyze_variant(connection, variant, evidence)
            variant_count = connection.execute(
                "SELECT COUNT(*) FROM variants"
            ).fetchone()[0]

        self.assertEqual(result.variant.id, existing.id)
        self.assertEqual(variant_count, 1)

    def test_analysis_receives_exact_submitted_evidence(self) -> None:
        variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        evidence = (self.evidence("one"), self.evidence("two"))
        captured: dict[str, object] = {}
        expected = AnalysisResult(
            variant=variant,
            classification=Classification.INSUFFICIENT_EVIDENCE,
            criteria_considered=(),
            evidence_used=evidence,
            decision_trace=("captured",),
        )

        def capture_analysis(
            analyzed_variant: Variant,
            analyzed_evidence: tuple[EvidenceItem, ...],
        ) -> AnalysisResult:
            captured["variant"] = analyzed_variant
            captured["evidence"] = analyzed_evidence
            return expected

        with connect(self.settings) as connection:
            result = persist_and_analyze_variant(
                connection,
                variant,
                evidence,
                analysis_operation=capture_analysis,
            )

        self.assertIs(result, expected)
        self.assertEqual(captured["evidence"], evidence)
        self.assertIsInstance(captured["variant"], Variant)

    def test_successful_analysis_commits_transaction(self) -> None:
        variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        evidence = (self.evidence("one"),)

        with connect(self.settings) as connection:
            persist_and_analyze_variant(connection, variant, evidence)

        with connect(self.settings) as connection:
            persisted = get_variant_by_identity(
                connection,
                variant.gene,
                variant.hgvs_notation,
            )
            self.assertIsNotNone(persisted)
            self.assertEqual(get_evidence_for_variant(connection, persisted.id), evidence)

    def test_duplicate_evidence_rolls_back_new_variant_and_batch(self) -> None:
        variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        duplicate = self.evidence("duplicate")

        with self.assertRaises(sqlite3.IntegrityError):
            with connect(self.settings) as connection:
                persist_and_analyze_variant(
                    connection,
                    variant,
                    (duplicate, duplicate),
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
                connection.execute("SELECT COUNT(*) FROM variant_evidence").fetchone()[0],
                0,
            )

    def test_failure_on_later_evidence_insert_rolls_back_everything(self) -> None:
        variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        first = self.evidence("first")
        second = self.evidence("second")
        duplicate_first = self.evidence("first")

        with self.assertRaises(sqlite3.IntegrityError):
            with connect(self.settings) as connection:
                persist_and_analyze_variant(
                    connection,
                    variant,
                    (first, second, duplicate_first),
                )

        with connect(self.settings) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variants").fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variant_evidence").fetchone()[0],
                0,
            )

    def test_analysis_failure_rolls_back_persistence(self) -> None:
        variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        evidence = (self.evidence("one"),)

        def failing_analysis(
            analyzed_variant: Variant,
            analyzed_evidence: tuple[EvidenceItem, ...],
        ) -> AnalysisResult:
            raise RuntimeError("analysis failed")

        with self.assertRaises(RuntimeError):
            with connect(self.settings) as connection:
                persist_and_analyze_variant(
                    connection,
                    variant,
                    evidence,
                    analysis_operation=failing_analysis,
                )

        with connect(self.settings) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variants").fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variant_evidence").fetchone()[0],
                0,
            )

    def test_no_analysis_result_table_is_created(self) -> None:
        with connect(self.settings) as connection:
            result_table = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name = 'analysis_results'
                """
            ).fetchone()

        self.assertIsNone(result_table)


if __name__ == "__main__":
    unittest.main()
