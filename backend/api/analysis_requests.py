"""Parsing and mapping for the variant analysis request contract."""

from dataclasses import dataclass
from typing import Any

from backend.analysis.types import (
    CriterionCode,
    CriterionStrength,
    EvidenceDirection,
    EvidenceItem,
    EvidenceSource,
)
from backend.models.variant import Variant


@dataclass(frozen=True)
class AnalysisRequest:
    variant: Variant
    evidence: tuple[EvidenceItem, ...]


def _require_object(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_string(
    payload: dict[str, Any], field_name: str, label: str | None = None
) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label or field_name} must be a non-empty string")
    return value


def _parse_evidence(payload: object) -> EvidenceItem:
    item = _require_object(payload, "evidence item")
    source_payload = _require_object(item.get("source"), "source")
    reference = source_payload.get("reference")
    if reference is not None and not isinstance(reference, str):
        raise ValueError("source.reference must be a string or null")

    try:
        criterion = CriterionCode(item.get("criterion"))
        strength = CriterionStrength(item.get("strength"))
        direction = EvidenceDirection(item.get("direction"))
    except (TypeError, ValueError) as error:
        raise ValueError("invalid criterion, strength, or direction") from error

    return EvidenceItem(
        evidence_id=_require_string(item, "evidence_id"),
        criterion=criterion,
        strength=strength,
        direction=direction,
        source=EvidenceSource(
            name=_require_string(source_payload, "name", "source.name"),
            reference=reference,
        ),
        summary=_require_string(item, "summary"),
    )


def parse_analysis_request(payload: object) -> AnalysisRequest:
    request = _require_object(payload, "request body")
    variant_payload = _require_object(request.get("variant"), "variant")
    evidence_payload = request.get("evidence")
    if not isinstance(evidence_payload, list):
        raise ValueError("evidence must be an array")

    variant = Variant(
        gene=_require_string(variant_payload, "gene", "variant.gene"),
        hgvs_notation=_require_string(
            variant_payload, "hgvs_notation", "variant.hgvs_notation"
        ),
    )
    evidence = tuple(_parse_evidence(item) for item in evidence_payload)
    return AnalysisRequest(variant=variant, evidence=evidence)
