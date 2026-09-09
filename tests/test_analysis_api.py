import json
from http.client import HTTPConnection
import threading
import unittest
from unittest.mock import patch

from backend.analysis.types import AnalysisResult, Classification
from backend.api.server import create_server
from backend.config.settings import Settings
from backend.models.variant import Variant


class AnalysisApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = create_server(Settings(host="127.0.0.1", port=0))
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def request(
        self,
        method: str,
        path: str,
        payload: object = None,
        include_body: bool = True,
    ) -> tuple[int, dict[str, object]]:
        connection = HTTPConnection("127.0.0.1", self.port)
        body = json.dumps(payload) if include_body else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        response_payload = json.loads(response.read())
        connection.close()
        return response.status, response_payload

    def valid_request(self, evidence: list[dict[str, object]] | None = None) -> dict[str, object]:
        return {
            "variant": {
                "gene": "BRCA1",
                "hgvs_notation": "c.5266dupC",
            },
            "evidence": [] if evidence is None else evidence,
        }

    def evidence(
        self,
        evidence_id: str,
        criterion: str,
        strength: str,
        direction: str,
    ) -> dict[str, object]:
        return {
            "evidence_id": evidence_id,
            "criterion": criterion,
            "strength": strength,
            "direction": direction,
            "source": {
                "name": "test-source",
                "reference": "https://example.test/evidence/" + evidence_id,
            },
            "summary": "Explicit test evidence",
        }

    def test_empty_evidence_returns_insufficient_evidence(self) -> None:
        status, payload = self.request(
            "POST", "/analysis/variants", self.valid_request()
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["classification"], "insufficient_evidence")
        self.assertEqual(payload["status"], "insufficient")
        self.assertEqual(payload["evidence_used"], [])

    def test_supported_pathogenic_classification_is_serialized(self) -> None:
        evidence = [
            self.evidence("functional", "PS3", "strong", "pathogenic"),
            self.evidence("population", "PM2", "moderate", "pathogenic"),
        ]

        status, payload = self.request(
            "POST", "/analysis/variants", self.valid_request(evidence)
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["classification"], "likely_pathogenic")
        self.assertEqual(payload["satisfied_rules"], ["LP_STRONG_PLUS_MODERATE"])

    def test_supported_benign_classification_is_serialized(self) -> None:
        evidence = [
            self.evidence("strong", "BS1", "strong", "benign"),
            self.evidence("supporting", "BP4", "supporting", "benign"),
        ]

        status, payload = self.request(
            "POST", "/analysis/variants", self.valid_request(evidence)
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["classification"], "likely_benign")
        self.assertEqual(payload["satisfied_rules"], ["LB_STRONG_PLUS_SUPPORTING"])

    def test_conflicting_evidence_is_an_analysis_result_not_http_error(self) -> None:
        evidence = [
            self.evidence("pathogenic", "PM2", "moderate", "pathogenic"),
            self.evidence("benign", "BP4", "supporting", "benign"),
        ]

        status, payload = self.request(
            "POST", "/analysis/variants", self.valid_request(evidence)
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["classification"], "conflicting")
        self.assertEqual(payload["status"], "conflicting")

    def test_traceability_survives_serialization(self) -> None:
        evidence = [
            self.evidence("functional", "PS3", "strong", "pathogenic"),
            self.evidence("population", "PM2", "moderate", "pathogenic"),
        ]

        _, payload = self.request(
            "POST", "/analysis/variants", self.valid_request(evidence)
        )

        self.assertEqual(
            [item["evidence_id"] for item in payload["evidence_used"]],
            ["functional", "population"],
        )
        self.assertEqual(
            payload["criterion_evaluations"][0]["evidence_ids"], ["population"]
        )
        self.assertIn("functional", payload["decision_trace"][0])
        self.assertIn("population", payload["decision_trace"][0])

    def test_invalid_json_returns_bad_request(self) -> None:
        connection = HTTPConnection("127.0.0.1", self.port)
        connection.request(
            "POST",
            "/analysis/variants",
            body="{invalid",
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()

        self.assertEqual(response.status, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")

    def test_missing_request_body_returns_bad_request(self) -> None:
        status, payload = self.request(
            "POST", "/analysis/variants", include_body=False
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")

    def test_missing_variant_returns_bad_request(self) -> None:
        status, payload = self.request(
            "POST", "/analysis/variants", {"evidence": []}
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")

    def test_missing_variant_field_returns_bad_request(self) -> None:
        status, payload = self.request(
            "POST",
            "/analysis/variants",
            {"variant": {"gene": "BRCA1"}, "evidence": []},
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")

    def test_invalid_criterion_returns_bad_request(self) -> None:
        evidence = [self.evidence("bad", "NOT_ACMG", "moderate", "pathogenic")]

        status, payload = self.request(
            "POST", "/analysis/variants", self.valid_request(evidence)
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")

    def test_invalid_strength_or_direction_returns_bad_request(self) -> None:
        for field, value in (("strength", "invalid"), ("direction", "invalid")):
            evidence = [self.evidence("bad", "PM2", "moderate", "pathogenic")]
            evidence[0][field] = value

            status, payload = self.request(
                "POST", "/analysis/variants", self.valid_request(evidence)
            )

            self.assertEqual(status, 400)
            self.assertEqual(payload["error"]["code"], "invalid_request")

    def test_malformed_evidence_returns_bad_request(self) -> None:
        evidence = [self.evidence("bad", "PM2", "moderate", "pathogenic")]
        del evidence[0]["summary"]

        status, payload = self.request(
            "POST", "/analysis/variants", self.valid_request(evidence)
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")

    def test_unsupported_method_returns_method_not_allowed(self) -> None:
        status, payload = self.request("GET", "/analysis/variants")

        self.assertEqual(status, 405)
        self.assertEqual(payload["error"]["code"], "method_not_allowed")

    def test_health_contract_remains_unchanged(self) -> None:
        status, payload = self.request("GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_identical_requests_return_equivalent_json(self) -> None:
        request = self.valid_request(
            [self.evidence("evidence-1", "PM2", "moderate", "pathogenic")]
        )

        first_status, first_payload = self.request(
            "POST", "/analysis/variants", request
        )
        second_status, second_payload = self.request(
            "POST", "/analysis/variants", request
        )

        self.assertEqual(first_status, second_status)
        self.assertEqual(first_payload, second_payload)

    def test_controller_delegates_to_application_service(self) -> None:
        expected = AnalysisResult(
            variant=Variant(gene="BRCA1", hgvs_notation="c.5266dupC"),
            classification=Classification.BENIGN,
            criteria_considered=(),
            evidence_used=(),
            decision_trace=("stub decision",),
        )
        request = self.valid_request()

        with patch("backend.api.controllers.run_variant_analysis", return_value=expected) as run:
            status, payload = self.request("POST", "/analysis/variants", request)

        self.assertEqual(status, 200)
        run.assert_called_once()
        self.assertEqual(payload["classification"], "benign")
        self.assertEqual(payload["decision_trace"], ["stub decision"])


if __name__ == "__main__":
    unittest.main()
