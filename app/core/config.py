from functools import lru_cache
from typing import List, Optional

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "InvestiFlow API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: Optional[str] = None  # Set via environment variable or .env file
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "investi_flow_db"
    DATABASE_USER: str = "investi_flow_user"
    DATABASE_PASSWORD: str = ""

    # JWT Security
    SECRET_KEY: Optional[SecretStr] = None  # Set via environment variable or .env file
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutos para mayor seguridad
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1  # 24 horas

    # CORS
    BACKEND_CORS_ORIGIN: str = "http://localhost:5173"

    # File Upload
    MAX_FILE_SIZE: int = 10485760  # 10MB
    UPLOAD_FOLDER: str = "uploads"
    ALLOWED_EXTENSIONS: str = "pdf,doc,docx,txt,md"

    # AI Services
    OPENAI_API_KEY: Optional[SecretStr] = None
    GOOGLE_AI_API_KEY: Optional[SecretStr] = None

    # AI Models
    AI_MODEL_CHAT: str = "gemini-2.5-flash-lite"
    AI_MODEL_SUGGESTIONS: str = "gemini-2.5-flash-lite"
    AI_MODEL_CITATIONS: str = "gemini-2.5-flash-lite"
    AI_MODEL_BIBLIOGRAPHY: str = "gemini-3.1-pro-preview"

    # Redis
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[SecretStr] = None

    def get_backend_cors_origins(self) -> List[str]:
        origin_value = self.BACKEND_CORS_ORIGIN.strip()
        if not origin_value:
            return []
        return [origin.strip() for origin in origin_value.split(",") if origin.strip()]

    def get_allowed_extensions(self) -> List[str]:
        return [
            ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()
        ]

    def require_database_url(self) -> str:
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is not set in the configuration.")
        return self.DATABASE_URL

    def require_secret_key(self) -> str:
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY is not set in the configuration.")
        return self.SECRET_KEY.get_secret_value()

    def require_google_ai_api_key(self) -> str:
        if not self.GOOGLE_AI_API_KEY:
            raise ValueError("GOOGLE_AI_API_KEY is not set in the configuration.")
        return self.GOOGLE_AI_API_KEY.get_secret_value()

    def get_google_ai_api_key(self) -> Optional[str]:
        if not self.GOOGLE_AI_API_KEY:
            return None
        return self.GOOGLE_AI_API_KEY.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
