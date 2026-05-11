from pathlib import Path
from src.parser import ParsedLine
from src.exporter import export_translated
from src.utils import calc_lines_per_minute, calc_eta_seconds

def test_export_same_line_count(tmp_path: Path):
    lines = [ParsedLine(line_number=1,chinese_part="中",separator="|",english_part="A",portuguese_translation="B",status="translated",original_line_ending="\n"),
             ParsedLine(line_number=2,original_line="sem",status="skipped_no_separator",original_line_ending="\n")]
    out,_ = export_translated(tmp_path/"a.txt", tmp_path, lines)
    assert len(out.read_text(encoding="utf-8").splitlines()) == 2

def test_export_no_separator_exact(tmp_path: Path):
    lines = [ParsedLine(line_number=1,original_line="apenas texto",status="skipped_no_separator",original_line_ending="\n")]
    out,_ = export_translated(tmp_path/"a.txt", tmp_path, lines)
    assert out.read_text(encoding="utf-8") == "apenas texto\n"

def test_eta_calc():
    lpm = calc_lines_per_minute(120,120)
    assert round(lpm,1) == 60.0
    assert int(calc_eta_seconds(60,lpm)) == 60
