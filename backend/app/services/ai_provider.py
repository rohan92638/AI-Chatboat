from app.core.config import settings
from app.services.gemini_service import GeminiService
from app.services.ollama_service import OllamaService

# Instantiate services once (singletons)
_gemini_service = GeminiService()
_ollama_service = OllamaService()

def get_ai_service():
    """
    Returns the configured AI service provider based on settings.AI_PROVIDER.
    """
    if settings.AI_PROVIDER.lower() == "ollama":
        return _ollama_service
    
    # Default to Gemini
    return _gemini_service

def get_active_model_name():
    """
    Returns the model name of the active provider.
    """
    if settings.AI_PROVIDER.lower() == "ollama":
        return settings.OLLAMA_MODEL
    
    return settings.GEMINI_MODEL
