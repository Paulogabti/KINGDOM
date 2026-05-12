from __future__ import annotations
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from .utils import split_line_ending


class DelimiterMode(str, Enum):
    AUTO = "auto"
    PIPE = "pipe"
    EQUALS = "equals"


DELIMITER_CHAR = {
    DelimiterMode.PIPE: "|",
    DelimiterMode.EQUALS: "=",
}

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

    @property
    def key_part(self) -> str:
        return self.chinese_part

    @key_part.setter
    def key_part(self, value: str) -> None:
        self.chinese_part = value

    @property
    def value_part(self) -> str:
        return self.english_part

    @value_part.setter
    def value_part(self, value: str) -> None:
        self.english_part = value


def _count_unescaped(text: str, needle: str) -> int:
    count = 0
    escaped = False
    for ch in text:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == needle:
            count += 1
    return count


def _split_first_unescaped(text: str, needle: str) -> tuple[str, str] | None:
    escaped = False
    for idx, ch in enumerate(text):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == needle:
            return text[:idx], text[idx + 1 :]
    return None


def detect_delimiter(text: str, mode: str = "auto") -> str:
    mode = (mode or "auto").lower()
    if mode == DelimiterMode.PIPE.value:
        return "|"
    if mode == DelimiterMode.EQUALS.value:
        return "="
    pipe_lines = 0
    equals_lines = 0
    for line in text.splitlines():
        if _count_unescaped(line, "|") > 0:
            pipe_lines += 1
        if _count_unescaped(line, "=") > 0:
            equals_lines += 1
    return "|" if pipe_lines >= equals_lines else "="


def _read_text_with_fallback(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    logging.warning("Fallback com errors=replace para %s", path)
    return path.read_text(encoding="utf-8", errors="replace")


def parse_file(path: Path, delimiter: str = "auto") -> list[ParsedLine]:
    text = _read_text_with_fallback(path)
    detected_delimiter = detect_delimiter(text, mode=delimiter)
    raw_lines = text.splitlines(keepends=True)
    if text and not raw_lines:
        raw_lines = [text]
    parsed: list[ParsedLine] = []
    for idx, raw in enumerate(raw_lines, start=1):
        content, ending = split_line_ending(raw)
        item = ParsedLine(line_number=idx, original_line=content, original_line_ending=ending)
        split = _split_first_unescaped(content, detected_delimiter)
        if split is not None:
            cn, en = split
            item.chinese_part = cn
            item.separator = detected_delimiter
            item.english_part = en
            item.status = "pending"
        else:
            item.status = "skipped_no_separator"
        parsed.append(item)
    return parsed
