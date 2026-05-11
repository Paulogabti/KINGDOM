from src.parser import ParsedLine
from src.validator import validate_lines

def test_validator_chinese_changed_fails():
    o = [ParsedLine(line_number=1,chinese_part="中",separator="|",english_part="A")]
    t = [ParsedLine(line_number=1,chinese_part="文",separator="|",english_part="B")]
    assert not validate_lines(o,t).passed

def test_validator_line_count_fails():
    o = [ParsedLine(line_number=1,chinese_part="中",separator="|",english_part="A")]
    t = []
    assert not validate_lines(o,t).passed

def test_validator_internal_break_fails():
    o = [ParsedLine(line_number=1,chinese_part="中",separator="|",english_part="A")]
    t = [ParsedLine(line_number=1,chinese_part="中",separator="|",english_part="linha\nquebra")]
    assert not validate_lines(o,t).passed
