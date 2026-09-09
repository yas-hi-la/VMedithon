import json
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from backend.services.evidence_retrieval.clinvar import (
    ClinVarRetrievalError,
    normalize_clinvar_record,
    retrieve_clinvar_evidence,
)


class ClinVarServiceTest(unittest.TestCase):
    def response(self, payload: object) -> Mock:
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        response.read.return_value = json.dumps(payload).encode("utf-8")
        return response

    def test_successful_retrieval_normalizes_source_record_without_acmg_criterion(self) -> None:
        search = {"esearchresult": {"idlist": ["123"]}}
        summary = {
            "result": {
                "uids": ["123"],
                "123": {
                    "accession": "VCV000000123.1",
                    "title": "NM_007294.4(BRCA1):c.5266dupC",
                    "germline_classification": {
                        "description": "Pathogenic",
                        "review_status": "criteria provided, multiple submitters",
                        "last_evaluated": "2024/01/01",
                    },
                },
            }
        }

        with patch(
            "backend.services.evidence_retrieval.clinvar.urlopen",
            side_effect=[self.response(search), self.response(summary)],
        ):
            result = retrieve_clinvar_evidence("BRCA1", "c.5266dupC")

        self.assertEqual(result.status, "found")
        self.assertEqual(result.evidence[0].source, "ClinVar")
        self.assertEqual(result.evidence[0].source_ref, "VCV000000123.1")
        self.assertIn("Pathogenic", result.evidence[0].summary)

    def test_no_matching_result_returns_explicit_empty_state(self) -> None:
        search = {"esearchresult": {"idlist": ["123"]}}
        summary = {
            "result": {
                "uids": ["123"],
                "123": {"accession": "VCV000000123.1", "title": "BRCA1:c.1A>G"},
            }
        }

        with patch(
            "backend.services.evidence_retrieval.clinvar.urlopen",
            side_effect=[self.response(search), self.response(summary)],
        ):
            result = retrieve_clinvar_evidence("BRCA1", "c.5266dupC")

        self.assertEqual(result.status, "not_found")
        self.assertEqual(result.message, "No matching public evidence found")
        self.assertEqual(result.evidence, ())

    def test_malformed_response_is_reported(self) -> None:
        with patch(
            "backend.services.evidence_retrieval.clinvar.urlopen",
            return_value=self.response({"unexpected": "shape"}),
        ):
            with self.assertRaises(ClinVarRetrievalError):
                retrieve_clinvar_evidence("BRCA1", "c.5266dupC")

    def test_network_failure_is_reported(self) -> None:
        with patch(
            "backend.services.evidence_retrieval.clinvar.urlopen",
            side_effect=URLError("offline"),
        ):
            with self.assertRaises(ClinVarRetrievalError):
                retrieve_clinvar_evidence("BRCA1", "c.5266dupC")

    def test_normalization_does_not_convert_classification_to_acmg_criterion(self) -> None:
        evidence = normalize_clinvar_record(
            {
                "accession": "VCV000000123.1",
                "germline_classification": {"description": "Likely benign"},
            }
        )

        self.assertEqual(evidence.classification, "Likely benign")
        self.assertNotIn("PS3", evidence.summary)
        self.assertNotIn("PM2", evidence.summary)


if __name__ == "__main__":
    unittest.main()
