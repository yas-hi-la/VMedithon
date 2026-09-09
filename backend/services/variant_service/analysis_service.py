"""Application use case for running deterministic variant analysis."""

from collections.abc import Callable, Iterable

from backend.analysis.engine import analyze_variant as run_analysis_engine
from backend.analysis.types import AnalysisResult, EvidenceItem
from backend.models.variant import Variant

AnalysisEngine = Callable[[Variant, Iterable[EvidenceItem]], AnalysisResult]


def run_variant_analysis(
    variant: Variant | None,
    evidence: Iterable[EvidenceItem] | None,
    analysis_engine: AnalysisEngine = run_analysis_engine,
) -> AnalysisResult:
    """Coordinate variant analysis without implementing scientific rules."""
    if variant is None:
        raise ValueError("variant is required")
    if not isinstance(variant, Variant):
        raise TypeError("variant must be a Variant")
    if evidence is None:
        raise ValueError("evidence is required")

    evidence_items = tuple(evidence)
    return analysis_engine(variant, evidence_items)
