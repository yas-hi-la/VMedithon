import json
from http.client import HTTPConnection
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from backend.analysis.types import AnalysisResult, Classification
from backend.api.server import create_server
from backend.config.settings import Settings
from backend.database.config import DatabaseSettings
from backend.database.connection import connect
from backend.database.initialize import initialize_database
from backend.models.variant import Variant


class AnalysisApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.database_path = Path(cls.temp_dir.name) / "api.db"
        cls.environment = patch.dict(
            os.environ,
            {"DB_PATH": str(cls.database_path)},
        )
        cls.environment.start()
        initialize_database(DatabaseSettings(path=cls.database_path))
        cls.server = create_server(Settings(host="127.0.0.1", port=0))
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    def setUp(self) -> None:
        with connect(DatabaseSettings(path=self.database_path)) as connection:
            connection.execute("DELETE FROM variant_evidence")
            connection.execute("DELETE FROM variants")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()
        cls.environment.stop()
        cls.temp_dir.cleanup()

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
        with connect(DatabaseSettings(path=self.database_path)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variant_evidence").fetchone()[0],
                0,
            )

    def test_one_evidence_item_is_persisted(self) -> None:
        evidence = [self.evidence("one", "PM2", "moderate", "pathogenic")]

        status, payload = self.request(
            "POST", "/analysis/variants", self.valid_request(evidence)
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["classification"], "insufficient_evidence")
        with connect(DatabaseSettings(path=self.database_path)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variants").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variant_evidence").fetchone()[0],
                1,
            )

    def test_multiple_evidence_items_are_persisted_and_analyzed(self) -> None:
        evidence = [
            self.evidence("functional", "PS3", "strong", "pathogenic"),
            self.evidence("population", "PM2", "moderate", "pathogenic"),
        ]

        status, payload = self.request(
            "POST", "/analysis/variants", self.valid_request(evidence)
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["classification"], "likely_pathogenic")
        with connect(DatabaseSettings(path=self.database_path)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variant_evidence").fetchone()[0],
                2,
            )

    def test_repeated_variant_request_reuses_variant_and_adds_evidence(self) -> None:
        first = self.valid_request(
            [self.evidence("first", "PM2", "moderate", "pathogenic")]
        )
        second = self.valid_request(
            [self.evidence("second", "PP3", "supporting", "pathogenic")]
        )

        self.assertEqual(self.request("POST", "/analysis/variants", first)[0], 200)
        self.assertEqual(self.request("POST", "/analysis/variants", second)[0], 200)

        with connect(DatabaseSettings(path=self.database_path)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variants").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variant_evidence").fetchone()[0],
                2,
            )

    def test_duplicate_evidence_returns_conflict_and_rolls_back_new_rows(self) -> None:
        first = self.valid_request(
            [self.evidence("existing", "PM2", "moderate", "pathogenic")]
        )
        duplicate_submission = self.valid_request(
            [
                self.evidence("new", "PP3", "supporting", "pathogenic"),
                self.evidence("existing", "PM2", "moderate", "pathogenic"),
            ]
        )

        self.assertEqual(self.request("POST", "/analysis/variants", first)[0], 200)
        status, payload = self.request(
            "POST", "/analysis/variants", duplicate_submission
        )

        self.assertEqual(status, 409)
        self.assertEqual(payload["error"]["code"], "persistence_conflict")
        with connect(DatabaseSettings(path=self.database_path)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variants").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM variant_evidence").fetchone()[0],
                1,
            )

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
        request = self.valid_request()

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

        with patch(
            "backend.api.controllers.persist_and_analyze_variant_from_environment",
            return_value=expected,
        ) as run:
            status, payload = self.request("POST", "/analysis/variants", request)

        self.assertEqual(status, 200)
        run.assert_called_once()
        self.assertEqual(payload["classification"], "benign")
        self.assertEqual(payload["decision_trace"], ["stub decision"])


if __name__ == "__main__":
    unittest.main()
