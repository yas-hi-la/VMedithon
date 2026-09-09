"""Application use case combining evidence persistence and analysis."""

from collections.abc import Callable, Iterable
import sqlite3

from backend.analysis.types import AnalysisResult, EvidenceItem
from backend.models.variant import Variant
from backend.services.variant_service.analysis_service import run_variant_analysis
from backend.services.variant_service.persistence_service import persist_variant_evidence

PersistenceOperation = Callable[
    [sqlite3.Connection, Variant, Iterable[EvidenceItem]],
    tuple[Variant, tuple[EvidenceItem, ...]],
]
AnalysisOperation = Callable[
    [Variant, Iterable[EvidenceItem]],
    AnalysisResult,
]


def persist_and_analyze_variant(
    connection: sqlite3.Connection,
    variant: Variant,
    evidence: Iterable[EvidenceItem],
    persistence_operation: PersistenceOperation = persist_variant_evidence,
    analysis_operation: AnalysisOperation = run_variant_analysis,
) -> AnalysisResult:
    """Persist one submission and analyze the exact submitted evidence atomically."""
    if not isinstance(connection, sqlite3.Connection):
        raise TypeError("connection must be a sqlite3.Connection")
    if not isinstance(variant, Variant):
        raise TypeError("variant must be a Variant")

    evidence_items = tuple(evidence)
    with connection:
        persisted_variant, persisted_evidence = persistence_operation(
            connection,
            variant,
            evidence_items,
        )
        return analysis_operation(persisted_variant, persisted_evidence)
