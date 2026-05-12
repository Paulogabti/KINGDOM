from __future__ import annotations
import logging
from dataclasses import dataclass
from .providers import TranslationItem, TranslationResult, ProviderTestResult
from .providers import ProviderQuotaExceededError, ProviderRateLimitError, ProviderTemporaryError
from .providers import deepl_provider
from .providers.deepl_provider import DeepLProvider
deepl = deepl_provider.deepl
from .providers.azure_provider import AzureProvider

@dataclass
class DeepLTranslationSettings:
    api_key: str
    api_url: str
    source_lang: str = "EN"
    target_lang: str = "PT-BR"
    formality: str = "prefer_more"

def translate_batch_with_deepl(items: list[dict], settings: DeepLTranslationSettings, retries: int = 3) -> list[dict]:
    deepl_provider.deepl = deepl
    provider = DeepLProvider(settings.api_key, settings.api_url, settings.source_lang, settings.target_lang, settings.formality)
    try:
        out = provider.translate_batch([TranslationItem(line_number=i["line_number"], text=i["text"]) for i in items], retries=retries)
        return [{"line_number": r.line_number, "translation": r.translation} for r in out]
    except ProviderQuotaExceededError:
        return [{"line_number": i["line_number"], "translation": ""} for i in items]

def test_deepl_connection(settings: DeepLTranslationSettings) -> tuple[bool, str]:
    try:
        rs = translate_batch_with_deepl([{"line_number": 1, "text": "Hello"}], settings, retries=1)
        return (bool(rs and rs[0]["translation"]), "Conexão DeepL OK")
    except Exception as e:
        return False, f"Falha ao testar conexão DeepL: {e}"

def test_azure_connection(provider: AzureProvider) -> ProviderTestResult:
    try:
        out = provider.translate_batch([TranslationItem(line_number=1, text="Hello")])
        return ProviderTestResult(provider="azure", ok=bool(out and out[0].translation), message="Conexão Azure OK")
    except Exception as e:
        return ProviderTestResult(provider="azure", ok=False, message=f"Falha Azure: {e}")

def translate_with_fallback(items: list[TranslationItem], deepl: DeepLProvider | None, azure: AzureProvider | None, enable_fallback: bool = True) -> tuple[list[TranslationResult], dict]:
    attempted = []
    if deepl:
        attempted.append("deepl")
        try:
            r = deepl.translate_batch(items)
            return r, {"provider":"deepl","fallback_used":False,"provider_chain_attempted":attempted}
        except (ProviderQuotaExceededError, ProviderRateLimitError, ProviderTemporaryError) as e:
            logging.warning("Falha DeepL (%s), tentando fallback", e)
            if not enable_fallback:
                raise
    if azure and enable_fallback:
        attempted.append("azure")
        r = azure.translate_batch(items)
        return r, {"provider":"azure","fallback_used":True,"provider_chain_attempted":attempted}
    raise RuntimeError("Nenhum provider disponível")
