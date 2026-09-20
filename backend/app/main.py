import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes.usage import router as usage_router
from app.core.logging import setup_logging


setup_logging()

logger = logging.getLogger(__name__)


app = FastAPI(
    title="AI Chatbot API",
    description="Production-style AI chatbot backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    logger.info("Health check requested")

    return {
        "status": "ok",
        "message": "AI Chatbot API is running",
    }


app.include_router(chat_router)
app.include_router(usage_router)