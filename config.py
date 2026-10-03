import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    """Centralized Configuration Manager for Screener AI Stock Analyzer."""
    
    # API Keys
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

    # Model Selectors (Using non-obsolete active models)
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it:free").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

    # Network & Request Timeouts (seconds)
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "20"))
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "45"))

    # User Agent for HTTP Web Requests
    USER_AGENT = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # News Settings
    DEFAULT_NEWS_LIMIT = int(os.getenv("DEFAULT_NEWS_LIMIT", "8"))
    DEFAULT_NEWS_FRESHNESS_DAYS = int(os.getenv("DEFAULT_NEWS_FRESHNESS_DAYS", "30"))

    # Cache TTL (seconds)
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

    @classmethod
    def get_openrouter_key(cls, override_key=None):
        key = (override_key or cls.OPENROUTER_API_KEY or "").strip()
        return key

    @classmethod
    def get_gemini_key(cls, override_key=None):
        key = (override_key or cls.GEMINI_API_KEY or "").strip()
        return key

    @classmethod
    def get_groq_key(cls, override_key=None):
        key = (override_key or cls.GROQ_API_KEY or "").strip()
        return key
