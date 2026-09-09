import unittest

from backend.analysis.engine import analyze_variant
from backend.analysis.types import (
    AnalysisStatus,
    Classification,
    CriterionCode,
    CriterionStrength,
    EvidenceDirection,
    EvidenceItem,
    EvidenceSource,
)
from backend.models.variant import Variant


class AnalysisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.variant = Variant(gene="BRCA1", hgvs_notation="c.5266dupC")
        self.source = EvidenceSource(
            name="test-source", reference="https://example.test/evidence/1"
        )

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

    def test_empty_evidence_is_insufficient(self) -> None:
        result = analyze_variant(self.variant, [])

        self.assertEqual(result.classification, Classification.INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.criteria_considered, ())
        self.assertEqual(result.evidence_used, ())
        self.assertIn("missing evidence", result.decision_trace[0])

    def test_structured_evidence_preserves_provenance(self) -> None:
        item = self.evidence()

        result = analyze_variant(self.variant, [item])

        self.assertEqual(result.evidence_used, (item,))
        self.assertEqual(result.evidence_used[0].source, self.source)
        self.assertEqual(result.criteria_considered, (CriterionCode.PM2,))

    def test_supported_criteria_and_strength_are_representable(self) -> None:
        item = self.evidence(
            criterion=CriterionCode.PS3,
            strength=CriterionStrength.STRONG,
        )

        self.assertEqual(item.criterion, CriterionCode.PS3)
        self.assertEqual(item.strength, CriterionStrength.STRONG)

    def test_invalid_criterion_and_strength_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.evidence(criterion="NOT_ACMG")  # type: ignore[arg-type]

        with self.assertRaises(ValueError):
            self.evidence(strength="unsupported")  # type: ignore[arg-type]

    def test_single_direction_does_not_claim_a_clinical_classification(self) -> None:
        result = analyze_variant(self.variant, [self.evidence()])

        self.assertEqual(result.classification, Classification.INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.status, AnalysisStatus.UNSUPPORTED)
        self.assertIn("no ACMG/AMP combination rule", result.decision_trace[0])

    def test_one_pathogenic_criterion_is_insufficient(self) -> None:
        result = analyze_variant(
            self.variant,
            [self.evidence(criterion=CriterionCode.PS3, strength=CriterionStrength.STRONG)],
        )

        self.assertEqual(result.classification, Classification.INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.satisfied_rules, ())

    def test_one_strong_benign_criterion_is_insufficient(self) -> None:
        result = analyze_variant(
            self.variant,
            [
                self.evidence(
                    criterion=CriterionCode.BS1,
                    strength=CriterionStrength.STRONG,
                    direction=EvidenceDirection.BENIGN,
                )
            ],
        )

        self.assertEqual(result.classification, Classification.INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.satisfied_rules, ())

    def test_two_supporting_benign_criteria_are_insufficient(self) -> None:
        result = analyze_variant(
            self.variant,
            [
                self.evidence(
                    evidence_id="frequency",
                    criterion=CriterionCode.BS1,
                    strength=CriterionStrength.SUPPORTING,
                    direction=EvidenceDirection.BENIGN,
                ),
                self.evidence(
                    evidence_id="computational",
                    criterion=CriterionCode.BP4,
                    strength=CriterionStrength.SUPPORTING,
                    direction=EvidenceDirection.BENIGN,
                ),
            ],
        )

        self.assertEqual(result.classification, Classification.INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.satisfied_rules, ())

    def test_strong_plus_supporting_benign_is_likely_benign(self) -> None:
        result = analyze_variant(
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
        self.assertEqual(result.satisfied_rules, ("LB_STRONG_PLUS_SUPPORTING",))

    def test_two_strong_benign_criteria_are_benign(self) -> None:
        result = analyze_variant(
            self.variant,
            [
                self.evidence(
                    evidence_id="strong-one",
                    criterion=CriterionCode.BS1,
                    strength=CriterionStrength.STRONG,
                    direction=EvidenceDirection.BENIGN,
                ),
                self.evidence(
                    evidence_id="strong-two",
                    criterion=CriterionCode.BP4,
                    strength=CriterionStrength.STRONG,
                    direction=EvidenceDirection.BENIGN,
                ),
            ],
        )

        self.assertEqual(result.classification, Classification.BENIGN)
        self.assertEqual(result.satisfied_rules, ("B_TWO_STRONG",))

    def test_stand_alone_benign_evidence_is_benign(self) -> None:
        result = analyze_variant(
            self.variant,
            [
                self.evidence(
                    criterion=CriterionCode.BS1,
                    strength=CriterionStrength.STAND_ALONE,
                    direction=EvidenceDirection.BENIGN,
                )
            ],
        )

        self.assertEqual(result.classification, Classification.BENIGN)
        self.assertEqual(result.satisfied_rules, ("B_STAND_ALONE",))

    def test_pathogenic_strong_plus_moderate_is_likely_pathogenic(self) -> None:
        result = analyze_variant(
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
        self.assertEqual(result.satisfied_rules, ("LP_STRONG_PLUS_MODERATE",))
        self.assertEqual(
            result.rule_evaluations[3].evidence_ids,
            ("functional", "population"),
        )

    def test_unsupported_combinations_are_reported(self) -> None:
        result = analyze_variant(
            self.variant,
            [self.evidence(criterion=CriterionCode.PP3)],
        )

        self.assertEqual(result.status, AnalysisStatus.UNSUPPORTED)
        self.assertEqual(result.classification, Classification.INSUFFICIENT_EVIDENCE)
        self.assertIn("ADDITIONAL_ACMG_AMP_COMBINATIONS", result.unsupported_rules)
        self.assertTrue(all(not rule.satisfied for rule in result.rule_evaluations))

    def test_conflicting_evidence_is_explicit(self) -> None:
        result = analyze_variant(
            self.variant,
            [
                self.evidence(evidence_id="pathogenic"),
                self.evidence(
                    evidence_id="benign",
                    criterion=CriterionCode.BP4,
                    direction=EvidenceDirection.BENIGN,
                ),
            ],
        )

        self.assertEqual(result.classification, Classification.CONFLICTING)
        self.assertEqual(result.status, AnalysisStatus.CONFLICTING)
        self.assertEqual(
            result.criteria_considered,
            (CriterionCode.BP4, CriterionCode.PM2),
        )
        self.assertEqual(len(result.evidence_used), 2)
        self.assertIn("conflicting evidence", result.decision_trace[0])

    def test_rule_trace_is_evidence_traceable(self) -> None:
        result = analyze_variant(
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

        self.assertEqual(result.criterion_evaluations[0].evidence_ids, ("population",))
        self.assertEqual(result.criterion_evaluations[1].evidence_ids, ("functional",))
        self.assertIn("functional", result.decision_trace[0])
        self.assertIn("population", result.decision_trace[0])

    def test_duplicate_evidence_ids_are_rejected(self) -> None:
        item = self.evidence()

        with self.assertRaises(ValueError):
            analyze_variant(self.variant, [item, item])

    def test_analysis_is_deterministic(self) -> None:
        evidence = [
            self.evidence(evidence_id="b", criterion=CriterionCode.PS3),
            self.evidence(evidence_id="a"),
        ]

        first = analyze_variant(self.variant, evidence)
        second = analyze_variant(self.variant, evidence)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
