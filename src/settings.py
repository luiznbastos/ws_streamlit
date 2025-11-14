from pydantic import Field
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)

env_file_path = Path(__file__).parent.parent / ".env"
if not env_file_path.exists():
    env_file_path = Path(".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(env_file_path),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    environment: str = Field(default="development", description="App environment", alias="ENVIRONMENT")

    region: str = Field(default="us-east-1", alias="REGION")
    
    redshift_host: Optional[str] = Field(default=None, alias="REDSHIFT_HOST")
    redshift_port: int = Field(default=5439, alias="REDSHIFT_PORT")
    redshift_database: Optional[str] = Field(default=None, alias="REDSHIFT_DATABASE")
    redshift_user: Optional[str] = Field(default=None, alias="REDSHIFT_USER")
    redshift_password: Optional[str] = Field(default=None, alias="REDSHIFT_PASSWORD")
    redshift_cluster_id: Optional[str] = Field(default=None, alias="REDSHIFT_CLUSTER_ID")
    
    use_iam_auth: bool = Field(default=True, alias="USE_IAM_AUTH")

    @property
    def storage_suffix(self) -> str:
        if self.environment in ["staging", "development"]:
            return "_dev"
        elif self.environment == "production":
            return ""
        else:
            raise ValueError("Invalid environment. Choose 'staging', 'development', or 'production'.")

logger.info("Loading settings from environment variables...")
settings = Settings()
logger.info("Settings loaded successfully.")
logger.info(f"Environment: {settings.environment}")

