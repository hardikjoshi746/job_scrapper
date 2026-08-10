from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    adzuna_app_id: str
    adzuna_app_key: str
    secret_key: str = "change-this-to-a-random-secret"

    class Config:
        env_file = ".env"


settings = Settings()