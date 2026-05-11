from __future__ import annotations
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.config import Settings, ensure_dirs, DEEPL_FREE_URL, DEEPL_PRO_URL
from src.parser import parse_file
from src.exporter import export_translated
from src.progress import ProgressStore
from src.utils import file_hash, now_ts, calc_lines_per_minute, calc_eta_seconds, calc_percent, fmt_duration
from src.placeholders import protect_placeholders, restore_placeholders, placeholders_preserved
from src.translator import DeepLTranslationSettings, translate_batch_with_deepl, test_deepl_connection

def resolve_url(plan: str, custom: str | None) -> str:
    return custom or (DEEPL_PRO_URL if plan == "pro" else DEEPL_FREE_URL)

def run_translate(args):
    s = Settings(); ensure_dirs(s)
    lines = parse_file(Path(args.input))
    translatable = [l for l in lines if l.separator == "|"]
    cfg = DeepLTranslationSettings(api_key=s.deepl_api_key, api_url=resolve_url(args.deepl_plan, args.deepl_api_url), source_lang=args.source_lang, target_lang=args.target_lang, formality=args.formality)
    start = now_ts(); done=0; chars=0
    total_batches = (len(translatable)+args.batch_size-1)//args.batch_size
    for i in range(0, len(translatable), args.batch_size):
        batch = translatable[i:i+args.batch_size]
        items=[]; maps={}
        for l in batch:
            p = protect_placeholders(l.english_part); maps[l.line_number]=p.mapping; l.protected_english=p.text; items.append({"line_number":l.line_number,"text":p.text})
        result = translate_batch_with_deepl(items, cfg)
        by_ln = {x['line_number']:x['translation'] for x in result}
        for l in batch:
            t = by_ln.get(l.line_number, "")
            if not t: l.status="error"; l.error_message="Falha DeepL"; continue
            r = restore_placeholders(t, maps[l.line_number])
            if not placeholders_preserved(r, maps[l.line_number]): l.status="error"; l.error_message="Placeholder alterado"; continue
            l.portuguese_translation=r; l.status="translated"; done+=1; chars += len(l.english_part)
        elapsed=now_ts()-start; spd=calc_lines_per_minute(done,elapsed); eta=calc_eta_seconds(len(translatable)-done,spd)
        print(f"Arquivo: {Path(args.input).name}\nProgresso: {done}/{len(translatable)} linhas traduzíveis ({calc_percent(done,len(translatable)):.1f}%)\nLote: {(i//args.batch_size)+1}/{total_batches}\nVelocidade: {spd:.1f} linhas/min\nCaracteres traduzidos: {chars}\nTempo decorrido: {fmt_duration(elapsed)}\nETA: {fmt_duration(eta)}\nErros: {sum(1 for x in lines if x.status=='error')}\n")
    export_translated(Path(args.input), Path(args.output_dir), lines)

def main():
    load_dotenv(); p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd", required=True)
    t=sub.add_parser("translate"); t.add_argument("--input", required=True); t.add_argument("--output-dir", required=True); t.add_argument("--batch-size", type=int, default=20); t.add_argument("--deepl-plan", choices=["free","pro"], default="free"); t.add_argument("--deepl-api-url"); t.add_argument("--source-lang", default="EN"); t.add_argument("--target-lang", default="PT-BR"); t.add_argument("--formality", default="prefer_more")
    r=sub.add_parser("resume"); r.add_argument("--input", required=True); r.add_argument("--output-dir", required=True); r.add_argument("--batch-size", type=int, default=20); r.add_argument("--deepl-plan", choices=["free","pro"], default="free"); r.add_argument("--deepl-api-url"); r.add_argument("--source-lang", default="EN"); r.add_argument("--target-lang", default="PT-BR"); r.add_argument("--formality", default="prefer_more")
    v=sub.add_parser("validate"); v.add_argument("--original", required=True); v.add_argument("--translated", required=True)
    td=sub.add_parser("test-deepl"); td.add_argument("--deepl-plan", choices=["free","pro"], default="free"); td.add_argument("--deepl-api-url")
    a=p.parse_args()
    if a.cmd in {"translate","resume"}: run_translate(a)
    elif a.cmd=="test-deepl":
        s=Settings(); ok,msg=test_deepl_connection(DeepLTranslationSettings(api_key=s.deepl_api_key, api_url=resolve_url(a.deepl_plan,a.deepl_api_url))); print(msg); raise SystemExit(0 if ok else 1)
    else:
        from src.validator import validate_lines
        res = validate_lines(parse_file(Path(a.original)), parse_file(Path(a.translated))); print("OK" if res.passed else "FALHOU"); [print(e) for e in res.errors]

if __name__ == "__main__": main()
