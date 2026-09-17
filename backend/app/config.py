"""
Application configuration.

Loads settings from environment variables / a .env file. Add new
settings here as the project grows (e.g. rate limit thresholds,
alternate LLM providers, auth secrets).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MLH LLM Fellowship Project"
    database_url: str = "sqlite:///./app.db"

    # LLM provider config. Fellows will extend this to support
    # multiple providers behind the abstract interface in app/llm/.
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # CORS - the Vite dev server default port. In production set this to
    # the deployed frontend URL. Comma-separate to allow more than one.
    frontend_origin: str = "http://localhost:5173"

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
