from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from .parser import parse_file, detect_delimiter
from .progress import ProgressStore
from .validator import validate_lines
from .utils import now_ts, calc_lines_per_minute

# ... keep previous functions

def export_from_progress(source_file: Path, out_dir: Path, store: ProgressStore, force_export: bool = False, block_on_pending_error: bool = False, metadata: dict | None = None, delimiter: str = "auto"):
    started = now_ts(); original = parse_file(source_file, delimiter=delimiter); store.apply_existing(original)
    chosen_delimiter = detect_delimiter(source_file.read_text(encoding="utf-8", errors="replace"), mode=delimiter)
    pending = sum(1 for l in original if l.status == "pending"); errors = sum(1 for l in original if l.status == "error")
    if block_on_pending_error and (pending > 0 or errors > 0) and not force_export: raise ValueError("Exportação bloqueada: existem linhas pending/error.")
    reconstructed=[]
    for l in original:
        if l.separator in ("|", "="):
            pt = l.portuguese_translation if l.status == "translated" and l.portuguese_translation else l.english_part
            l.english_part = pt; l.original_line = f"{l.chinese_part}{l.separator}{pt}"
        reconstructed.append(l)
    validation = validate_lines(parse_file(source_file, delimiter=delimiter), reconstructed)
    base = source_file.stem; out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{base}.pt-BR.txt"; report_file = out_dir / f"{base}.translation_report.json"
    if validation.validation_passed or force_export:
        with out_file.open("w", encoding="utf-8", newline="") as f:
            for l in reconstructed:
                f.write((f"{l.chinese_part}{l.separator}{l.english_part}" if l.separator in ("|", "=") else l.original_line) + l.original_line_ending)
    report = _build_report(source_file, out_file, store, reconstructed, validation.to_dict(), started, metadata, force_export, chosen_delimiter)
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return (out_file if validation.validation_passed or force_export else None), report_file, validation

def _build_report(source_file, out_file, store, lines, validation_dict, started, metadata, force_export, delimiter):
    metadata = metadata or {}; finished = now_ts(); elapsed = finished - started
    translated = sum(1 for l in lines if l.status == "translated"); chars = sum(l.characters_count for l in lines if l.status == "translated")
    providers_used = sorted({getattr(l, "provider", "") for l in lines if getattr(l, "provider", "")})
    lines_by_provider = {}
    characters_by_provider = {}
    fallback_events = 0
    for l in lines:
        pr = getattr(l, "provider", "")
        if pr:
            lines_by_provider[pr] = lines_by_provider.get(pr, 0) + (1 if l.status == "translated" else 0)
            characters_by_provider[pr] = characters_by_provider.get(pr, 0) + (l.characters_sent or l.characters_count or 0)
        if getattr(l, "fallback_used", False):
            fallback_events += 1
    return {"source_file": str(source_file),"output_file": str(out_file),"file_hash": getattr(store,'file_hash',''),"delimiter": delimiter,"total_lines": len(lines),"translatable_lines": sum(1 for l in lines if l.separator in ("|", "=")),"translated_lines": translated,"pending_lines": sum(1 for l in lines if l.status == "pending"),"error_lines": sum(1 for l in lines if l.status == "error"),"skipped_lines": sum(1 for l in lines if l.status == "skipped_no_separator"),"validation_passed": validation_dict["validation_passed"],"list_of_errors": validation_dict["errors"],"started_at": datetime.utcfromtimestamp(started).isoformat(),"finished_at": datetime.utcfromtimestamp(finished).isoformat(),"elapsed_seconds": elapsed,"average_lines_per_minute": calc_lines_per_minute(translated, elapsed),"average_characters_per_minute": calc_lines_per_minute(chars, elapsed),"characters_translated": chars,"provider": metadata.get("provider", providers_used[0] if providers_used else "azure"),"deepl_endpoint_used": metadata.get("deepl_endpoint_used", ""),"source_lang": metadata.get("source_lang", "EN"),"target_lang": metadata.get("target_lang", "PT-BR"),"batch_size": metadata.get("batch_size", 20),"force_export": force_export, "providers_used": providers_used, "lines_by_provider": lines_by_provider, "characters_by_provider": characters_by_provider, "fallback_events": fallback_events, "provider_errors": [l.error_message for l in lines if l.status=="error" and l.error_message]}

def export_translated(source_file: Path, out_dir: Path, lines: list, block_on_errors: bool=False):
    out_dir.mkdir(parents=True, exist_ok=True); base = source_file.stem
    out_file = out_dir / f"{base}.pt-BR.txt"; report_file = out_dir / f"{base}.translation_report.json"
    pending = any(l.status=="pending" for l in lines); errors = any(l.status=="error" for l in lines)
    if block_on_errors and (pending or errors): raise ValueError("Exportação bloqueada por erros/pendências")
    with out_file.open("w", encoding="utf-8", newline="") as f:
        for l in lines:
            if l.separator in ("|", "="):
                pt=l.portuguese_translation if l.status=="translated" and l.portuguese_translation else l.english_part
                f.write(f"{l.chinese_part}{l.separator}{pt}{l.original_line_ending}")
            else:
                f.write(f"{l.original_line}{l.original_line_ending}")
    report_file.write_text(json.dumps({"source_file":str(source_file),"output_file":str(out_file)}, ensure_ascii=False), encoding='utf-8')
    return out_file, report_file
