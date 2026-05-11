from src.placeholders import protect_placeholders, restore_placeholders

def test_placeholder_protect_restore():
    txt = "NI wants to go to PLACE1NAME with SN1MING."
    p = protect_placeholders(txt)
    restored = restore_placeholders(p.text, p.mapping)
    assert "NI" in restored and "PLACE1NAME" in restored and "SN1MING" in restored
