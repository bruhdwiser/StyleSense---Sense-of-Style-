"""StyleSense AI — Application Configuration."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "StyleSense AI"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/stylesense.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_ALWAYS_EAGER: bool = True

    JWT_SECRET: str = "stylesense-secret-key-change-in-prod"
    JWT_REFRESH_SECRET: str = "stylesense-refresh-secret-key-change-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATA_PROCESSED_DIR: str = str(ROOT_DIR / "data" / "processed")
    STATIC_SEEDINGS_DIR: str = str(ROOT_DIR / "Static_Seedings")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
