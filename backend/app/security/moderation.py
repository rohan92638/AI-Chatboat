import re
from dataclasses import dataclass


@dataclass
class ModerationResult:
    is_safe: bool
    reason: str | None = None


MODERATION_PATTERNS = [
    (
        r"\b(kill|murder|assassinate)\b",
        "violent_content",
    ),
    (
        r"\b(make|build|create)\b.{0,50}\b(bomb|explosive)\b",
        "dangerous_activity",
    ),
    (
        r"\b(steal|rob|hack)\b.{0,50}\b(password|account|credentials)\b",
        "criminal_activity",
    ),
]


def moderate_text(text: str) -> ModerationResult:
    """
    Perform basic application-level moderation.

    This is a simple rule-based layer and is not
    a complete content moderation system.
    """

    if not text or not text.strip():
        return ModerationResult(
            is_safe=False,
            reason="empty_content",
        )

    for pattern, reason in MODERATION_PATTERNS:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return ModerationResult(
                is_safe=False,
                reason=reason,
            )

    return ModerationResult(
        is_safe=True,
    )