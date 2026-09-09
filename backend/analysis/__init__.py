"""Deterministic, in-memory variant analysis domain."""

from backend.analysis.engine import analyze_variant
from backend.analysis.types import (
    AnalysisResult,
    Classification,
    CriterionCode,
    CriterionStrength,
    EvidenceDirection,
    EvidenceItem,
    EvidenceSource,
)

__all__ = [
    "AnalysisResult",
    "Classification",
    "CriterionCode",
    "CriterionStrength",
    "EvidenceDirection",
    "EvidenceItem",
    "EvidenceSource",
    "analyze_variant",
]
