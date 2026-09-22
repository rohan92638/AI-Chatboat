from app.services.context_service import estimate_tokens


class TokenManager:

    def estimate_text_tokens(
        self,
        text: str,
    ) -> int:
        """
        Estimate tokens for a text.
        """

        return estimate_tokens(text)

    def estimate_messages_tokens(
        self,
        messages: list,
    ) -> int:
        """
        Estimate total tokens used by messages.
        """

        total_tokens = 0

        for message in messages:
            if hasattr(message, "content"):
                content = message.content
            else:
                content = message["content"]

            total_tokens += estimate_tokens(content)

        return total_tokens

    def calculate_remaining_tokens(
        self,
        max_tokens: int,
        used_tokens: int,
    ) -> int:
        """
        Calculate remaining token budget.
        """

        return max(
            0,
            max_tokens - used_tokens,
        )

    def build_usage(
        self,
        history_tokens: int,
        user_message: str,
        system_prompt: str,
        max_context_tokens: int,
    ):
        """
        Build token usage metadata.
        """

        system_prompt_tokens = (
            self.estimate_text_tokens(system_prompt)
        )

        user_tokens = self.estimate_text_tokens(
            user_message
        )

        total_tokens = (
            system_prompt_tokens
            + history_tokens
            + user_tokens
        )

        remaining_tokens = (
            self.calculate_remaining_tokens(
                max_context_tokens,
                total_tokens,
            )
        )

        return {
            "system_prompt_tokens": system_prompt_tokens,
            "history_tokens": history_tokens,
            "user_tokens": user_tokens,
            "total_tokens": total_tokens,
            "remaining_tokens": remaining_tokens,
            "max_tokens": max_context_tokens,
        }

    def validate_budget(
        self,
        token_usage: dict,
    ) -> dict:
        """
        Check if total estimated tokens exceed the budget.
        Returns {"valid": True/False, "reason": "..."}
        """

        is_valid = (
            token_usage["total_tokens"] <= token_usage["max_tokens"]
        )

        reason = None
        if not is_valid:
            reason = "The message is too large for the configured context budget."

        return {
            "valid": is_valid,
            "reason": reason,
        }

    def build_final_usage(
        self,
        token_usage: dict,
        usage_metadata=None,
        estimated_output_tokens: int = None,
    ) -> dict:
        """
        Create a final token usage structure separating estimates
        and provider-reported values.
        """

        estimated_input = token_usage["total_tokens"]

        estimated_total = estimated_input
        if estimated_input is not None and estimated_output_tokens is not None:
            estimated_total = estimated_input + estimated_output_tokens

        provider_input = None
        provider_output = None
        provider_total = None

        if usage_metadata:
            provider_input = getattr(
                usage_metadata, "prompt_token_count", None
            )
            provider_output = getattr(
                usage_metadata, "candidates_token_count", None
            )
            provider_total = getattr(
                usage_metadata, "total_token_count", None
            )

        return {
            "estimated_input_tokens": estimated_input,
            "estimated_output_tokens": estimated_output_tokens,
            "estimated_total_tokens": estimated_total,
            "provider_input_tokens": provider_input,
            "provider_output_tokens": provider_output,
            "provider_total_tokens": provider_total,
        }