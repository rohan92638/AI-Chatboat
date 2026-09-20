import uuid


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return uuid.uuid4().hex
