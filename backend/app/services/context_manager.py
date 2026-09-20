from app.services.context_service import (
    select_context_messages,
    get_context_token_count,
    estimate_tokens,
)


class ContextManager:

    def build_context(
        self,
        messages: list,
        current_message: str,
        max_tokens: int,
    ):
        # Select history messages that fit
        # within the configured context budget.
        selected_messages = select_context_messages(
            messages,
            current_message=current_message,
            max_tokens=max_tokens,
        )

        # Estimate tokens used by selected history.
        history_tokens = get_context_token_count(
            selected_messages
        )

        # Estimate tokens used by current user message.
        current_message_tokens = estimate_tokens(
            current_message
        )

        # Total estimated tokens.
        total_context_tokens = (
            history_tokens
            + current_message_tokens
        )

        # Convert database messages into
        # Gemini-compatible history format.
        history = []

        for message in selected_messages:
            history.append(
                {
                    "role": message.role,
                    "content": message.content,
                }
            )

        return {
            "history": history,
            "history_message_count": len(history),
            "history_tokens": history_tokens,
            "current_message_tokens": current_message_tokens,
            "total_context_tokens": total_context_tokens,
            "max_context_tokens": max_tokens,
        }