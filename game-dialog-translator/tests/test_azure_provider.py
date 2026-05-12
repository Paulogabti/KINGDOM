from src.providers.azure_provider import AzureProvider
from src.providers.base import TranslationItem, ProviderRateLimitError, ProviderNotConfiguredError

class Resp:
    def __init__(self, code, data=None, text=''):
        self.status_code=code; self._data=data or []; self.text=text
    def json(self): return self._data

def test_azure_translate_batch(monkeypatch):
    def fake_post(*a,**k):
        return Resp(200,[{"translations":[{"text":"Olá"}]},{"translations":[{"text":"Tchau"}]}])
    import src.providers.azure_provider as m
    monkeypatch.setattr(m.requests,'post',fake_post)
    p=AzureProvider('k','https://x')
    out=p.translate_batch([TranslationItem(10,'Hello'),TranslationItem(20,'Bye')])
    assert [x.line_number for x in out]==[10,20]

def test_azure_429(monkeypatch):
    import src.providers.azure_provider as m
    monkeypatch.setattr(m.requests,'post',lambda *a,**k: Resp(429,text='rate'))
    try:
        AzureProvider('k','https://x').translate_batch([TranslationItem(1,'Hello')])
        assert False
    except ProviderRateLimitError:
        assert True

def test_azure_401(monkeypatch):
    import src.providers.azure_provider as m
    monkeypatch.setattr(m.requests,'post',lambda *a,**k: Resp(401,text='bad key'))
    try:
        AzureProvider('k','https://x').translate_batch([TranslationItem(1,'Hello')])
        assert False
    except ProviderNotConfiguredError:
        assert True
