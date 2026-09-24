import re
import unicodedata
from dataclasses import dataclass


@dataclass
class InputValidationResult:
    is_valid: bool
    reason: str | None = None


def normalize_input(text: str) -> str:
    """
    Normalize user input before processing.

    This does not remove meaningful content.
    It mainly normalizes Unicode and whitespace.
    """

    text = unicodedata.normalize("NFKC", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def validate_message(
    text: str,
    max_length: int = 4000,
) -> InputValidationResult:
    """
    Validate a user message before sending it to the AI provider.
    """

    if not text or not text.strip():
        return InputValidationResult(
            is_valid=False,
            reason="empty_message",
        )

    if len(text) > max_length:
        return InputValidationResult(
            is_valid=False,
            reason="message_too_long",
        )

    # Detect extremely long runs of the same character.
    # Example:
    # "aaaaaaaaaaaaaaaaaaaaaaaa..."
    if re.search(r"(.)\1{1000,}", text):
        return InputValidationResult(
            is_valid=False,
            reason="excessive_repeated_characters",
        )

    # Detect extremely large whitespace runs.
    if re.search(r"\s{1000,}", text):
        return InputValidationResult(
            is_valid=False,
            reason="excessive_whitespace",
        )

    return InputValidationResult(
        is_valid=True,
    )