"""Domain model for a submitted genetic variant."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Variant:
    gene: str
    hgvs_notation: str
    id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.gene, str) or not self.gene.strip():
            raise ValueError("gene must be a non-empty string")
        if not isinstance(self.hgvs_notation, str) or not self.hgvs_notation.strip():
            raise ValueError("hgvs_notation must be a non-empty string")

    @classmethod
    def from_row(cls, row: Any) -> "Variant":
        return cls(
            id=row["id"],
            gene=row["gene"],
            hgvs_notation=row["hgvs_notation"],
        )
