from __future__ import annotations

import argparse
from pathlib import Path
from dotenv import load_dotenv

from src.config import Settings, ensure_dirs, DEEPL_FREE_URL, DEEPL_PRO_URL
from src.exporter import export_from_progress
from src.parser import parse_file
from src.placeholders import protect_placeholders, restore_placeholders, placeholders_preserved
from src.progress import ProgressStore
from src.translator import DeepLTranslationSettings, translate_batch_with_deepl, test_deepl_connection
from src.validator import validate_lines


def resolve_url(plan: str, custom: str | None) -> str:
    return custom or (DEEPL_PRO_URL if plan == "pro" else DEEPL_FREE_URL)


def run_translate(args):
    s = Settings(); ensure_dirs(s)
    source = Path(args.input)
    lines = parse_file(source)
    store = ProgressStore(s.progress_dir, source)
    if args.overwrite:
        store.reset_progress()
    store.initialize_progress(lines)
    store.apply_existing(lines)
    if args.retry_errors:
        store.mark_errors_for_retry(); store.apply_existing(lines)

    translatable = [l for l in lines if l.separator == "|" and l.status in {"pending", "error"}]
    cfg = DeepLTranslationSettings(api_key=s.deepl_api_key, api_url=resolve_url(args.deepl_plan, args.deepl_api_url), source_lang=args.source_lang, target_lang=args.target_lang, formality=args.formality)

    for i in range(0, len(translatable), args.batch_size):
        batch = translatable[i:i + args.batch_size]
        items = []; maps = {}
        for l in batch:
            p = protect_placeholders(l.english_part)
            maps[l.line_number] = p.mapping
            l.protected_english = p.text
            items.append({"line_number": l.line_number, "text": p.text})
        result = translate_batch_with_deepl(items, cfg)
        by_ln = {x["line_number"]: x["translation"] for x in result}
        for l in batch:
            l.attempts += 1
            t = by_ln.get(l.line_number, "")
            if not t:
                l.status = "error"; l.error_message = "Falha DeepL"
                continue
            r = restore_placeholders(t, maps[l.line_number])
            if not placeholders_preserved(r, maps[l.line_number]):
                l.status = "error"; l.error_message = "Placeholder alterado"
                continue
            l.portuguese_translation = r; l.status = "translated"; l.characters_count = len(l.english_part)
        store.save_batch(batch, batch_number=(i // args.batch_size) + 1)


def main():
    load_dotenv()
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("translate")
    t.add_argument("--input", required=True); t.add_argument("--output-dir", required=True)
    t.add_argument("--batch-size", type=int, default=20); t.add_argument("--deepl-plan", choices=["free", "pro"], default="free")
    t.add_argument("--deepl-api-url"); t.add_argument("--source-lang", default="EN"); t.add_argument("--target-lang", default="PT-BR")
    t.add_argument("--formality", default="prefer_more"); t.add_argument("--resume", action="store_true"); t.add_argument("--overwrite", action="store_true"); t.add_argument("--retry-errors", action="store_true")
    r = sub.add_parser("resume")
    for a in t._actions:
        if a.dest in {"help", "cmd", "resume", "overwrite", "retry_errors"}: continue
        r._add_action(a)
    r.set_defaults(resume=True, overwrite=False, retry_errors=False)

    v = sub.add_parser("validate"); v.add_argument("--original", required=True); v.add_argument("--translated", required=True)
    e = sub.add_parser("export"); e.add_argument("--input", required=True); e.add_argument("--output-dir", required=True); e.add_argument("--force", action="store_true")
    td = sub.add_parser("test-deepl"); td.add_argument("--deepl-plan", choices=["free", "pro"], default="free"); td.add_argument("--deepl-api-url")
    a = p.parse_args()
    s = Settings(); ensure_dirs(s)

    if a.cmd in {"translate", "resume"}:
        run_translate(a)
        store = ProgressStore(s.progress_dir, Path(a.input))
        out_file, report_file, validation = export_from_progress(Path(a.input), Path(a.output_dir), store, force_export=False, metadata={"deepl_endpoint_used": resolve_url(a.deepl_plan, a.deepl_api_url), "source_lang": a.source_lang, "target_lang": a.target_lang, "batch_size": a.batch_size})
        if out_file:
            print(f"Arquivo final: {out_file}")
        print(f"Relatório JSON: {report_file}")
        if not validation.validation_passed:
            print("Validação falhou antes da exportação.")
    elif a.cmd == "export":
        store = ProgressStore(s.progress_dir, Path(a.input))
        out_file, report_file, validation = export_from_progress(Path(a.input), Path(a.output_dir), store, force_export=a.force)
        if out_file:
            print(f"Arquivo final: {out_file}")
        print(f"Relatório JSON: {report_file}")
        if not validation.validation_passed:
            print("Validação falhou.")
    elif a.cmd == "test-deepl":
        ok, msg = test_deepl_connection(DeepLTranslationSettings(api_key=s.deepl_api_key, api_url=resolve_url(a.deepl_plan, a.deepl_api_url)))
        print(msg)
        raise SystemExit(0 if ok else 1)
    else:
        res = validate_lines(parse_file(Path(a.original)), parse_file(Path(a.translated)))
        print("OK" if res.validation_passed else "FALHOU")
        for err in res.errors:
            print(f"linha={err.line_number} code={err.code} {err.message}")


if __name__ == "__main__":
    main()
