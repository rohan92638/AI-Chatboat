import logging

import ollama

from app.core.config import settings
from app.prompts.chat_prompt import USER_PROMPT_TEMPLATE


logger = logging.getLogger(__name__)


class UsageMetadata:
    def __init__(self, prompt, candidates, total):
        self.prompt_token_count = prompt
        self.candidates_token_count = candidates
        self.total_token_count = total

class OllamaService:

    def __init__(self):
        self.client = ollama.Client(
            host=settings.OLLAMA_BASE_URL,
        )

    def generate_response(
        self,
        user_message: str,
        request_id: str,
        history: list,
    ):
        try:
            logger.info(
                "request_id=%s | Sending request to Ollama (%s)",
                request_id,
                settings.OLLAMA_MODEL,
            )

            # Create current user prompt
            user_prompt = USER_PROMPT_TEMPLATE.format(
                user_message=user_message
            )

            # Build Ollama messages list
            messages = []

            # Add system prompt as the first message
            messages.append({
                "role": "system",
                "content": settings.SYSTEM_PROMPT,
            })

            # Add conversation history
            for message in history:
                messages.append({
                    "role": message["role"],
                    "content": message["content"],
                })

            # Add current user message
            messages.append({
                "role": "user",
                "content": user_prompt,
            })

            # Send to Ollama
            response = self.client.chat(
                model=settings.OLLAMA_MODEL,
                messages=messages,
            )

            prompt_eval = getattr(response, "prompt_eval_count", 0) or 0
            eval_count = getattr(response, "eval_count", 0) or 0
            total_count = prompt_eval + eval_count

            usage_metadata = UsageMetadata(
                prompt=prompt_eval,
                candidates=eval_count,
                total=total_count,
            )

            # Log token usage if available
            logger.info(
                "request_id=%s | Ollama usage: prompt_eval_count=%s, eval_count=%s",
                request_id,
                prompt_eval,
                eval_count,
            )

            logger.info(
                "request_id=%s | Ollama response received",
                request_id,
            )

            return {
                "response": response.message.content,
                "model": settings.OLLAMA_MODEL,
                "usage_metadata": usage_metadata,
            }

        except ollama.ResponseError as e:
            logger.error(
                "request_id=%s | Ollama API error: %s",
                request_id,
                str(e),
            )
            raise

        except ConnectionError:
            logger.error(
                "request_id=%s | Cannot connect to Ollama at %s",
                request_id,
                settings.OLLAMA_BASE_URL,
            )
            raise

        except Exception:
            logger.exception(
                "request_id=%s | Ollama request failed",
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
        try:
            logger.info(
                "request_id=%s | Starting Ollama stream (%s)",
                request_id,
                settings.OLLAMA_MODEL,
            )

            user_prompt = USER_PROMPT_TEMPLATE.format(
                user_message=user_message
            )

            messages = []
            messages.append({
                "role": "system",
                "content": settings.SYSTEM_PROMPT,
            })

            for message in history:
                messages.append({
                    "role": message["role"],
                    "content": message["content"],
                })

            messages.append({
                "role": "user",
                "content": user_prompt,
            })

            stream = self.client.chat(
                model=settings.OLLAMA_MODEL,
                messages=messages,
                stream=True,
            )

            for chunk in stream:
                if chunk.message and chunk.message.content:
                    yield chunk.message.content

                if getattr(chunk, "done", False) and usage_container is not None:
                    prompt_eval = getattr(chunk, "prompt_eval_count", 0) or 0
                    eval_count = getattr(chunk, "eval_count", 0) or 0
                    
                    usage_container["usage_metadata"] = UsageMetadata(
                        prompt=prompt_eval,
                        candidates=eval_count,
                        total=prompt_eval + eval_count,
                    )
                    
                    logger.info(
                        "request_id=%s | Ollama stream finished. Usage: prompt_eval_count=%s, eval_count=%s",
                        request_id,
                        prompt_eval,
                        eval_count,
                    )

        except ollama.ResponseError as e:
            logger.error(
                "request_id=%s | Ollama streaming API error: %s",
                request_id,
                str(e),
            )
            raise

        except ConnectionError:
            logger.error(
                "request_id=%s | Cannot connect to Ollama at %s",
                request_id,
                settings.OLLAMA_BASE_URL,
            )
            raise

        except Exception:
            logger.exception(
                "request_id=%s | Ollama streaming failed",
                request_id,
            )
            raise
