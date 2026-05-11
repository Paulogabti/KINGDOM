from __future__ import annotations

from dataclasses import dataclass, asdict
import re

from .parser import ParsedLine
from .placeholders import protect_placeholders


@dataclass
class ValidationError:
    line_number: int
    code: str
    message: str
    original: str
    translated: str


@dataclass
class ValidationResult:
    validation_passed: bool
    total_errors: int
    errors: list[ValidationError]

    @property
    def passed(self) -> bool:
        return self.validation_passed

    def to_dict(self) -> dict:
        return {
            "validation_passed": self.validation_passed,
            "total_errors": self.total_errors,
            "errors": [asdict(e) for e in self.errors],
        }


def validate_lines(original: list[ParsedLine], translated: list[ParsedLine]) -> ValidationResult:
    errors: list[ValidationError] = []
    if len(original) != len(translated):
        errors.append(ValidationError(0, "LINE_COUNT_MISMATCH", "Número de linhas diferente", str(len(original)), str(len(translated))))
        return ValidationResult(False, len(errors), errors)

    for o, t in zip(original, translated):
        if o.original_line_ending != t.original_line_ending:
            errors.append(ValidationError(o.line_number, "LINE_ENDING_CHANGED", "Quebra de linha alterada", o.original_line_ending, t.original_line_ending))
        if o.separator == "|":
            if "|" not in f"{t.chinese_part}{t.separator}{t.english_part}":
                errors.append(ValidationError(o.line_number, "SEPARATOR_MISSING", "Linha perdeu separador |", o.original_line, t.original_line))
            if o.chinese_part != t.chinese_part:
                errors.append(ValidationError(o.line_number, "CHINESE_CHANGED", "Parte chinesa alterada", o.chinese_part, t.chinese_part))
            if "__PH_" in t.english_part:
                errors.append(ValidationError(o.line_number, "INTERNAL_TOKEN_FOUND", "Token interno __PH_ encontrado", o.english_part, t.english_part))
            original_placeholders = set(protect_placeholders(o.english_part).mapping.values())
            for token in original_placeholders:
                if token not in t.english_part:
                    errors.append(ValidationError(o.line_number, "PLACEHOLDER_MISSING", f"Placeholder ausente: {token}", o.english_part, t.english_part))
            if o.english_part.strip() and not t.english_part.strip():
                errors.append(ValidationError(o.line_number, "EMPTY_TRANSLATION", "Tradução vazia para linha não vazia", o.english_part, t.english_part))
            if "\n" in t.english_part or "\r" in t.english_part:
                errors.append(ValidationError(o.line_number, "INTERNAL_LINEBREAK", "Tradução contém quebra de linha interna", o.english_part, t.english_part))
        else:
            if o.original_line != t.original_line:
                errors.append(ValidationError(o.line_number, "NON_SEPARATOR_LINE_CHANGED", "Linha sem separador foi alterada", o.original_line, t.original_line))

    return ValidationResult(not errors, len(errors), errors)
