"""Persistence operations for explicitly submitted variant evidence."""

import sqlite3

from backend.analysis.types import (
    CriterionCode,
    CriterionStrength,
    EvidenceDirection,
    EvidenceItem,
    EvidenceSource,
)


def insert_evidence(
    connection: sqlite3.Connection,
    variant_id: int,
    evidence: EvidenceItem,
) -> EvidenceItem:
    connection.execute(
        """
        INSERT INTO variant_evidence (
            variant_id,
            evidence_id,
            criterion,
            strength,
            direction,
            source_name,
            source_reference,
            summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            variant_id,
            evidence.evidence_id,
            evidence.criterion.value,
            evidence.strength.value,
            evidence.direction.value,
            evidence.source.name,
            evidence.source.reference,
            evidence.summary,
        ),
    )
    return evidence


def get_evidence_for_variant(
    connection: sqlite3.Connection,
    variant_id: int,
) -> tuple[EvidenceItem, ...]:
    rows = connection.execute(
        """
        SELECT
            evidence_id,
            criterion,
            strength,
            direction,
            source_name,
            source_reference,
            summary
        FROM variant_evidence
        WHERE variant_id = ?
        ORDER BY id ASC
        """,
        (variant_id,),
    ).fetchall()
    return tuple(
        EvidenceItem(
            evidence_id=row["evidence_id"],
            criterion=CriterionCode(row["criterion"]),
            strength=CriterionStrength(row["strength"]),
            direction=EvidenceDirection(row["direction"]),
            source=EvidenceSource(
                name=row["source_name"],
                reference=row["source_reference"],
            ),
            summary=row["summary"],
        )
        for row in rows
    )