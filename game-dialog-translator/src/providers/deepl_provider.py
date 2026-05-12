from __future__ import annotations
import re
import time
from dataclasses import dataclass
from .base import TranslationItem, TranslationResult, ProviderQuotaExceededError, ProviderTemporaryError, ProviderInvalidResponseError, ProviderNotConfiguredError

try:
    import deepl
except ModuleNotFoundError:
    deepl = None

PH_VAR = re.compile(r"_+\s*PH_(\d{4})\s*_+|\bPH_(\d{4})\b")

def normalize_placeholder_variants(text: str, valid_tokens: set[str]) -> str:
    def repl(m):
        num = m.group(1) or m.group(2)
        cand = f"__PH_{num}__"
        return cand if cand in valid_tokens else m.group(0)
    return PH_VAR.sub(repl, text)

@dataclass
class DeepLProvider:
    api_key: str
    api_url: str
    source_lang: str = "EN"
    target_lang: str = "PT-BR"
    formality: str = "prefer_more"
    timeout: int = 30
    provider_name: str = "deepl"

    def translate_batch(self, items: list[TranslationItem], retries: int = 3) -> list[TranslationResult]:
        if not self.api_key:
            raise ProviderNotConfiguredError("DEEPL_API_KEY ausente")
        if deepl is None:
            raise ProviderNotConfiguredError("Dependência deepl ausente")
        translator = deepl.Translator(self.api_key, server_url=self.api_url)
        out: dict[int, str] = {}
        pending = items[:]
        for attempt in range(1, retries + 1):
            if not pending:
                break
            try:
                resp = translator.translate_text([x.text for x in pending], source_lang=self.source_lang, target_lang=self.target_lang, preserve_formatting=True, split_sentences="nonewlines", formality=self.formality)
                resp_list = resp if isinstance(resp, list) else [resp]
                if len(resp_list) != len(pending):
                    raise ProviderInvalidResponseError("Quantidade de traduções retornadas diferente da enviada")
                for src, tr in zip(pending, resp_list):
                    txt = normalize_placeholder_variants((tr.text or ""), set(re.findall(r"__PH_\d{4}__", src.text)))
                    out[src.line_number] = txt
                pending = [x for x in items if x.line_number not in out]
            except Exception as e:
                if isinstance(e, deepl.exceptions.QuotaExceededException):
                    raise ProviderQuotaExceededError(str(e)) from e
                if attempt >= retries:
                    raise ProviderTemporaryError(str(e)) from e
                time.sleep(2 ** (attempt - 1))
        return [TranslationResult(line_number=i.line_number, translation=out.get(i.line_number, ""), provider=self.provider_name, characters_sent=len(i.text)) for i in items]
