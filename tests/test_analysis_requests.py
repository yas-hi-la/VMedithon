import unittest
from unittest.mock import patch

from backend.analysis.types import (
    CriterionCode,
    CriterionStrength,
    EvidenceDirection,
)
from backend.api.analysis_requests import parse_analysis_request
from backend.api.controllers import analysis_controller
from backend.models.variant import Variant


class AnalysisRequestParserTest(unittest.TestCase):
    def valid_payload(self) -> dict[str, object]:
        return {
            "variant": {
                "gene": "BRCA1",
                "hgvs_notation": "c.5266dupC",
            },
            "evidence": [],
        }

    def evidence(self) -> dict[str, object]:
        return {
            "evidence_id": "evidence-1",
            "criterion": "PM2",
            "strength": "moderate",
            "direction": "pathogenic",
            "source": {
                "name": "test-source",
                "reference": "https://example.test/evidence-1",
            },
            "summary": "Explicit test evidence",
        }

    def assert_invalid(self, payload: object) -> None:
        with self.assertRaises((TypeError, ValueError)):
            parse_analysis_request(payload)

    def test_valid_minimal_request_maps_to_domain_objects(self) -> None:
        request = parse_analysis_request(self.valid_payload())

        self.assertEqual(
            request.variant,
            Variant(gene="BRCA1", hgvs_notation="c.5266dupC"),
        )
        self.assertEqual(request.evidence, ())

    def test_valid_multiple_evidence_records_are_mapped(self) -> None:
        payload = self.valid_payload()
        payload["evidence"] = [self.evidence(), {**self.evidence(), "evidence_id": "evidence-2"}]

        request = parse_analysis_request(payload)

        self.assertEqual(len(request.evidence), 2)
        self.assertEqual(request.evidence[0].criterion, CriterionCode.PM2)
        self.assertEqual(request.evidence[0].strength, CriterionStrength.MODERATE)
        self.assertEqual(request.evidence[0].direction, EvidenceDirection.PATHOGENIC)
        self.assertEqual(request.evidence[0].source.name, "test-source")

    def test_missing_variant_is_rejected(self) -> None:
        payload = self.valid_payload()
        del payload["variant"]
        self.assert_invalid(payload)

    def test_missing_gene_is_rejected(self) -> None:
        payload = self.valid_payload()
        del payload["variant"]["gene"]  # type: ignore[index]
        self.assert_invalid(payload)

    def test_blank_gene_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["variant"]["gene"] = "   "  # type: ignore[index]
        self.assert_invalid(payload)

    def test_missing_hgvs_notation_is_rejected(self) -> None:
        payload = self.valid_payload()
        del payload["variant"]["hgvs_notation"]  # type: ignore[index]
        self.assert_invalid(payload)

    def test_blank_hgvs_notation_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["variant"]["hgvs_notation"] = ""  # type: ignore[index]
        self.assert_invalid(payload)

    def test_missing_evidence_is_rejected(self) -> None:
        payload = self.valid_payload()
        del payload["evidence"]
        self.assert_invalid(payload)

    def test_evidence_must_be_an_array(self) -> None:
        payload = self.valid_payload()
        payload["evidence"] = {}
        self.assert_invalid(payload)

    def test_malformed_evidence_item_is_rejected(self) -> None:
        payload = self.valid_payload()
        payload["evidence"] = ["not an object"]
        self.assert_invalid(payload)

    def test_invalid_criterion_is_rejected(self) -> None:
        payload = self.valid_payload()
        item = self.evidence()
        item["criterion"] = "NOT_ACMG"
        payload["evidence"] = [item]
        self.assert_invalid(payload)

    def test_invalid_strength_is_rejected(self) -> None:
        payload = self.valid_payload()
        item = self.evidence()
        item["strength"] = "invalid"
        payload["evidence"] = [item]
        self.assert_invalid(payload)

    def test_invalid_direction_is_rejected(self) -> None:
        payload = self.valid_payload()
        item = self.evidence()
        item["direction"] = "invalid"
        payload["evidence"] = [item]
        self.assert_invalid(payload)

    def test_invalid_evidence_id_is_rejected(self) -> None:
        for value in (None, "", "   ", 42):
            payload = self.valid_payload()
            item = self.evidence()
            item["evidence_id"] = value
            payload["evidence"] = [item]
            with self.subTest(value=value):
                self.assert_invalid(payload)

    def test_invalid_source_structure_is_rejected(self) -> None:
        for source in (None, [], {"reference": "missing name"}, {"name": ""}):
            payload = self.valid_payload()
            item = self.evidence()
            item["source"] = source
            payload["evidence"] = [item]
            with self.subTest(source=source):
                self.assert_invalid(payload)

    def test_invalid_summary_type_is_rejected(self) -> None:
        payload = self.valid_payload()
        item = self.evidence()
        item["summary"] = 123
        payload["evidence"] = [item]
        self.assert_invalid(payload)

    def test_valid_payload_reaches_application_service_with_domain_objects(self) -> None:
        payload = self.valid_payload()
        payload["evidence"] = [self.evidence()]
        expected_response = {"classification": "stub"}

        with patch(
            "backend.api.controllers.run_variant_analysis",
            return_value=type("Result", (), {})(),
        ) as run:
            with patch(
                "backend.api.controllers.serialize_analysis_result",
                return_value=expected_response,
            ):
                response = analysis_controller(payload)

        self.assertEqual(response, expected_response)
        run.assert_called_once()
        variant, evidence = run.call_args.args
        self.assertIsInstance(variant, Variant)
        self.assertEqual(variant.gene, "BRCA1")
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].evidence_id, "evidence-1")

    def test_invalid_payload_is_rejected_before_analysis_service_runs(self) -> None:
        payload = self.valid_payload()
        payload["variant"]["gene"] = ""  # type: ignore[index]

        with patch("backend.api.controllers.run_variant_analysis") as run:
            self.assert_invalid_controller_payload(payload)

        run.assert_not_called()

    def assert_invalid_controller_payload(self, payload: object) -> None:
        with self.assertRaises(ValueError):
            analysis_controller(payload)


if __name__ == "__main__":
    unittest.main()
