"""Business service for backend availability checks."""


def get_health_status() -> dict[str, str]:
    return {"status": "ok"}
