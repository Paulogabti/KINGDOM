from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"

@dataclass
class Settings:
    deepl_api_key: str = ""
    deepl_api_url: str = DEEPL_FREE_URL
    deepl_source_lang: str = "EN"
    deepl_target_lang: str = "PT-BR"
    default_batch_size: int = 20
    default_formality: str = "prefer_more"
    logs_dir: Path = Path("logs")
    progress_dir: Path = Path(".progress")

    def __post_init__(self):
        self.deepl_api_key = os.getenv("DEEPL_API_KEY", self.deepl_api_key)
        self.deepl_api_url = os.getenv("DEEPL_API_URL", self.deepl_api_url)
        self.deepl_source_lang = os.getenv("DEEPL_SOURCE_LANG", self.deepl_source_lang)
        self.deepl_target_lang = os.getenv("DEEPL_TARGET_LANG", self.deepl_target_lang)
        self.default_batch_size = int(os.getenv("DEFAULT_BATCH_SIZE", str(self.default_batch_size)))
        self.default_formality = os.getenv("DEFAULT_FORMALITY", self.default_formality)
        self.logs_dir = Path(os.getenv("LOGS_DIR", str(self.logs_dir)))
        self.progress_dir = Path(os.getenv("PROGRESS_DIR", str(self.progress_dir)))

def ensure_dirs(settings: Settings) -> None:
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.progress_dir.mkdir(parents=True, exist_ok=True)
