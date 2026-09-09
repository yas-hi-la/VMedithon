"""API route definitions."""

from collections.abc import Callable

from backend.api.controllers import health_controller

Controller = Callable[[], dict[str, str]]


ROUTES: dict[tuple[str, str], Controller] = {
    ("GET", "/health"): health_controller,
}


def resolve_route(method: str, path: str) -> Controller | None:
    return ROUTES.get((method.upper(), path))
