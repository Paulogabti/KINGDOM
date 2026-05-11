from __future__ import annotations

from dataclasses import dataclass
from .parser import ParsedLine

@dataclass
class ValidationResult:
    passed: bool
    errors: list[str]


def validate_lines(original: list[ParsedLine], translated: list[ParsedLine]) -> ValidationResult:
    errs = []
    if len(original) != len(translated):
        errs.append("Número de linhas diferente")
        return ValidationResult(False, errs)
    for o, t in zip(original, translated):
        if o.chinese_part != t.chinese_part:
            errs.append(f"Linha {o.line_number}: parte chinesa alterada")
        if o.separator == "|" and t.separator != "|":
            errs.append(f"Linha {o.line_number}: separador removido")
        if "__PH_" in t.english_part:
            errs.append(f"Linha {o.line_number}: placeholder interno restante")
        if "\n" in t.english_part or "\r" in t.english_part:
            errs.append(f"Linha {o.line_number}: quebra de linha interna na tradução")
        if o.separator == "|" and o.english_part.strip() and not t.english_part.strip():
            errs.append(f"Linha {o.line_number}: tradução vazia")
        if o.original_line_ending == "\r" and t.original_line_ending != "\r":
            errs.append(f"Linha {o.line_number}: perdeu CR")
    return ValidationResult(not errs, errs)
