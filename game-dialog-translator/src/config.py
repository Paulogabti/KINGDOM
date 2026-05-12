from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

DEEPL_FREE_BASE_URL = "https://api-free.deepl.com"
DEEPL_PRO_BASE_URL = "https://api.deepl.com"

@dataclass
class Settings:
    translation_provider: str = "azure"
    deepl_api_key: str = ""
    deepl_api_url: str = DEEPL_FREE_BASE_URL
    deepl_source_lang: str = "EN"
    deepl_target_lang: str = "PT-BR"
    default_batch_size: int = 20
    default_formality: str = "prefer_more"
    logs_dir: Path = Path("logs")
    progress_dir: Path = Path(".progress")
    azure_translate_enabled: bool = False
    azure_translator_key: str = ""
    azure_translator_endpoint: str = "https://api.cognitive.microsofttranslator.com"
    azure_translator_region: str = "brazilsouth"
    azure_source_lang: str = "en"
    azure_target_lang: str = "pt-br"
    enable_provider_fallback: bool = False
    fallback_providers: str = ""
    azure_max_retries: int = 8
    azure_initial_backoff_seconds: float = 3.0
    azure_max_backoff_seconds: float = 120.0
    azure_delay_between_batches_seconds: float = 0.1
    azure_dynamic_throttle: bool = True
    azure_start_lines_per_batch: int = 100
    azure_max_lines_per_batch: int = 100
    azure_min_lines_per_batch: int = 1
    azure_start_chars_per_batch: int = 8000
    azure_max_chars_per_batch: int = 12000
    azure_min_chars_per_batch: int = 500
    azure_dynamic_batching: bool = True
    azure_grow_after_successful_batches: int = 10
    azure_batch_growth_factor: float = 1.25
    azure_batch_shrink_factor: float = 0.5

    def __post_init__(self):
        self.deepl_api_key = os.getenv("DEEPL_API_KEY", self.deepl_api_key)
        self.translation_provider = os.getenv("TRANSLATION_PROVIDER", self.translation_provider).lower()
        self.deepl_api_url = os.getenv("DEEPL_API_URL", self.deepl_api_url)
        self.deepl_source_lang = os.getenv("DEEPL_SOURCE_LANG", self.deepl_source_lang)
        self.deepl_target_lang = os.getenv("DEEPL_TARGET_LANG", self.deepl_target_lang)
        self.default_batch_size = int(os.getenv("DEFAULT_BATCH_SIZE", str(self.default_batch_size)))
        self.default_formality = os.getenv("DEFAULT_FORMALITY", self.default_formality)
        self.logs_dir = Path(os.getenv("LOGS_DIR", str(self.logs_dir)))
        self.progress_dir = Path(os.getenv("PROGRESS_DIR", str(self.progress_dir)))
        self.azure_translate_enabled = os.getenv("AZURE_TRANSLATE_ENABLED", str(self.azure_translate_enabled)).lower() == "true"
        self.azure_translator_key = os.getenv("AZURE_TRANSLATOR_KEY", self.azure_translator_key)
        self.azure_translator_endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT", self.azure_translator_endpoint)
        self.azure_translator_region = os.getenv("AZURE_TRANSLATOR_REGION", self.azure_translator_region)
        self.azure_source_lang = os.getenv("AZURE_SOURCE_LANG", self.azure_source_lang)
        self.azure_target_lang = os.getenv("AZURE_TARGET_LANG", self.azure_target_lang)
        self.enable_provider_fallback = os.getenv("ENABLE_PROVIDER_FALLBACK", str(self.enable_provider_fallback)).lower() == "true"
        self.fallback_providers = os.getenv("FALLBACK_PROVIDERS", self.fallback_providers)
        self.azure_max_retries = int(os.getenv("AZURE_MAX_RETRIES", str(self.azure_max_retries)))
        self.azure_initial_backoff_seconds = float(os.getenv("AZURE_INITIAL_BACKOFF_SECONDS", str(self.azure_initial_backoff_seconds)))
        self.azure_max_backoff_seconds = float(os.getenv("AZURE_MAX_BACKOFF_SECONDS", str(self.azure_max_backoff_seconds)))
        self.azure_delay_between_batches_seconds = float(os.getenv("AZURE_DELAY_BETWEEN_BATCHES_SECONDS", str(self.azure_delay_between_batches_seconds)))
        self.azure_dynamic_throttle = os.getenv("AZURE_DYNAMIC_THROTTLE", str(self.azure_dynamic_throttle)).lower() == "true"
        self.azure_start_lines_per_batch = int(os.getenv("AZURE_START_LINES_PER_BATCH", str(self.azure_start_lines_per_batch)))
        self.azure_max_lines_per_batch = int(os.getenv("AZURE_MAX_LINES_PER_BATCH", str(self.azure_max_lines_per_batch)))
        self.azure_min_lines_per_batch = int(os.getenv("AZURE_MIN_LINES_PER_BATCH", str(self.azure_min_lines_per_batch)))
        self.azure_start_chars_per_batch = int(os.getenv("AZURE_START_CHARS_PER_BATCH", str(self.azure_start_chars_per_batch)))
        self.azure_max_chars_per_batch = int(os.getenv("AZURE_MAX_CHARS_PER_BATCH", str(self.azure_max_chars_per_batch)))
        self.azure_min_chars_per_batch = int(os.getenv("AZURE_MIN_CHARS_PER_BATCH", str(self.azure_min_chars_per_batch)))
        self.azure_dynamic_batching = os.getenv("AZURE_DYNAMIC_BATCHING", str(self.azure_dynamic_batching)).lower() == "true"
        self.azure_grow_after_successful_batches = int(os.getenv("AZURE_GROW_AFTER_SUCCESSFUL_BATCHES", str(self.azure_grow_after_successful_batches)))
        self.azure_batch_growth_factor = float(os.getenv("AZURE_BATCH_GROWTH_FACTOR", str(self.azure_batch_growth_factor)))
        self.azure_batch_shrink_factor = float(os.getenv("AZURE_BATCH_SHRINK_FACTOR", str(self.azure_batch_shrink_factor)))

def ensure_dirs(settings: Settings) -> None:
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.progress_dir.mkdir(parents=True, exist_ok=True)
