from sqlalchemy.orm import Session

from app.database.models import AIUsage


class UsageRepository:

    def save_usage(
        self,
        db: Session,
        usage_record: dict,
    ):
        ai_usage = AIUsage(
            request_id=usage_record["request_id"],
            conversation_id=usage_record["conversation_id"],
            model=usage_record["model"],
            request_type=usage_record["request_type"],
            estimated_input_tokens=usage_record["estimated_input_tokens"],
            estimated_output_tokens=usage_record["estimated_output_tokens"],
            estimated_total_tokens=usage_record["estimated_total_tokens"],
            provider_input_tokens=usage_record["provider_input_tokens"],
            provider_output_tokens=usage_record["provider_output_tokens"],
            provider_total_tokens=usage_record["provider_total_tokens"],
            status=usage_record["status"],
            latency_ms=usage_record["latency_ms"],
            created_at=usage_record["created_at"],
        )

        db.add(ai_usage)
        db.commit()
        db.refresh(ai_usage)

        return ai_usage

    def get_total_requests(self, db: Session) -> int:
        from sqlalchemy import func
        return db.query(func.count(AIUsage.id)).scalar() or 0

    def get_successful_requests(self, db: Session) -> int:
        from sqlalchemy import func
        return (
            db.query(func.count(AIUsage.id))
            .filter(AIUsage.status == "success")
            .scalar() or 0
        )

    def get_failed_requests(self, db: Session) -> int:
        from sqlalchemy import func
        return (
            db.query(func.count(AIUsage.id))
            .filter(AIUsage.status == "failure")
            .scalar() or 0
        )

    def get_total_tokens(self, db: Session) -> dict:
        from sqlalchemy import func
        result = db.query(
            func.sum(AIUsage.estimated_input_tokens).label("est_in"),
            func.sum(AIUsage.estimated_output_tokens).label("est_out"),
            func.sum(AIUsage.estimated_total_tokens).label("est_tot"),
            func.sum(AIUsage.provider_input_tokens).label("prov_in"),
            func.sum(AIUsage.provider_output_tokens).label("prov_out"),
            func.sum(AIUsage.provider_total_tokens).label("prov_tot"),
        ).first()

        return {
            "estimated_input": int(result.est_in or 0),
            "estimated_output": int(result.est_out or 0),
            "estimated_total": int(result.est_tot or 0),
            "provider_input": int(result.prov_in or 0),
            "provider_output": int(result.prov_out or 0),
            "provider_total": int(result.prov_tot or 0),
        }

    def get_usage_by_model(self, db: Session) -> list:
        from sqlalchemy import func
        results = (
            db.query(
                AIUsage.model,
                func.count(AIUsage.id).label("requests"),
            )
            .group_by(AIUsage.model)
            .all()
        )
        return [{"model": r.model, "requests": r.requests} for r in results]

    def get_usage_by_conversation(self, db: Session, limit: int = 10) -> list:
        from sqlalchemy import func
        results = (
            db.query(
                AIUsage.conversation_id,
                func.count(AIUsage.id).label("requests"),
                func.sum(AIUsage.estimated_total_tokens).label("tokens"),
            )
            .group_by(AIUsage.conversation_id)
            .order_by(func.count(AIUsage.id).desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "conversation_id": r.conversation_id,
                "requests": r.requests,
                "tokens": int(r.tokens or 0),
            }
            for r in results
        ]

    def get_usage_by_request_type(self, db: Session) -> list:
        from sqlalchemy import func
        results = (
            db.query(
                AIUsage.request_type,
                func.count(AIUsage.id).label("requests"),
            )
            .group_by(AIUsage.request_type)
            .all()
        )
        return [
            {"request_type": r.request_type, "requests": r.requests}
            for r in results
        ]
