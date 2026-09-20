def estimate_tokens(text: str) -> int:
    """
    Simple token estimation.
    Approximately 1 token per 4 characters.
    """
    return max(1, len(text) // 4)


def select_context_messages(
    messages: list,
    current_message: str,
    max_tokens: int = 4000,
):
    selected_messages = []

    # Reserve tokens for the current user message
    current_message_tokens = estimate_tokens(
        current_message
    )

    remaining_tokens = (
        max_tokens - current_message_tokens
    )

    if remaining_tokens < 0:
        remaining_tokens = 0

    total_tokens = 0

    # Start from newest history message
    for message in reversed(messages):
        message_tokens = estimate_tokens(
            message.content
        )

        if total_tokens + message_tokens > remaining_tokens:
            break

        selected_messages.append(message)
        total_tokens += message_tokens

    # Restore chronological order
    selected_messages.reverse()

    return selected_messages


def get_context_token_count(messages: list) -> int:
    total_tokens = 0

    for message in messages:
        total_tokens += estimate_tokens(
            message.content
        )

    return total_tokens