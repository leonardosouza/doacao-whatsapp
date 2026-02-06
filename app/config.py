import os

from pydantic_settings import BaseSettings

APP_ENV = os.getenv("APP_ENV", "development")
_env_file = f".env.{APP_ENV}"


class Settings(BaseSettings):
    # App
    APP_NAME: str
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    OPENAI_EMBEDDING_MODEL: str
    OPENAI_TEMPERATURE: float = 0.3

    # Z-API
    ZAPI_INSTANCE_ID: str
    ZAPI_TOKEN: str
    ZAPI_CLIENT_TOKEN: str

    model_config = {"env_file": _env_file, "extra": "ignore"}


settings = Settings()
