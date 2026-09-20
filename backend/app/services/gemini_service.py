import logging

from google import genai
from google.genai import types
import time
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from app.core.config import settings
from app.prompts.chat_prompt import USER_PROMPT_TEMPLATE


logger = logging.getLogger(__name__)


def is_retryable_error(exception: Exception) -> bool:
    error_str = str(exception).upper()

    return (
        "503" in error_str
        or "429" in error_str
        or "UNAVAILABLE" in error_str
    )


class GeminiService:

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    @retry(
        wait=wait_exponential(
            multiplier=1,
            min=2,
            max=10,
        ),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
    def generate_response(
        self,
        user_message: str,
        request_id: str,
        history: list,
    ):
        try:
            logger.info(
                "request_id=%s | Sending request to Gemini",
                request_id,
            )

            # Create current user prompt
            user_prompt = USER_PROMPT_TEMPLATE.format(
                user_message=user_message
            )

            # Build Gemini conversation contents
            contents = []

            for message in history:
                role = (
                    "model"
                    if message["role"] == "assistant"
                    else "user"
                )

                contents.append(
                    types.Content(
                        role=role,
                        parts=[
                            types.Part.from_text(
                                text=message["content"]
                            )
                        ],
                    )
                )

            # Add current user message
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=user_prompt
                        )
                    ],
                )
            )

            # Send conversation history + current message to Gemini
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=settings.SYSTEM_PROMPT,

                    temperature=0.3,
                ),
            )

            # Log token usage
            logger.info(
                "request_id=%s | Token usage: %s",
                request_id,
                response.usage_metadata,
            )

            logger.info(
                "request_id=%s | Gemini response received",
                request_id,
            )

            return {
                "response": response.text,
                "model": settings.GEMINI_MODEL,
                "usage_metadata": response.usage_metadata,
            }

        except Exception:
            logger.exception(
                "request_id=%s | Gemini API request failed",
                request_id,
            )
            raise

    def generate_stream(
        self,
        user_message: str,
        request_id: str,
        history: list,
        usage_container: dict = None,
    ):
        # Create current user prompt
        user_prompt = USER_PROMPT_TEMPLATE.format(
            user_message=user_message
        )

        # Build Gemini conversation contents
        contents = []

        for message in history:
            role = (
                "model"
                if message["role"] == "assistant"
                else "user"
            )

            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(
                            text=message["content"]
                        )
                    ],
                )
            )

        # Add current user message
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=user_prompt
                    )
                ],
            )
        )

        max_attempts = 5
        attempt = 1
        wait_time = 2
        yielded_any = False

        while attempt <= max_attempts:
            try:
                logger.info(
                    "request_id=%s | Starting Gemini streaming request (attempt %s)",
                    request_id, attempt
                )

                # Start Gemini streaming
                response_stream = (
                    self.client.models.generate_content_stream(
                        model=settings.GEMINI_MODEL,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=settings.SYSTEM_PROMPT,

                            temperature=0.3,
                        ),
                    )
                )

                # Send each chunk as it arrives
                for chunk in response_stream:
                    if (
                        chunk.usage_metadata is not None
                        and usage_container is not None
                    ):
                        usage_container["usage_metadata"] = (
                            chunk.usage_metadata
                        )

                    if chunk.text:
                        yield chunk.text
                        yielded_any = True

                logger.info(
                    "request_id=%s | Gemini streaming completed",
                    request_id,
                )
                return

            except Exception as e:
                if not yielded_any and is_retryable_error(e) and attempt < max_attempts:
                    logger.warning(
                        "request_id=%s | Retryable error: %s. Retrying in %s seconds...",
                        request_id, str(e), wait_time
                    )
                    time.sleep(wait_time)
                    attempt += 1
                    wait_time = min(wait_time * 2, 10)
                else:
                    logger.exception(
                        "request_id=%s | Gemini streaming failed",
                        request_id,
                    )
                    raise