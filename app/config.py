from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DoaçãoBot"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://doacao_user:doacao_pass@db:5432/doacao_db"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Z-API
    ZAPI_INSTANCE_ID: str = ""
    ZAPI_TOKEN: str = ""
    ZAPI_CLIENT_TOKEN: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
