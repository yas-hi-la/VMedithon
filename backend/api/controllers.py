"""Request controllers for the API layer."""

from typing import Any

from backend.api.analysis_requests import parse_analysis_request
from backend.api.serializers import serialize_analysis_result
from backend.services.health_service import get_health_status
from backend.services.variant_service.analysis_service import run_variant_analysis


def health_controller() -> dict[str, str]:
    return get_health_status()


def analysis_controller(payload: object) -> dict[str, Any]:
    request = parse_analysis_request(payload)
    result = run_variant_analysis(request.variant, request.evidence)
    return serialize_analysis_result(result)
