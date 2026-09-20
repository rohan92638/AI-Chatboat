from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.usage_service import UsageService


router = APIRouter(
    prefix="/api/v1/usage",
    tags=["Usage"],
)

usage_service = UsageService()

@router.get("/statistics")
def get_usage_statistics(
    db: Session = Depends(get_db),
    usage_service: UsageService = Depends(UsageService),
):
    """
    Get aggregated usage statistics for the AI Chatbot.
    """
    return usage_service.get_statistics(db)
