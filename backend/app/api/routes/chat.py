import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.request_id import generate_request_id
from app.database.connection import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.context_manager import ContextManager
from app.services.gemini_service import GeminiService
from app.services.memory_service import MemoryService
from app.services.token_manager import TokenManager
from app.services.usage_service import UsageService
import time


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1",
    tags=["Chat"],
)


gemini_service = GeminiService()
memory_service = MemoryService()
context_manager = ContextManager()
token_manager = TokenManager()
usage_service = UsageService()


# ============================================================
# NORMAL CHAT ENDPOINT
# ============================================================

@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    request_id = generate_request_id()

    try:
        logger.info(
            "request_id=%s | Chat request received",
            request_id,
        )

        # 1. Get or create conversation
        conversation = memory_service.get_or_create_conversation(
            db,
            request.conversation_id,
        )

        # 2. Get conversation history from PostgreSQL
        messages = memory_service.get_history(
            db,
            conversation,
            limit=settings.MAX_HISTORY_MESSAGES,
        )

        # 3. Select relevant context
        context_result = context_manager.build_context(
            messages,
            current_message=request.message,
            max_tokens=settings.MAX_CONTEXT_TOKENS,
        )

        history = context_result["history"]

        history_message_count = context_result[
            "history_message_count"
        ]

        history_tokens = context_result[
            "history_tokens"
        ]

        token_usage = token_manager.build_usage(
            history_tokens=history_tokens,
            user_message=request.message,
            system_prompt=settings.SYSTEM_PROMPT,
            max_context_tokens=settings.MAX_CONTEXT_TOKENS,
        )

        budget_validation = token_manager.validate_budget(token_usage)
        if not budget_validation["valid"]:
            logger.warning(
                "request_id=%s | Context budget exceeded: %s > %s",
                request_id,
                token_usage["total_tokens"],
                token_usage["max_tokens"],
            )
            raise HTTPException(
                status_code=413,
                detail=budget_validation["reason"],
            )

        logger.info(
            "request_id=%s | Context messages=%s | "
            "System prompt tokens=%s | "
            "History tokens=%s | "
            "User tokens=%s | "
            "Total context tokens=%s | "
            "Remaining context tokens=%s | "
            "Max context tokens=%s",
            request_id,
            history_message_count,
            token_usage["system_prompt_tokens"],
            token_usage["history_tokens"],
            token_usage["user_tokens"],
            token_usage["total_tokens"],
            token_usage["remaining_tokens"],
            token_usage["max_tokens"],
        )

        # 6. Generate normal Gemini response
        start_time = time.perf_counter()
        result = gemini_service.generate_response(
            request.message,
            request_id,
            history,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 7. Build final token usage structure
        estimated_output_tokens = token_manager.estimate_text_tokens(
            result["response"]
        )

        final_usage = token_manager.build_final_usage(
            token_usage=token_usage,
            usage_metadata=result.get("usage_metadata"),
            estimated_output_tokens=estimated_output_tokens,
        )

        usage_record = usage_service.build_usage_record(
            request_id=request_id,
            conversation_id=request.conversation_id,
            model=settings.GEMINI_MODEL,
            request_type="normal",
            final_usage=final_usage,
            status="success",
            latency_ms=latency_ms,
        )

        logger.info(
            "request_id=%s | Final Token Usage: %s",
            request_id,
            final_usage,
        )

        logger.info(
            "request_id=%s | Usage Record: %s",
            request_id,
            usage_record,
        )

        try:
            usage_service.save_usage(
                db,
                usage_record,
            )
        except Exception as e:
            logger.error(
                "request_id=%s | Failed to save usage record: %s",
                request_id,
                str(e),
            )

        # 8. Save user message
        memory_service.save_user_message(
            db,
            conversation,
            request.message,
        )

        # 9. Save assistant response
        memory_service.save_assistant_message(
            db,
            conversation,
            result["response"],
        )

        logger.info(
            "request_id=%s | Chat request completed",
            request_id,
        )

        return ChatResponse(
            response=result["response"],
            model=result["model"],
            request_id=request_id,
        )

    except Exception as e:
        logger.exception(
            "request_id=%s | Chat request failed",
            request_id,
        )

        error_msg = str(e).upper()

        if (
            "503" in error_msg
            or "UNAVAILABLE" in error_msg
        ):
            raise HTTPException(
                status_code=503,
                detail=(
                    "The AI service is currently experiencing "
                    "high demand. Please try again in a few moments."
                ),
            )

        if (
            "429" in error_msg
            or "RESOURCE_EXHAUSTED" in error_msg
        ):
            raise HTTPException(
                status_code=429,
                detail=(
                    "The AI service quota has been exceeded. "
                    "Please try again later."
                ),
            )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to generate AI response: {str(e)}"
            ),
        )


# ============================================================
# STREAMING CHAT ENDPOINT
# ============================================================

@router.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    request_id = generate_request_id()

    try:
        logger.info(
            "request_id=%s | Streaming chat request received",
            request_id,
        )

        # 1. Get or create conversation
        conversation = memory_service.get_or_create_conversation(
            db,
            request.conversation_id,
        )

        # 2. Get conversation history from PostgreSQL
        messages = memory_service.get_history(
            db,
            conversation,
            limit=settings.MAX_HISTORY_MESSAGES,
        )

        # 3. Select relevant context
        context_result = context_manager.build_context(
            messages,
            current_message=request.message,
            max_tokens=settings.MAX_CONTEXT_TOKENS,
        )

        history = context_result["history"]

        history_message_count = context_result[
            "history_message_count"
        ]

        history_tokens = context_result[
            "history_tokens"
        ]

        token_usage = token_manager.build_usage(
            history_tokens=history_tokens,
            user_message=request.message,
            system_prompt=settings.SYSTEM_PROMPT,
            max_context_tokens=settings.MAX_CONTEXT_TOKENS,
        )

        budget_validation = token_manager.validate_budget(token_usage)
        if not budget_validation["valid"]:
            logger.warning(
                "request_id=%s | Context budget exceeded: %s > %s",
                request_id,
                token_usage["total_tokens"],
                token_usage["max_tokens"],
            )
            raise HTTPException(
                status_code=413,
                detail=budget_validation["reason"],
            )

        logger.info(
            "request_id=%s | Context messages=%s | "
            "System prompt tokens=%s | "
            "History tokens=%s | "
            "User tokens=%s | "
            "Total context tokens=%s | "
            "Remaining context tokens=%s | "
            "Max context tokens=%s",
            request_id,
            history_message_count,
            token_usage["system_prompt_tokens"],
            token_usage["history_tokens"],
            token_usage["user_tokens"],
            token_usage["total_tokens"],
            token_usage["remaining_tokens"],
            token_usage["max_tokens"],
        )

        # 6. Start Gemini streaming
        stream_usage = {}

        start_time = time.perf_counter()
        stream = gemini_service.generate_stream(
            request.message,
            request_id,
            history,
            usage_container=stream_usage,
        )

        def stream_generator():
            full_response = ""
            stream_successful = False

            try:
                for chunk in stream:
                    full_response += chunk
                    yield chunk

                stream_successful = True

            except Exception:
                logger.exception(
                    "request_id=%s | Streaming error",
                    request_id,
                )

                yield (
                    "\n\n"
                    "[Error: Unable to complete AI response.]"
                )

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            status = "success" if stream_successful else "failure"

            # Build final token usage structure
            estimated_output_tokens = None
            if stream_successful and full_response:
                estimated_output_tokens = token_manager.estimate_text_tokens(
                    full_response
                )

            final_usage = token_manager.build_final_usage(
                token_usage=token_usage,
                usage_metadata=stream_usage.get("usage_metadata"),
                estimated_output_tokens=estimated_output_tokens,
            )

            usage_record = usage_service.build_usage_record(
                request_id=request_id,
                conversation_id=request.conversation_id,
                model=settings.GEMINI_MODEL,
                request_type="streaming",
                final_usage=final_usage,
                status=status,
                latency_ms=latency_ms,
            )

            logger.info(
                "request_id=%s | Final Token Usage: %s",
                request_id,
                final_usage,
            )

            logger.info(
                "request_id=%s | Usage Record: %s",
                request_id,
                usage_record,
            )

            try:
                usage_service.save_usage(
                    db,
                    usage_record,
                )
            except Exception as e:
                logger.error(
                    "request_id=%s | Failed to save usage record: %s",
                    request_id,
                    str(e),
                )

            # Save messages only after streaming finishes
            # successfully.
            if stream_successful:

                memory_service.save_user_message(
                    db,
                    conversation,
                    request.message,
                )

                if full_response:
                    memory_service.save_assistant_message(
                        db,
                        conversation,
                        full_response,
                    )

                logger.info(
                    "request_id=%s | "
                    "Chat streaming completed successfully",
                    request_id,
                )

            else:

                logger.warning(
                    "request_id=%s | "
                    "Streaming failed. Messages were not saved.",
                    request_id,
                )

        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
        )

    except Exception as e:
        logger.exception(
            "request_id=%s | "
            "Failed to start streaming",
            request_id,
        )

        error_msg = str(e).upper()

        if (
            "503" in error_msg
            or "UNAVAILABLE" in error_msg
        ):
            raise HTTPException(
                status_code=503,
                detail=(
                    "The AI service is currently experiencing "
                    "high demand. Please try again in a few moments."
                ),
            )

        if (
            "429" in error_msg
            or "RESOURCE_EXHAUSTED" in error_msg
        ):
            raise HTTPException(
                status_code=429,
                detail=(
                    "The AI service quota has been exceeded. "
                    "Please try again later."
                ),
            )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to start AI streaming response."
            ),
        )