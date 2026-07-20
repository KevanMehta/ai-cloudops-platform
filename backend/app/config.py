from enum import Enum

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OperatingMode(str, Enum):
    demo = "demo"
    connected = "connected"
    offline = "offline"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://cloudops:cloudops_secret@localhost:5432/cloudops"
    redis_url: str = "redis://localhost:6379/0"
    operating_mode: OperatingMode = OperatingMode.demo
    openai_api_key: str = ""
    log_level: str = "INFO"
    infra_samples_path: str = "./infra-samples"
    cors_origins: str = "http://localhost:3000"
    aws_region: str = "us-east-1"
    aws_role_arn: str = ""
    aws_external_id: str = ""
    aws_session_name: str = "cloudops-platform"
    aws_cost_lookback_days: int = 90
    kubernetes_context: str = ""
    app_name: str = "AI CloudOps Platform"
    app_version: str = "1.1.0"

    @field_validator("aws_cost_lookback_days")
    @classmethod
    def validate_lookback(cls, value: int) -> int:
        if not 1 <= value <= 365:
            raise ValueError("aws_cost_lookback_days must be between 1 and 365")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
