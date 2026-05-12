from __future__ import annotations
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.config import Settings, ensure_dirs, DEEPL_FREE_BASE_URL, DEEPL_PRO_BASE_URL
from src.exporter import export_from_progress
from src.parser import parse_file
from src.placeholders import protect_placeholders, restore_placeholders, placeholders_preserved
from src.progress import ProgressStore
from src.translator import DeepLTranslationSettings, test_deepl_connection, translate_with_fallback, test_azure_connection
from src.providers import TranslationItem
from src.providers.deepl_provider import DeepLProvider
from src.providers.azure_provider import AzureProvider
from src.validator import validate_lines

def resolve_url(plan: str, custom: str | None) -> str:
    return custom or (DEEPL_PRO_BASE_URL if plan == "pro" else DEEPL_FREE_BASE_URL)

def run_translate(args):
    s = Settings(); ensure_dirs(s)
    source = Path(args.input); lines = parse_file(source); store = ProgressStore(s.progress_dir, source)
    if args.overwrite: store.reset_progress()
    store.initialize_progress(lines); store.apply_existing(lines)
    if args.retry_errors: store.mark_errors_for_retry(); store.apply_existing(lines)
    translatable = [l for l in lines if l.separator == "|" and l.status in {"pending", "error"}]
    deepl = DeepLProvider(s.deepl_api_key, resolve_url(args.deepl_plan, args.deepl_api_url), args.source_lang, args.target_lang, args.formality) if args.provider == 'deepl' else None
    az_key = args.azure_key or s.azure_translator_key
    azure = AzureProvider(az_key, args.azure_endpoint or s.azure_translator_endpoint, args.azure_region or s.azure_translator_region, s.azure_source_lang, s.azure_target_lang) if args.provider == 'azure' or (args.fallback=='azure' and not args.no_fallback) else None
    for i in range(0, len(translatable), args.batch_size):
        batch = translatable[i:i + args.batch_size]; items=[]; maps={}
        for l in batch:
            p = protect_placeholders(l.english_part); maps[l.line_number]=p.mapping; l.protected_english=p.text
            items.append(TranslationItem(line_number=l.line_number,text=p.text))
        try:
            results, meta = translate_with_fallback(items, deepl=deepl, azure=azure, enable_fallback=(not args.no_fallback))
            by_ln={x.line_number:x for x in results}
            for l in batch:
                r=by_ln.get(l.line_number)
                if not r or not r.translation: l.status='error'; l.error_message='Falha providers'; continue
                rt=restore_placeholders(r.translation,maps[l.line_number])
                if not placeholders_preserved(rt,maps[l.line_number]): l.status='error'; l.error_message='Placeholder alterado'; continue
                l.portuguese_translation=rt; l.status='translated'; l.characters_count=len(l.english_part); l.provider=r.provider; l.fallback_used=meta['fallback_used']; l.provider_chain_attempted=','.join(meta['provider_chain_attempted']); l.characters_sent=r.characters_sent
        except Exception as e:
            for l in batch: l.status='error'; l.error_message=str(e)
        store.save_batch(batch,batch_number=(i//args.batch_size)+1)

def main():
    load_dotenv(); p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    t=sub.add_parser('translate'); t.add_argument('--input',required=True); t.add_argument('--output-dir',required=True); t.add_argument('--batch-size',type=int,default=20); t.add_argument('--deepl-plan',choices=['free','pro'],default='free'); t.add_argument('--deepl-api-url'); t.add_argument('--source-lang',default='EN'); t.add_argument('--target-lang',default='PT-BR'); t.add_argument('--formality',default='prefer_more'); t.add_argument('--resume',action='store_true'); t.add_argument('--overwrite',action='store_true'); t.add_argument('--retry-errors',action='store_true'); t.add_argument('--provider',choices=['deepl','azure'],default='deepl'); t.add_argument('--fallback',choices=['azure'],default='azure'); t.add_argument('--no-fallback',action='store_true'); t.add_argument('--azure-key'); t.add_argument('--azure-endpoint'); t.add_argument('--azure-region')
    r=sub.add_parser('resume');
    for a in t._actions:
        if a.dest in {'help','cmd','resume','overwrite','retry_errors'}: continue
        r._add_action(a)
    r.set_defaults(resume=True,overwrite=False,retry_errors=False)
    v=sub.add_parser('validate'); v.add_argument('--original',required=True); v.add_argument('--translated',required=True)
    e=sub.add_parser('export'); e.add_argument('--input',required=True); e.add_argument('--output-dir',required=True); e.add_argument('--force',action='store_true')
    td=sub.add_parser('test-deepl'); td.add_argument('--deepl-plan',choices=['free','pro'],default='free'); td.add_argument('--deepl-api-url')
    ta=sub.add_parser('test-azure')
    sub.add_parser('providers')
    a=p.parse_args(); s=Settings(); ensure_dirs(s)
    if a.cmd in {'translate','resume'}:
        run_translate(a); store=ProgressStore(s.progress_dir,Path(a.input)); export_from_progress(Path(a.input),Path(a.output_dir),store,force_export=False)
    elif a.cmd=='test-deepl':
        ok,msg=test_deepl_connection(DeepLTranslationSettings(api_key=s.deepl_api_key,api_url=resolve_url(a.deepl_plan,a.deepl_api_url))); print(msg); raise SystemExit(0 if ok else 1)
    elif a.cmd=='test-azure':
        res=test_azure_connection(AzureProvider(s.azure_translator_key,s.azure_translator_endpoint,s.azure_translator_region,s.azure_source_lang,s.azure_target_lang)); print(res.message); raise SystemExit(0 if res.ok else 1)
    elif a.cmd=='providers':
        print('deepl: enabled' if s.deepl_api_key else 'deepl: not configured')
        print('azure: enabled' if s.azure_translate_enabled and s.azure_translator_key else 'azure: not configured')
    elif a.cmd=='export':
        store=ProgressStore(s.progress_dir,Path(a.input)); export_from_progress(Path(a.input),Path(a.output_dir),store,force_export=a.force)
    else:
        res=validate_lines(parse_file(Path(a.original)),parse_file(Path(a.translated))); print('OK' if res.validation_passed else 'FALHOU')

if __name__ == '__main__':
    main()
