import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    azure_document_intelligence_endpoint: Optional[str] = Field(
        default=None, alias="AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
    )
    azure_document_intelligence_key: Optional[str] = Field(
        default=None, alias="AZURE_DOCUMENT_INTELLIGENCE_KEY"
    )
    azure_openai_endpoint: Optional[str] = Field(
        default=None, alias="AZURE_OPENAI_ENDPOINT"
    )
    azure_openai_api_key: Optional[str] = Field(
        default=None, alias="AZURE_OPENAI_API_KEY"
    )
    azure_openai_deployment: Optional[str] = Field(
        default=None, alias="AZURE_OPENAI_DEPLOYMENT"
    )
    storage_path: Path = Path(os.environ.get("INVOICE_STORAGE_PATH", "data/invoices"))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    return settings
