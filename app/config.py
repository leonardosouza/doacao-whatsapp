from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DoaçãoBot"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://doacao_user:doacao_pass@db:5432/doacao_db"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Z-API
    ZAPI_INSTANCE_ID: str = ""
    ZAPI_TOKEN: str = ""
    ZAPI_CLIENT_TOKEN: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
