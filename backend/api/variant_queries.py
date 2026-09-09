"""Query-string parsing for variant read requests."""

from dataclasses import dataclass
from urllib.parse import parse_qs


@dataclass(frozen=True)
class VariantLookup:
    gene: str
    hgvs_notation: str


def _single_query_value(query: dict[str, list[str]], name: str) -> str:
    values = query.get(name)
    if values is None or len(values) != 1 or not values[0].strip():
        raise ValueError(f"{name} must be a non-empty query parameter")
    return values[0]


def parse_variant_lookup(query_string: str) -> VariantLookup:
    if not isinstance(query_string, str):
        raise TypeError("query string must be a string")

    query = parse_qs(query_string, keep_blank_values=True)
    return VariantLookup(
        gene=_single_query_value(query, "gene"),
        hgvs_notation=_single_query_value(query, "hgvs_notation"),
    )
