"""Deterministic, in-memory variant analysis domain."""

from backend.analysis.engine import analyze_variant
from backend.analysis.types import (
    AnalysisResult,
    AnalysisStatus,
    Classification,
    CriterionEvaluation,
    CriterionCode,
    CriterionStrength,
    EvidenceDirection,
    EvidenceItem,
    EvidenceSource,
    RuleEvaluation,
)

__all__ = [
    "AnalysisResult",
    "AnalysisStatus",
    "Classification",
    "CriterionEvaluation",
    "CriterionCode",
    "CriterionStrength",
    "EvidenceDirection",
    "EvidenceItem",
    "EvidenceSource",
    "RuleEvaluation",
    "analyze_variant",
]
