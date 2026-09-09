"""Request controllers for the API layer."""

from typing import Any

from backend.api.analysis_requests import parse_analysis_request
from backend.api.serializers import (
    serialize_analysis_result,
    serialize_variant_with_evidence,
)
from backend.api.variant_queries import parse_variant_lookup
from backend.services.health_service import get_health_status
from backend.services.evidence_retrieval.clinvar import retrieve_clinvar_evidence
from backend.services.variant_service.persisted_analysis_service import (
    persist_and_analyze_variant_from_environment,
)
from backend.services.variant_service.read_service import (
    get_variant_with_evidence_from_environment,
)


def health_controller() -> dict[str, str]:
    return get_health_status()


def analysis_controller(payload: object) -> dict[str, Any]:
    request = parse_analysis_request(payload)
    result = persist_and_analyze_variant_from_environment(
        request.variant,
        request.evidence,
    )
    return serialize_analysis_result(result)


def variant_evidence_controller(query_string: str) -> dict[str, Any]:
    lookup = parse_variant_lookup(query_string)
    result = get_variant_with_evidence_from_environment(
        lookup.gene,
        lookup.hgvs_notation,
    )
    return serialize_variant_with_evidence(result)


def external_evidence_controller(gene: str, hgvs_notation: str) -> dict[str, Any]:
    result = retrieve_clinvar_evidence(gene, hgvs_notation)
    return {
        "source": result.source,
        "status": result.status,
        "message": result.message,
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "criterion": None,
                "strength": None,
                "direction": None,
                "source": {
                    "name": item.source,
                    "reference": item.source_ref,
                },
                "summary": item.summary,
                "metadata": {
                    "classification": item.classification,
                    "review_status": item.review_status,
                    "last_evaluated": item.last_evaluated,
                },
            }
            for item in result.evidence
        ],
    }
