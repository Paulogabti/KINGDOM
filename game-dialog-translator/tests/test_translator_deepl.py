from src.translator import translate_batch_with_deepl, DeepLTranslationSettings

class FakeResp:
    def __init__(self,t): self.text=t
class FakeTranslator:
    def __init__(self,*a,**k): self.calls=[]
    def translate_text(self,texts,**kwargs):
        self.calls.append((texts,kwargs))
        return [FakeResp("Ola"), FakeResp("__PH_0001__ pode ajudar __PH_0002__?")]

def test_deepl_mapping(monkeypatch):
    import src.translator as t
    monkeypatch.setattr(t.deepl, "Translator", FakeTranslator)
    items=[{"line_number":10,"text":"Hello"},{"line_number":20,"text":"Can __PH_0001__ help __PH_0002__?"}]
    out = translate_batch_with_deepl(items, DeepLTranslationSettings(api_key="k",api_url="u"))
    assert out[0]["line_number"] == 10
    assert out[1]["line_number"] == 20

def test_deepl_quota_error(monkeypatch):
    import src.translator as t
    class BadTranslator:
        def __init__(self,*a,**k): pass
        def translate_text(self,*a,**k):
            raise t.deepl.exceptions.QuotaExceededException("quota")
    monkeypatch.setattr(t.deepl, "Translator", BadTranslator)
    out = translate_batch_with_deepl([{"line_number":1,"text":"Hello"}], DeepLTranslationSettings(api_key="k",api_url="u"))
    assert out[0]["translation"] == ""
