import unittest

from backend.analysis.engine import analyze_variant
from backend.analysis.types import (
    AnalysisResult,
    Classification,
    CriterionCode,
    CriterionStrength,
    EvidenceDirection,
    EvidenceItem,
    EvidenceSource,
)
from backend.models.variant import Variant
from backend.services.variant_service.analysis_service import run_variant_analysis


class VariantAnalysisServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        self.source = EvidenceSource(name="test-source")

    def evidence(
        self,
        evidence_id: str = "evidence-1",
        criterion: CriterionCode = CriterionCode.PM2,
        strength: CriterionStrength = CriterionStrength.MODERATE,
        direction: EvidenceDirection = EvidenceDirection.PATHOGENIC,
    ) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=evidence_id,
            criterion=criterion,
            strength=strength,
            direction=direction,
            source=self.source,
            summary="Explicit test evidence",
        )

    def test_empty_evidence_delegates_and_returns_insufficient_result(self) -> None:
        result = run_variant_analysis(self.variant, [])

        self.assertEqual(result.classification, Classification.INSUFFICIENT_EVIDENCE)

    def test_service_returns_engine_result_unchanged(self) -> None:
        expected = AnalysisResult(
            variant=self.variant,
            classification=Classification.BENIGN,
            criteria_considered=(),
            evidence_used=(),
            decision_trace=("stub decision",),
        )
        calls: list[tuple[Variant, tuple[EvidenceItem, ...]]] = []

        def fake_engine(
            variant: Variant, evidence: tuple[EvidenceItem, ...]
        ) -> AnalysisResult:
            calls.append((variant, evidence))
            return expected

        result = run_variant_analysis(self.variant, [], analysis_engine=fake_engine)

        self.assertIs(result, expected)
        self.assertEqual(calls, [(self.variant, ())])

    def test_supported_pathogenic_result_is_preserved(self) -> None:
        result = run_variant_analysis(
            self.variant,
            [
                self.evidence(
                    evidence_id="functional",
                    criterion=CriterionCode.PS3,
                    strength=CriterionStrength.STRONG,
                ),
                self.evidence(
                    evidence_id="population",
                    criterion=CriterionCode.PM2,
                    strength=CriterionStrength.MODERATE,
                ),
            ],
        )

        self.assertEqual(result.classification, Classification.LIKELY_PATHOGENIC)
        self.assertEqual(
            tuple(item.evidence_id for item in result.evidence_used),
            ("functional", "population"),
        )

    def test_supported_benign_result_is_preserved(self) -> None:
        result = run_variant_analysis(
            self.variant,
            [
                self.evidence(
                    evidence_id="strong",
                    criterion=CriterionCode.BS1,
                    strength=CriterionStrength.STRONG,
                    direction=EvidenceDirection.BENIGN,
                ),
                self.evidence(
                    evidence_id="supporting",
                    criterion=CriterionCode.BP4,
                    strength=CriterionStrength.SUPPORTING,
                    direction=EvidenceDirection.BENIGN,
                ),
            ],
        )

        self.assertEqual(result.classification, Classification.LIKELY_BENIGN)
        self.assertEqual(
            tuple(item.evidence_id for item in result.evidence_used),
            ("strong", "supporting"),
        )

    def test_conflicting_result_is_preserved(self) -> None:
        result = run_variant_analysis(
            self.variant,
            [
                self.evidence(evidence_id="pathogenic"),
                self.evidence(
                    evidence_id="benign", direction=EvidenceDirection.BENIGN
                ),
            ],
        )

        self.assertEqual(result.classification, Classification.CONFLICTING)
        self.assertEqual(
            tuple(item.evidence_id for item in result.evidence_used),
            ("pathogenic", "benign"),
        )
        self.assertIn("conflicting evidence", result.decision_trace[0])

    def test_missing_variant_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            run_variant_analysis(None, [])

    def test_invalid_variant_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            run_variant_analysis("not-a-variant", [])  # type: ignore[arg-type]

    def test_missing_evidence_collection_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            run_variant_analysis(self.variant, None)

    def test_duplicate_evidence_ids_remain_engine_validation(self) -> None:
        item = self.evidence()

        with self.assertRaises(ValueError):
            run_variant_analysis(self.variant, [item, item])


if __name__ == "__main__":
    unittest.main()
