from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    OPENAI_EMBEDDING_MODEL: str

    # Z-API
    ZAPI_INSTANCE_ID: str
    ZAPI_TOKEN: str
    ZAPI_CLIENT_TOKEN: str

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
