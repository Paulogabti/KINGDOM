from __future__ import annotations

import json
from pathlib import Path
from .parser import ParsedLine


def export_translated(source_file: Path, out_dir: Path, lines: list[ParsedLine], block_on_errors: bool=False) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    base = source_file.stem
    out_file = out_dir / f"{base}.pt-BR.txt"
    report_file = out_dir / f"{base}.translation_report.json"
    errors = [l for l in lines if l.status == "error"]
    pend = [l for l in lines if l.status == "pending"]
    if block_on_errors and (errors or pend):
        raise ValueError("Exportação bloqueada por erros/pendências")
    with out_file.open("w", encoding="utf-8", newline="") as f:
        for l in lines:
            if l.separator == "|":
                pt = l.portuguese_translation if l.status == "translated" and l.portuguese_translation else l.english_part
                f.write(f"{l.chinese_part}|{pt}{l.original_line_ending}")
            else:
                f.write(f"{l.original_line}{l.original_line_ending}")
    report = {
        "source_file": str(source_file), "output_file": str(out_file),
        "total_lines": len(lines), "translatable_lines": sum(1 for l in lines if l.separator == "|"),
        "translated_lines": sum(1 for l in lines if l.status == "translated"),
        "pending_lines": len(pend), "error_lines": len(errors),
        "skipped_lines": sum(1 for l in lines if l.status == "skipped_no_separator"),
        "validation_passed": False, "list_of_errors": [l.error_message for l in errors if l.error_message],
    }
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_file, report_file
