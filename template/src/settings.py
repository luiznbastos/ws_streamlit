from pydantic import Field
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
# Set up logging
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Pydantic config
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # General
    environment: str = Field(default="development", description="App environment", alias="ENVIRONMENT")

    # AWS
    region: str = Field(default="us-east-1", alias="REGION")
    streamlit_role_arn: Optional[str] = Field(default=None, alias="STREAMLIT_ROLE_ARN")
    documents_bucket: str = Field(default="streamlit-fastapi-documents-32142665", alias="DOCUMENTS_BUCKET")

    # RAG backend
    rag_api_base_url: str = Field(default="http://fastapi:8000", alias="RAG_API_BASE_URL")

    # Database credentials
    rds_host: Optional[str] = Field(default=None, alias="RDS_HOST")
    rds_db: Optional[str] = Field(default=None, alias="RDS_DB")
    rds_user: Optional[str] = Field(default=None, alias="RDS_USER")
    rds_password: Optional[str] = Field(default=None, alias="RDS_PASSWORD")
    
    # OpenAI API key for title generation
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    @property
    def storage_suffix(self) -> str:
        if self.environment in ["staging", "development"]:
            return "_dev"
        elif self.environment == "production":
            return ""
        else:
            raise ValueError("Invalid environment. Choose 'staging', 'development', or 'production'.")

logger.info("Loading settings from environment variables...")
# Load settings
settings = Settings()
logger.info("Settings loaded successfully.")
logger.info(f"Settings: {settings}")