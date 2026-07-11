"""
Configuration management for the FitNova Sales-Call Intelligence application.

Why this approach:
We use pydantic_settings to define a strongly-typed Settings class. This automatically
loads and validates configuration parameters from environment variables or a local .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings class.
    
    Reads from environment variables and supports .env file loading.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Database configuration
    DATABASE_URL: str = "postgresql://postgres:postgres_secure_pass@db:5432/fitnova_db"
    
    # LLM Provider API Keys
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    
    # Application environments
    APP_ENV: str = "development"
    MOCK_CALLS_DIR: str = "data/mock_calls"
    WHISPER_MODEL_NAME: str = "tiny"
    
    # CORS Configuration
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    
    # JWT authentication settings
    JWT_SECRET_KEY: str = "placeholder_secret_key_change_me_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

# Create a singleton settings object
settings = Settings()
