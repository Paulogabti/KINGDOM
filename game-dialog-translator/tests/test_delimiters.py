from pathlib import Path

from src.exporter import export_translated
from src.parser import parse_file
from src.validator import validate_lines


def test_pipe_still_works(tmp_path: Path):
    p = tmp_path / "pipe.txt"
    p.write_text("中文|Menu\n", encoding="utf-8")
    line = parse_file(p)[0]
    assert line.separator == "|"
    assert line.chinese_part == "中文"
    assert line.english_part == "Menu"


def test_equals_works(tmp_path: Path):
    p = tmp_path / "eq.txt"
    p.write_text("菜单=Menu\n", encoding="utf-8")
    line = parse_file(p)[0]
    assert line.separator == "="
    assert line.chinese_part == "菜单"
    assert line.english_part == "Menu"


def test_split_ignores_escaped_equals(tmp_path: Path):
    p = tmp_path / "escaped.txt"
    p.write_text(r"点燃范围\=2米直径=Ignite radius\n", encoding="utf-8")
    line = parse_file(p, delimiter="equals")[0]
    assert line.chinese_part == r"点燃范围\=2米直径"


def test_export_preserves_equals(tmp_path: Path):
    p = tmp_path / "a.txt"
    lines = parse_file(_write(tmp_path, "a.txt", "菜单=Menu\n"), delimiter="equals")
    lines[0].status = "translated"
    lines[0].portuguese_translation = "Menu PT"
    out, _ = export_translated(p, tmp_path, lines)
    assert out.read_text(encoding="utf-8") == "菜单=Menu PT\n"


def test_validate_equals(tmp_path: Path):
    original = parse_file(_write(tmp_path, "o.txt", "菜单=Menu\n"), delimiter="equals")
    translated = parse_file(_write(tmp_path, "t.txt", "菜单=Menu PT\n"), delimiter="equals")
    assert validate_lines(original, translated).passed


def test_line_without_delimiter_preserved(tmp_path: Path):
    p = _write(tmp_path, "x.txt", "sem separador\n")
    line = parse_file(p, delimiter="equals")[0]
    assert line.status == "skipped_no_separator"


def test_color_tag_preserved(tmp_path: Path):
    p = _write(tmp_path, "tag.txt", r"系统=<color\=#ff0000>System</color>\n")
    line = parse_file(p, delimiter="equals")[0]
    assert line.chinese_part == "系统"
    assert line.english_part == r"<color\=#ff0000>System</color>\n"


def test_backslash_n_preserved(tmp_path: Path):
    p = _write(tmp_path, "bn.txt", r"系统=Line1\nLine2\n")
    line = parse_file(p, delimiter="equals")[0]
    assert line.english_part == r"Line1\nLine2\n"


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p
