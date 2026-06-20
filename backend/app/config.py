from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://cloudops:cloudops_secret@localhost:5432/cloudops"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    log_level: str = "INFO"
    infra_samples_path: str = "./infra-samples"
    app_name: str = "AI CloudOps Platform"
    app_version: str = "1.0.0"


settings = Settings()
