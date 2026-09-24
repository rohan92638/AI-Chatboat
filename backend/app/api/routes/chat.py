import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.request_id import generate_request_id
from app.core.rate_limiter import limiter
from app.database.connection import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.context_manager import ContextManager
from app.services.ai_provider import get_ai_service, get_active_model_name
from app.services.memory_service import MemoryService
from app.services.token_manager import TokenManager
from app.services.usage_service import UsageService
import time
from app.security.prompt_injection import (
    detect_prompt_injection,
)
from app.security.input_validator import (
    normalize_input,
    validate_message,
)
from app.security.output_guard import (
    validate_output,
    validate_stream_chunk,
)
from app.security.moderation import moderate_text
from app.security.pii_detector import detect_pii

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1",
    tags=["Chat"],
)


memory_service = MemoryService()
context_manager = ContextManager()
token_manager = TokenManager()
usage_service = UsageService()


# ============================================================
# NORMAL CHAT ENDPOINT
# ============================================================

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
def chat(
    request: Request,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
):
    request_id = generate_request_id()
    normalized_message = normalize_input(
        chat_request.message
    )

    validation_result = validate_message(
        normalized_message,
        max_length=4000,
    )

    if not validation_result.is_valid:
        logger.warning(
            "request_id=%s | Input validation failed | reason=%s",
            request_id,
            validation_result.reason,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid message. Please check your input "
                "and try again."
            ),
        )
    injection_result = detect_prompt_injection(
        normalized_message
    )

    if injection_result.is_injection:
        logger.warning(
            "request_id=%s | Prompt injection detected | "
            "reason=%s",
            request_id,
            injection_result.reason,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Your message appears to contain a prompt "
                "injection attempt. Please rephrase your request."
            ),
        )

    # 3. Moderation check
    moderation_result = moderate_text(
        normalized_message
    )

    if not moderation_result.is_safe:
        logger.warning(
            "request_id=%s | Moderation blocked input | reason=%s",
            request_id,
            moderation_result.reason,
        )

        raise HTTPException(
            status_code=400,
            detail="Your message was blocked by the content safety filter.",
        )
    # 4. PII detection
    pii_result = detect_pii(
        normalized_message
    )

    if pii_result.contains_pii:
        logger.warning(
            "request_id=%s | PII detected | type=%s",
            request_id,
            pii_result.pii_type,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Your message contains personal information. "
                "Please remove sensitive information and try again."
            ),
        )

    try:
        logger.info(
            "request_id=%s | Chat request received",
            request_id,
        )

        # 1. Get or create conversation
        conversation = memory_service.get_or_create_conversation(
            db,
            chat_request.conversation_id,
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
            current_message=normalized_message,
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
            user_message=normalized_message,
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

        # 6. Generate normal AI response
        ai_service = get_ai_service()
        start_time = time.perf_counter()
        result = ai_service.generate_response(
            normalized_message,
            request_id,
            history,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # 6.1 Validate AI output
        output_result = validate_output(
            result["response"]
        )

        if not output_result.is_safe:
            logger.warning(
                "request_id=%s | Output guard blocked response | reason=%s",
                request_id,
                output_result.reason,
            )
            raise HTTPException(
                status_code=500,
                detail="The AI generated an unsafe response.",
            )

        # 6.2 Moderate AI output
        moderation_result = moderate_text(
            result["response"]
        )

        if not moderation_result.is_safe:
            logger.warning(
                "request_id=%s | Moderation blocked AI output | reason=%s",
                request_id,
                moderation_result.reason,
            )
            raise HTTPException(
                status_code=500,
                detail="The AI generated an unsafe response.",
            )

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
            model=get_active_model_name(),
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
            normalized_message,
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
@limiter.limit("10/minute")
def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
):
    request_id = generate_request_id()
    normalized_message = normalize_input(
        chat_request.message
    )

    validation_result = validate_message(
        normalized_message,
        max_length=4000,
    )

    if not validation_result.is_valid:
        logger.warning(
            "request_id=%s | Input validation failed | reason=%s",
            request_id,
            validation_result.reason,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid message. Please check your input "
                "and try again."
            ),
        )
    injection_result = detect_prompt_injection(
        normalized_message
    )

    if injection_result.is_injection:
        logger.warning(
            "request_id=%s | Prompt injection detected | "
            "reason=%s",
            request_id,
            injection_result.reason,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Your message appears to contain a prompt "
                "injection attempt. Please rephrase your request."
            ),
        )

    # 3. Moderation check
    moderation_result = moderate_text(
        normalized_message
    )

    if not moderation_result.is_safe:
        logger.warning(
            "request_id=%s | Moderation blocked input | reason=%s",
            request_id,
            moderation_result.reason,
        )

        raise HTTPException(
            status_code=400,
            detail="Your message was blocked by the content safety filter.",
        )

    # 4. PII detection
    pii_result = detect_pii(
        normalized_message
    )

    if pii_result.contains_pii:
        logger.warning(
            "request_id=%s | PII detected | type=%s",
            request_id,
            pii_result.pii_type,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Your message contains personal information. "
                "Please remove sensitive information and try again."
            ),
        )

    try:
        logger.info(
            "request_id=%s | Streaming chat request received",
            request_id,
        )

        # 1. Get or create conversation
        conversation = memory_service.get_or_create_conversation(
            db,
            chat_request.conversation_id,
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
            current_message=normalized_message,
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
            user_message=normalized_message,
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

        # 6. Start AI streaming
        ai_service = get_ai_service()
        stream_usage = {}

        start_time = time.perf_counter()
        stream = ai_service.generate_stream(
            normalized_message,
            request_id,
            history,
            usage_container=stream_usage,
        )

        def stream_generator():
            full_response = ""
            stream_successful = False
            stream_buffer = ""

            try:
                for chunk in stream:

                    # Validate streaming output before sending it
                    is_safe, reason, stream_buffer = validate_stream_chunk(
                        chunk,
                        buffer=stream_buffer,
                    )

                    if not is_safe:
                        logger.warning(
                            "request_id=%s | Streaming output blocked | reason=%s",
                            request_id,
                            reason,
                        )

                        yield "\n\n[Error: AI response blocked by security guard.]"
                        break

                    full_response += chunk
                    # Moderate accumulated AI output
                    moderation_result = moderate_text(
                        full_response
                    )

                    if not moderation_result.is_safe:
                        logger.warning(
                            "request_id=%s | Moderation blocked streaming AI output | reason=%s",
                            request_id,
                            moderation_result.reason,
                        )

                        yield "\n\n[Error: AI response blocked by content safety filter.]"
                        break

                    yield chunk

                else:
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
                conversation_id=chat_request.conversation_id,
                model=get_active_model_name(),
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
                    normalized_message,
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