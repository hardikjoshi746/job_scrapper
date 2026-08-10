from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str = ""
    adzuna_app_id: str
    adzuna_app_key: str
    secret_key: str = "change-this-to-a-random-secret"

    # S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
