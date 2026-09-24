import re
import unicodedata
from dataclasses import dataclass


@dataclass
class PromptInjectionResult:
    is_injection: bool
    reason: str | None = None
    matched_pattern: str | None = None


INJECTION_PATTERNS = [
    # ---------------------------------------------------------
    # 1. Instruction override
    # ---------------------------------------------------------
    (
        r"\b(ignore|disregard|override|bypass)\b"
        r".{0,80}\b"
        r"(previous|prior|above|earlier|original|system|"
        r"safety|security)?\s*"
        r"(instructions?|rules?|prompts?|policies?|restrictions?)\b",
        "instruction_override",
    ),

    # ---------------------------------------------------------
    # 2. Instruction deletion / reset
    # ---------------------------------------------------------
    (
        r"\b(forget|delete|remove|erase|discard)\b"
        r".{0,80}\b"
        r"(previous|prior|above|earlier|your|system)?\s*"
        r"(instructions?|rules?|prompts?|policies?)\b",
        "instruction_reset",
    ),

    # ---------------------------------------------------------
    # 3. Pretend previous instructions do not exist
    # ---------------------------------------------------------
    (
        r"\b(pretend|assume|imagine)\b"
        r".{0,80}\b"
        r"(previous|prior|earlier|system)?\s*"
        r"(instructions?|rules?|prompts?)\b"
        r".{0,50}\b"
        r"(don't|do not|never)\s+(exist|apply|matter)\b",
        "instruction_override",
    ),

    # ---------------------------------------------------------
    # 4. Unrestricted / uncensored role override
    # ---------------------------------------------------------
    (
        r"\b(you\s+are\s+now|act\s+as|behave\s+as|"
        r"pretend\s+to\s+be|role[-\s]?play\s+as)\b"
        r".{0,100}\b"
        r"(unrestricted|uncensored|unfiltered|unlimited|"
        r"without\s+restrictions?|without\s+rules?|"
        r"no\s+restrictions?|no\s+rules?)\b",
        "role_override",
    ),

    # ---------------------------------------------------------
    # 5. "Act as if you have no restrictions"
    # ---------------------------------------------------------
    (
        r"\b(act|behave|respond|operate)\b"
        r".{0,80}\b"
        r"(as\s+if|as\s+though)\b"
        r".{0,80}\b"
        r"(no\s+restrictions?|no\s+rules?|"
        r"without\s+restrictions?|without\s+rules?)\b",
        "role_override",
    ),

    # ---------------------------------------------------------
    # 6. System prompt extraction
    # ---------------------------------------------------------
    (
        r"\b(reveal|show|print|display|repeat|provide|"
        r"give|tell|expose|output|return)\b"
        r".{0,100}\b"
        r"(system\s+prompt|system\s+instructions?|"
        r"hidden\s+instructions?|internal\s+instructions?|"
        r"developer\s+instructions?)\b",
        "system_prompt_extraction",
    ),

    # ---------------------------------------------------------
    # 7. Ask what controls the model's behavior
    # ---------------------------------------------------------
    (
        r"\b(what|which|tell\s+me|describe|explain)\b"
        r".{0,100}\b"
        r"(instructions?|rules?|prompts?|configuration|"
        r"guidelines?)\b"
        r".{0,100}\b"
        r"(control|govern|define|determine|drive)\b"
        r".{0,100}\b"
        r"(your|the\s+assistant|the\s+model|your\s+behavior)\b",
        "system_prompt_extraction",
    ),

    # ---------------------------------------------------------
    # 8. Direct "what are your instructions?"
    # ---------------------------------------------------------
    (
        r"\b(what|what\s+are|show|tell)\b"
        r".{0,50}\b"
        r"(your|the)\b"
        r".{0,50}\b"
        r"(instructions?|rules?|system\s+prompt|"
        r"hidden\s+instructions?)\b",
        "system_prompt_extraction",
    ),

    # ---------------------------------------------------------
    # 9. Fake authority
    # ---------------------------------------------------------
    (
        r"\b(the\s+)?"
        r"(system\s+administrator|administrator|admin|"
        r"developer|system|authorized\s+user)\b"
        r".{0,100}\b"
        r"(authorized|approved|allowed|instructed|told|ordered)\b"
        r".{0,100}\b"
        r"(ignore|override|disable|bypass|remove|"
        r"disregard)\b",
        "fake_authority",
    ),

    # ---------------------------------------------------------
    # 10. Safety/security bypass
    # ---------------------------------------------------------
    (
        r"\b(bypass|disable|remove|turn\s+off|ignore|"
        r"circumvent)\b"
        r".{0,80}\b"
        r"(safety|security|guardrails?|restrictions?|"
        r"content\s+policy|policies?)\b",
        "safety_override",
    ),

    # ---------------------------------------------------------
    # 11. "No restrictions" without explicit role phrase
    # ---------------------------------------------------------
    (
        r"\b(no\s+restrictions?|without\s+restrictions?|"
        r"without\s+any\s+rules?|no\s+rules?)\b"
        r".{0,80}\b"
        r"(assistant|AI|model|chatbot|you)\b",
        "role_override",
    ),
]


def normalize_text(text: str) -> str:
    """
    Normalize user input before security checks.

    Handles:
    - Unicode normalization
    - lowercase conversion
    - repeated whitespace
    """

    normalized = unicodedata.normalize(
        "NFKC",
        text,
    )

    normalized = normalized.lower()

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def detect_prompt_injection(
    text: str,
) -> PromptInjectionResult:
    """
    Detect common prompt-injection patterns.

    This is a defensive heuristic layer.
    It is not a complete security boundary.
    """

    normalized_text = normalize_text(text)

    for pattern, reason in INJECTION_PATTERNS:
        if re.search(
            pattern,
            normalized_text,
            flags=re.IGNORECASE,
        ):
            return PromptInjectionResult(
                is_injection=True,
                reason=reason,
                matched_pattern=pattern,
            )

    return PromptInjectionResult(
        is_injection=False,
    )