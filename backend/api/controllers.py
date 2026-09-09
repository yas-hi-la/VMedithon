"""Request controllers for the API layer."""

from backend.services.health_service import get_health_status


def health_controller() -> dict[str, str]:
    return get_health_status()
