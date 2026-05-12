from __future__ import annotations
from dataclasses import dataclass

@dataclass
class TranslationItem:
    line_number: int
    text: str

@dataclass
class TranslationResult:
    line_number: int
    translation: str
    provider: str
    characters_sent: int

@dataclass
class ProviderTestResult:
    provider: str
    ok: bool
    message: str

class ProviderError(Exception):
    pass
class ProviderNotConfiguredError(ProviderError):
    pass
class ProviderQuotaExceededError(ProviderError):
    pass
class ProviderRateLimitError(ProviderError):
    pass
class ProviderTemporaryError(ProviderError):
    pass
class ProviderPermanentError(ProviderError):
    pass
class ProviderInvalidResponseError(ProviderError):
    pass
