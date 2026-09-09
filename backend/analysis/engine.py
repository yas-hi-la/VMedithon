"""Deterministic analysis over explicitly supplied evidence."""

from collections.abc import Iterable

from backend.analysis.types import (
    AnalysisResult,
    Classification,
    CriterionCode,
    EvidenceDirection,
    EvidenceItem,
)
from backend.models.variant import Variant


def analyze_variant(
    variant: Variant,
    evidence: Iterable[EvidenceItem],
) -> AnalysisResult:
    """Analyze supplied evidence without inferring missing clinical evidence.

    ACMG/AMP combination rules are intentionally not implemented yet. The
    engine therefore reports insufficient evidence unless explicitly supplied
    evidence conflicts, which it reports separately.
    """
    if not isinstance(variant, Variant):
        raise TypeError("variant must be a Variant")

    evidence_items = tuple(evidence)
    if any(not isinstance(item, EvidenceItem) for item in evidence_items):
        raise TypeError("evidence must contain only EvidenceItem values")
    evidence_ids = [item.evidence_id for item in evidence_items]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("evidence_id values must be unique")

    criteria_considered = tuple(
        sorted({item.criterion for item in evidence_items}, key=lambda item: item.value)
    )
    directions = {item.direction for item in evidence_items}

    if not evidence_items:
        classification = Classification.INSUFFICIENT_EVIDENCE
        trace = (
            "No structured evidence was supplied; missing evidence is not treated "
            "as benign or pathogenic.",
        )
    elif directions == {
        EvidenceDirection.PATHOGENIC,
        EvidenceDirection.BENIGN,
    }:
        classification = Classification.CONFLICTING
        trace = (
            "Both pathogenic and benign evidence are present; conflicting evidence "
            "is reported explicitly.",
        )
    else:
        classification = Classification.INSUFFICIENT_EVIDENCE
        trace = (
            "Structured evidence was supplied, but no ACMG/AMP combination rule "
            "is implemented yet; classification remains insufficient.",
        )

    return AnalysisResult(
        variant=variant,
        classification=classification,
        criteria_considered=criteria_considered,
        evidence_used=evidence_items,
        decision_trace=trace,
    )
