from typing import List, Optional, Union

from pydantic import field_validator
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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return [v.strip()]
        elif isinstance(v, list):
            return v
        raise ValueError(f"Invalid type for CORS origins: {type(v)}")

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
