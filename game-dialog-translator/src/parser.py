from __future__ import annotations
import logging
from dataclasses import dataclass
from pathlib import Path
from .utils import split_line_ending

@dataclass
class ParsedLine:
    line_number: int
    chinese_part: str = ""
    separator: str = ""
    english_part: str = ""
    original_line_ending: str = ""
    status: str = "pending"
    original_line: str = ""
    portuguese_translation: str = ""
    error_message: str = ""
    protected_english: str = ""
    attempts: int = 0
    characters_count: int = 0
    provider: str = ""
    fallback_used: bool = False
    provider_chain_attempted: str = ""
    characters_sent: int = 0
    translated_at: str = ""


def _read_text_with_fallback(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    logging.warning("Fallback com errors=replace para %s", path)
    return path.read_text(encoding="utf-8", errors="replace")


def parse_file(path: Path) -> list[ParsedLine]:
    text = _read_text_with_fallback(path)
    raw_lines = text.splitlines(keepends=True)
    if text and not raw_lines:
        raw_lines = [text]
    parsed: list[ParsedLine] = []
    for idx, raw in enumerate(raw_lines, start=1):
        content, ending = split_line_ending(raw)
        item = ParsedLine(line_number=idx, original_line=content, original_line_ending=ending)
        if "|" in content:
            cn, en = content.split("|", 1)
            item.chinese_part = cn
            item.separator = "|"
            item.english_part = en
            item.status = "pending"
        else:
            item.status = "skipped_no_separator"
        parsed.append(item)
    return parsed
