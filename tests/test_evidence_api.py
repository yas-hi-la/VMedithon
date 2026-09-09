import json
from http.client import HTTPConnection
import threading
import unittest
from unittest.mock import patch

from backend.api.server import create_server
from backend.config.settings import Settings
from backend.services.evidence_retrieval.clinvar import (
    EvidenceRetrievalResult,
    RetrievedEvidence,
)


class EvidenceApiTest(unittest.TestCase):
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

    def test_clinvar_endpoint_returns_source_metadata_without_acmg_mapping(self) -> None:
        retrieval = EvidenceRetrievalResult(
            source="ClinVar",
            status="found",
            message="Found 1 ClinVar record(s)",
            evidence=(
                RetrievedEvidence(
                    evidence_id="clinvar-VCV1",
                    source="ClinVar",
                    source_ref="VCV1",
                    summary="Asserted classification: Pathogenic.",
                    classification="Pathogenic",
                    review_status="criteria provided",
                    last_evaluated="2024/01/01",
                ),
            ),
        )
        with patch(
            "backend.api.controllers.retrieve_clinvar_evidence",
            return_value=retrieval,
        ):
            connection = HTTPConnection("127.0.0.1", self.port)
            connection.request("GET", "/evidence/BRCA1/c.5266dupC")
            response = connection.getresponse()
            payload = json.loads(response.read())
            connection.close()

        self.assertEqual(response.status, 200)
        item = payload["evidence"][0]
        self.assertEqual(item["source"]["name"], "ClinVar")
        self.assertIsNone(item["criterion"])
        self.assertEqual(item["metadata"]["classification"], "Pathogenic")


if __name__ == "__main__":
    unittest.main()
