"""Read-only application workflow for persisted variant evidence."""

from dataclasses import dataclass
from collections.abc import Iterable
import sqlite3

from backend.analysis.types import EvidenceItem
from backend.database.config import DatabaseSettings
from backend.database.connection import connect
from backend.models.variant import Variant
from backend.services.variant_service.evidence_repository import get_evidence_for_variant
from backend.services.variant_service.repository import get_variant_by_identity


class VariantNotFoundError(LookupError):
    """Raised when a requested variant identity is not persisted."""


@dataclass(frozen=True)
class VariantWithEvidence:
    variant: Variant
    evidence: tuple[EvidenceItem, ...]


def get_variant_with_evidence(
    connection: sqlite3.Connection,
    gene: str,
    hgvs_notation: str,
) -> VariantWithEvidence:
    variant = get_variant_by_identity(connection, gene, hgvs_notation)
    if variant is None or variant.id is None:
        raise VariantNotFoundError("Variant not found")

    return VariantWithEvidence(
        variant=variant,
        evidence=get_evidence_for_variant(connection, variant.id),
    )


def get_variant_with_evidence_from_environment(
    gene: str,
    hgvs_notation: str,
) -> VariantWithEvidence:
    """Retrieve persisted variant evidence using configured SQLite storage."""
    settings = DatabaseSettings.from_environment()
    connection = connect(settings)
    try:
        return get_variant_with_evidence(connection, gene, hgvs_notation)
    finally:
        connection.close()
