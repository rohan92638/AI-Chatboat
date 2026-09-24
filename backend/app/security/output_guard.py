import re

from dataclasses import dataclass


@dataclass
class OutputGuardResult:
    is_safe: bool
    reason: str | None = None


# Patterns that indicate the model may be exposing internal instructions.
SENSITIVE_OUTPUT_PATTERNS = [
    r"\b(system prompt|system instructions)\b",
    r"\bdeveloper instructions\b",
    r"\bhidden instructions\b",
    r"\bsecret system message\b",
]


def validate_output(
    text: str,
    max_length: int = 12000,
) -> OutputGuardResult:
    """
    Perform basic safety checks on model output.

    This is an application-level guard.
    It is not a complete moderation system.
    """

    if not text or not text.strip():
        return OutputGuardResult(
            is_safe=False,
            reason="empty_output",
        )

    if len(text) > max_length:
        return OutputGuardResult(
            is_safe=False,
            reason="output_too_long",
        )

    for pattern in SENSITIVE_OUTPUT_PATTERNS:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return OutputGuardResult(
                is_safe=False,
                reason="possible_instruction_leakage",
            )

    return OutputGuardResult(
        is_safe=True,
    )


def validate_stream_chunk(
    chunk: str,
    buffer: str = "",
    max_buffer_size: int = 500,
):
    """
    Validate one streaming chunk while keeping
    a rolling buffer to detect patterns split
    across multiple chunks.
    """

    combined_text = buffer + chunk

    for pattern in SENSITIVE_OUTPUT_PATTERNS:
        if re.search(
            pattern,
            combined_text,
            flags=re.IGNORECASE,
        ):
            return (
                False,
                "possible_instruction_leakage",
                combined_text[-max_buffer_size:],
            )

    new_buffer = combined_text[-max_buffer_size:]

    return (
        True,
        None,
        new_buffer,
    )