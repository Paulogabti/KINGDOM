from __future__ import annotations
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"

class Settings(BaseSettings):
    deepl_api_key: str = Field(default="", alias="DEEPL_API_KEY")
    deepl_api_url: str = Field(default=DEEPL_FREE_URL, alias="DEEPL_API_URL")
    deepl_source_lang: str = Field(default="EN", alias="DEEPL_SOURCE_LANG")
    deepl_target_lang: str = Field(default="PT-BR", alias="DEEPL_TARGET_LANG")
    default_batch_size: int = Field(default=20, alias="DEFAULT_BATCH_SIZE")
    default_formality: str = Field(default="prefer_more", alias="DEFAULT_FORMALITY")
    logs_dir: Path = Path("logs")
    progress_dir: Path = Path(".progress")
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

def ensure_dirs(settings: Settings) -> None:
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.progress_dir.mkdir(parents=True, exist_ok=True)
