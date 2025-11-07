from typing import Optional

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
    SECRET_KEY: Optional[str] = None  # Set via environment variable or .env file
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
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_AI_API_KEY: Optional[str] = None

    # Redis
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None


settings = Settings()
