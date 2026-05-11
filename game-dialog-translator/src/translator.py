from __future__ import annotations
import logging, re, time
from dataclasses import dataclass
try:
    import deepl
except ModuleNotFoundError:
    class _DeepLException(Exception):
        pass
    class _QuotaExceededException(_DeepLException):
        pass
    class _DummyExceptions:
        DeepLException = _DeepLException
        QuotaExceededException = _QuotaExceededException
    class _DummyDeepL:
        exceptions = _DummyExceptions()
        class Translator:
            def __init__(self,*a,**k):
                raise RuntimeError("Dependência deepl ausente")
    deepl = _DummyDeepL()

PH_VAR = re.compile(r"_+\s*PH_(\d{4})\s*_+|\bPH_(\d{4})\b")

@dataclass
class DeepLTranslationSettings:
    api_key: str
    api_url: str
    source_lang: str = "EN"
    target_lang: str = "PT-BR"
    formality: str = "prefer_more"

def normalize_placeholder_variants(text: str, valid_tokens: set[str]) -> str:
    def repl(m):
        num = m.group(1) or m.group(2)
        cand = f"__PH_{num}__"
        return cand if cand in valid_tokens else m.group(0)
    return PH_VAR.sub(repl, text)

def translate_batch_with_deepl(items: list[dict], settings: DeepLTranslationSettings, retries: int = 3) -> list[dict]:
    if not settings.api_key:
        raise ValueError("DEEPL_API_KEY ausente")
    translator = deepl.Translator(settings.api_key, server_url=settings.api_url)
    out: dict[int, str] = {}
    pending = items[:]
    for attempt in range(1, retries + 1):
        if not pending: break
        try:
            resp = translator.translate_text([x["text"] for x in pending], source_lang=settings.source_lang, target_lang=settings.target_lang, preserve_formatting=True, split_sentences="nonewlines", formality=settings.formality)
            resp_list = resp if isinstance(resp, list) else [resp]
            if len(resp_list) != len(pending):
                raise RuntimeError("Quantidade de traduções retornadas diferente da enviada")
            for src, tr in zip(pending, resp_list):
                txt = normalize_placeholder_variants((tr.text or ""), set(re.findall(r"__PH_\d{4}__", src["text"])))
                if "\n" in txt or "\r" in txt:
                    raise RuntimeError("Tradução com quebra de linha interna")
                out[src["line_number"]] = txt
            pending = [x for x in items if x["line_number"] not in out]
        except Exception as e:
            if deepl is not None and isinstance(e, deepl.exceptions.QuotaExceededException):
                logging.error("Quota exceeded (456): %s", e)
                break
            logging.error("Erro DeepL tentativa %s: %s", attempt, e)
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
    return [{"line_number": i["line_number"], "translation": out.get(i["line_number"], "")} for i in items]

def test_deepl_connection(settings: DeepLTranslationSettings) -> tuple[bool, str]:
    try:
        rs = translate_batch_with_deepl([{"line_number": 1, "text": "Hello"}], settings, retries=1)
        return (bool(rs and rs[0]["translation"]), "Conexão DeepL OK")
    except Exception as e:
        return False, f"Falha ao testar conexão DeepL: {e}"
