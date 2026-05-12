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
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after
class ProviderTemporaryError(ProviderError):
    pass
class ProviderPermanentError(ProviderError):
    pass
class ProviderInvalidResponseError(ProviderError):
    pass
