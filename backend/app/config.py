"""
Application configuration.

Loads settings from environment variables / a .env file. Add new
settings here as the project grows (e.g. rate limit thresholds,
alternate LLM providers, auth secrets).
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "MLH LLM Fellowship Project"
    database_url: str = f"sqlite:///{(BASE_DIR / 'app.db').as_posix()}"
    log_level: str = "INFO"
    # Signs auth tokens. Left empty, a random key is used per process,
    # so tokens stop working on restart. Set a real one in .env.
    jwt_secret_key: str = ""

    # LLM provider config. Fellows will extend this to support
    # multiple providers behind the abstract interface in app/llm/.
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    # Global system prompt sent with every LLM request.
    system_prompt: str = "You are a helpful assistant."

    # CORS - the Vite dev server default port
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")


settings = Settings()
