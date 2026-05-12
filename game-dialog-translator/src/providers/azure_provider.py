from __future__ import annotations
from dataclasses import dataclass
import requests
from .base import TranslationItem, TranslationResult, ProviderNotConfiguredError, ProviderRateLimitError, ProviderTemporaryError, ProviderPermanentError, ProviderInvalidResponseError, ProviderQuotaExceededError

@dataclass
class AzureProvider:
    key: str
    endpoint: str
    region: str = ""
    source_lang: str = "en"
    target_lang: str = "pt-br"
    timeout: int = 30
    provider_name: str = "azure"

    def is_configured(self) -> bool:
        return bool(self.key and self.endpoint)

    def translate_batch(self, items: list[TranslationItem]) -> list[TranslationResult]:
        if not self.is_configured():
            raise ProviderNotConfiguredError("Azure Translator não configurado")
        url = f"{self.endpoint.rstrip('/')}/translate"
        params = {"api-version": "3.0", "from": self.source_lang, "to": self.target_lang}
        headers = {"Ocp-Apim-Subscription-Key": self.key, "Content-Type": "application/json"}
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region
        body = [{"text": i.text} for i in items]
        resp = requests.post(url, params=params, headers=headers, json=body, timeout=self.timeout)
        if resp.status_code in (401, 403):
            raise ProviderNotConfiguredError(resp.text)
        if resp.status_code == 429:
            retry_after = getattr(resp, "headers", {}).get("Retry-After")
            retry_after_value = None
            if retry_after:
                try:
                    retry_after_value = float(retry_after)
                except ValueError:
                    retry_after_value = None
            if "quota" in resp.text.lower():
                raise ProviderQuotaExceededError(resp.text)
            raise ProviderRateLimitError(resp.text, retry_after=retry_after_value)
        if 500 <= resp.status_code <= 599:
            raise ProviderTemporaryError(resp.text)
        if resp.status_code >= 400:
            raise ProviderPermanentError(resp.text)
        data = resp.json()
        if not isinstance(data, list) or len(data) != len(items):
            raise ProviderInvalidResponseError("Quantidade de respostas diferente da enviada")
        out = []
        for src, row in zip(items, data):
            trans = ((row.get("translations") or [{}])[0]).get("text", "")
            out.append(TranslationResult(line_number=src.line_number, translation=trans, provider=self.provider_name, characters_sent=len(src.text)))
        return out
