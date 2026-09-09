"""API route definitions."""

from collections.abc import Callable
from typing import Any

from backend.api.controllers import (
    analysis_controller,
    health_controller,
    variant_evidence_controller,
)

Controller = Callable[..., dict[str, Any]]


ROUTES: dict[tuple[str, str], Controller] = {
    ("GET", "/health"): health_controller,
    ("GET", "/analysis/variants"): variant_evidence_controller,
    ("POST", "/analysis/variants"): analysis_controller,
}


def resolve_route(method: str, path: str) -> Controller | None:
    return ROUTES.get((method.upper(), path))


def route_exists(path: str) -> bool:
    return any(route_path == path for _, route_path in ROUTES)
