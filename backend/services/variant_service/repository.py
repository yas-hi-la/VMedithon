"""Persistence operations for variants."""

import sqlite3

from backend.models.variant import Variant


def insert_variant(connection: sqlite3.Connection, variant: Variant) -> Variant:
    cursor = connection.execute(
        """
        INSERT INTO variants (gene, hgvs_notation)
        VALUES (?, ?)
        """,
        (variant.gene, variant.hgvs_notation),
    )
    return Variant(
        id=cursor.lastrowid,
        gene=variant.gene,
        hgvs_notation=variant.hgvs_notation,
    )


def get_variant(connection: sqlite3.Connection, variant_id: int) -> Variant | None:
    row = connection.execute(
        """
        SELECT id, gene, hgvs_notation
        FROM variants
        WHERE id = ?
        """,
        (variant_id,),
    ).fetchone()
    return Variant.from_row(row) if row is not None else None


def get_variant_by_identity(
    connection: sqlite3.Connection,
    gene: str,
    hgvs_notation: str,
) -> Variant | None:
    row = connection.execute(
        """
        SELECT id, gene, hgvs_notation
        FROM variants
        WHERE gene = ? AND hgvs_notation = ?
        """,
        (gene, hgvs_notation),
    ).fetchone()
    return Variant.from_row(row) if row is not None else None
