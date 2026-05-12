from src.translator import translate_with_fallback
from src.providers.base import TranslationItem, ProviderQuotaExceededError
from cli import main
import sys

class D:
    def __init__(self,*a,**k): pass
    def translate_batch(self, items, retries=3):
        return [type('R',(),{'line_number':i.line_number,'translation':'ok','provider':'deepl','characters_sent':len(i.text)}) for i in items]
class DQ(D):
    def translate_batch(self, items, retries=3):
        raise ProviderQuotaExceededError('q')
class A(D):
    def translate_batch(self, items):
        return [type('R',(),{'line_number':i.line_number,'translation':'ok2','provider':'azure','characters_sent':len(i.text)}) for i in items]

def test_orchestrator_uses_deepl():
    r,m=translate_with_fallback([TranslationItem(1,'x')],D(),A(),True)
    assert m['provider']=='deepl'

def test_orchestrator_uses_azure_on_quota():
    r,m=translate_with_fallback([TranslationItem(1,'x')],DQ(),A(),True)
    assert m['provider']=='azure' and m['fallback_used']

def test_orchestrator_no_fallback():
    try:
        translate_with_fallback([TranslationItem(1,'x')],DQ(),A(),False)
        assert False
    except ProviderQuotaExceededError:
        assert True
