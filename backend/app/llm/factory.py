from app.config import get_settings
from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiLLMProvider


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        return GeminiLLMProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_chat_model,
            temperature=settings.llm_temperature,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
