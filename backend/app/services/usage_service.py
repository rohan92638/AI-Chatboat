from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.usage_repository import UsageRepository


class UsageService:

    def __init__(self):
        self.repository = UsageRepository()

    def build_usage_record(
        self,
        request_id: str,
        conversation_id: str,
        model: str,
        request_type: str,
        final_usage: dict,
        status: str,
        latency_ms: int,
    ) -> dict:
        """
        Build a complete AI usage record dictionary.
        """

        # Ensure final_usage is a dict even if None is passed
        if final_usage is None:
            final_usage = {}

        return {
            "request_id": request_id,
            "conversation_id": conversation_id,
            "model": model,
            "request_type": request_type,
            
            "estimated_input_tokens": final_usage.get("estimated_input_tokens"),
            "estimated_output_tokens": final_usage.get("estimated_output_tokens"),
            "estimated_total_tokens": final_usage.get("estimated_total_tokens"),
            
            "provider_input_tokens": final_usage.get("provider_input_tokens"),
            "provider_output_tokens": final_usage.get("provider_output_tokens"),
            "provider_total_tokens": final_usage.get("provider_total_tokens"),
            
            "status": status,
            "latency_ms": latency_ms,
            "created_at": datetime.utcnow(),
        }

    def save_usage(
        self,
        db: Session,
        usage_record: dict,
    ):
        """
        Save an AI usage record to the database.
        """
        return self.repository.save_usage(
            db,
            usage_record,
        )

    def get_statistics(self, db: Session) -> dict:
        """
        Get aggregated usage statistics.
        """
        return {
            "total_requests": self.repository.get_total_requests(db),
            "successful_requests": self.repository.get_successful_requests(db),
            "failed_requests": self.repository.get_failed_requests(db),
            "total_tokens": self.repository.get_total_tokens(db),
            "usage_by_model": self.repository.get_usage_by_model(db),
            "usage_by_conversation": self.repository.get_usage_by_conversation(db),
            "usage_by_request_type": self.repository.get_usage_by_request_type(db),
        }
