"""Transaction-aware persistence for submitted variant evidence."""

from collections.abc import Iterable
import sqlite3

from backend.analysis.types import EvidenceItem
from backend.models.variant import Variant
from backend.services.variant_service.evidence_repository import insert_evidence
from backend.services.variant_service.repository import (
    get_variant_by_identity,
    insert_variant,
)


def persist_variant_evidence(
    connection: sqlite3.Connection,
    variant: Variant,
    evidence: Iterable[EvidenceItem],
) -> tuple[Variant, tuple[EvidenceItem, ...]]:
    """Persist a variant and its evidence without committing the transaction.

    The caller owns the connection context and therefore controls commit or
    rollback for the complete variant/evidence batch.
    """
    if not isinstance(variant, Variant):
        raise TypeError("variant must be a Variant")

    evidence_items = tuple(evidence)
    persisted_variant = get_variant_by_identity(
        connection,
        variant.gene,
        variant.hgvs_notation,
    )
    if persisted_variant is None:
        persisted_variant = insert_variant(connection, variant)

    if persisted_variant.id is None:
        raise RuntimeError("persisted variant must have an id")

    for item in evidence_items:
        insert_evidence(connection, persisted_variant.id, item)

    return persisted_variant, evidence_items