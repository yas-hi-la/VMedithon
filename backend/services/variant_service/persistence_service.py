"""Transaction-aware persistence for submitted variant evidence."""

from collections.abc import Iterable
import sqlite3

from backend.analysis.types import EvidenceItem
from backend.models.variant import Variant
from backend.services.variant_service.evidence_repository import (
    get_evidence_for_variant,
    insert_evidence,
)
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

    Identical evidence submissions are treated as safe retries. A submission
    that mixes existing evidence with new evidence remains a conflict.
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

    existing_evidence = {
        item.evidence_id: item
        for item in get_evidence_for_variant(
            connection,
            persisted_variant.id,
        )
    }

    duplicate_items = [
        item
        for item in evidence_items
        if item.evidence_id in existing_evidence
    ]

    new_items = [
        item
        for item in evidence_items
        if item.evidence_id not in existing_evidence
    ]

    # Preserve conflict behavior when a request mixes existing
    # evidence with genuinely new evidence.
    if duplicate_items and new_items:
        raise sqlite3.IntegrityError(
            "Submitted data conflicts with existing data"
        )

    # Allow an exact retry of already-persisted evidence.
    if duplicate_items:
        for item in duplicate_items:
            if existing_evidence[item.evidence_id] != item:
                raise sqlite3.IntegrityError(
                    "Submitted data conflicts with existing data"
                )

        return persisted_variant, tuple(
            existing_evidence[item.evidence_id]
            for item in evidence_items
        )

    # Persist genuinely new evidence.
    for item in new_items:
        insert_evidence(
            connection,
            persisted_variant.id,
            item,
        )

    return persisted_variant, tuple(new_items)