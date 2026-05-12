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

def build_providers(args, s: Settings):
    provider = (args.provider or s.translation_provider).lower()
    enable_fallback = s.enable_provider_fallback and (not args.no_fallback)
    deepl = None
    azure = None
    if provider == "azure":
        azure = AzureProvider(args.azure_key or s.azure_translator_key, args.azure_endpoint or s.azure_translator_endpoint, args.azure_region or s.azure_translator_region, s.azure_source_lang, s.azure_target_lang)
        if enable_fallback and "deepl" in s.fallback_providers.split(",") and s.deepl_api_key:
            deepl = DeepLProvider(s.deepl_api_key, resolve_url(args.deepl_plan, args.deepl_api_url), args.source_lang, args.target_lang, args.formality)
    else:
        deepl = DeepLProvider(s.deepl_api_key, resolve_url(args.deepl_plan, args.deepl_api_url), args.source_lang, args.target_lang, args.formality)
        if enable_fallback and "azure" in s.fallback_providers.split(","):
            azure = AzureProvider(args.azure_key or s.azure_translator_key, args.azure_endpoint or s.azure_translator_endpoint, args.azure_region or s.azure_translator_region, s.azure_source_lang, s.azure_target_lang)
    return provider, enable_fallback, deepl, azure

def run_translate(args):
    s = Settings(); ensure_dirs(s)
    source = Path(args.input); lines = parse_file(source); store = ProgressStore(s.progress_dir, source)
    existing_db = store.db_path.exists() and store.db_path.stat().st_size > 0
    store.backup()
    if args.overwrite:
        store.reset_progress()
        existing_db = False

    if args.resume and existing_db:
        # Em resume, sempre carregar progresso existente antes de qualquer seleção.
        store.apply_existing(lines)
        loaded_rows = len(store.load_progress())
        if loaded_rows == 0:
            raise RuntimeError(
                f"--resume solicitado e SQLite existente em {store.db_path}, mas nenhum progresso foi carregado."
            )
    else:
        store.initialize_progress(lines)
        store.apply_existing(lines)
    if args.retry_errors: store.mark_errors_for_retry(); store.apply_existing(lines)

    provider, enable_fallback, deepl, azure = build_providers(args, s)
    if provider == "azure" and (not s.azure_translate_enabled or not (args.azure_key or s.azure_translator_key) or not (args.azure_endpoint or s.azure_translator_endpoint) or not (args.azure_region or s.azure_translator_region)):
        raise RuntimeError("Nenhum provider disponível. Verifique AZURE_TRANSLATOR_KEY, AZURE_TRANSLATOR_ENDPOINT e AZURE_TRANSLATOR_REGION.")

    translatable = [l for l in lines if l.separator == "|" and l.status in ({"error"} if args.retry_errors else {"pending", "error"})]
    summary = store.get_summary()
    effective = [provider] + ([p for p in s.fallback_providers.split(",") if p] if enable_fallback else [])
    print(f"Provider principal: {provider}")
    print(f"Fallback ativo: {str(enable_fallback).lower()}")
    print(f"Providers efetivos: {','.join(effective)}")
    print(f"Hash: {store.file_hash}")
    print(f"Translated existentes: {summary['translated_lines']}")
    print(f"Pending selecionadas: {sum(1 for x in translatable if x.status=='pending')}")
    print(f"Errors existentes: {summary['error_lines']}")
    print(f"Skipped: {summary['skipped_lines']}")
    print(f"Batch size: {args.batch_size}")

    for i in range(0, len(translatable), args.batch_size):
        batch = translatable[i:i + args.batch_size]; items=[]; maps={}
        for l in batch:
            p = protect_placeholders(l.english_part); maps[l.line_number]=p.mapping; l.protected_english=p.text
            items.append(TranslationItem(line_number=l.line_number,text=p.text))
        results, meta = translate_with_fallback(items, deepl=deepl, azure=azure, enable_fallback=enable_fallback)
        by_ln={x.line_number:x for x in results}
        for l in batch:
            r=by_ln.get(l.line_number)
            if not r or not r.translation: l.status='error'; l.error_message='Falha providers'; continue
            rt=restore_placeholders(r.translation,maps[l.line_number])
            if not placeholders_preserved(rt,maps[l.line_number]): l.status='error'; l.error_message='Placeholder alterado'; continue
            l.portuguese_translation=rt; l.status='translated'; l.characters_count=len(l.english_part); l.provider=r.provider; l.fallback_used=meta['fallback_used']; l.provider_chain_attempted=','.join(meta['provider_chain_attempted']); l.characters_sent=r.characters_sent
        store.save_batch(batch,batch_number=(i//args.batch_size)+1)

def main():
    load_dotenv(); p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    s = Settings()
    t=sub.add_parser('translate'); t.add_argument('--input',required=True); t.add_argument('--output-dir',required=True); t.add_argument('--batch-size',type=int,default=20); t.add_argument('--deepl-plan',choices=['free','pro'],default='free'); t.add_argument('--deepl-api-url'); t.add_argument('--source-lang',default='EN'); t.add_argument('--target-lang',default='PT-BR'); t.add_argument('--formality',default='prefer_more'); t.add_argument('--resume',action='store_true'); t.add_argument('--overwrite',action='store_true'); t.add_argument('--retry-errors',action='store_true'); t.add_argument('--provider',choices=['deepl','azure'],default=s.translation_provider); t.add_argument('--no-fallback',action='store_true'); t.add_argument('--azure-key'); t.add_argument('--azure-endpoint'); t.add_argument('--azure-region')
    sub.add_parser('validate').add_argument('--original',required=False)
    v=sub.choices['validate']; v.add_argument('--translated',required=True)
    e=sub.add_parser('export'); e.add_argument('--input',required=True); e.add_argument('--output-dir',required=True); e.add_argument('--force',action='store_true')
    td=sub.add_parser('test-deepl'); td.add_argument('--deepl-plan',choices=['free','pro'],default='free'); td.add_argument('--deepl-api-url')
    sub.add_parser('test-azure'); sub.add_parser('providers')
    a=p.parse_args(); s=Settings(); ensure_dirs(s)
    if a.cmd=='translate':
        run_translate(a); store=ProgressStore(s.progress_dir,Path(a.input)); export_from_progress(Path(a.input),Path(a.output_dir),store,force_export=False,metadata={"provider":a.provider,"batch_size":a.batch_size})
    elif a.cmd=='test-deepl':
        ok,msg=test_deepl_connection(DeepLTranslationSettings(api_key=s.deepl_api_key,api_url=resolve_url(a.deepl_plan,a.deepl_api_url))); print(msg); raise SystemExit(0 if ok else 1)
    elif a.cmd=='test-azure':
        res=test_azure_connection(AzureProvider(s.azure_translator_key,s.azure_translator_endpoint,s.azure_translator_region,s.azure_source_lang,s.azure_target_lang)); print(res.message); raise SystemExit(0 if res.ok else 1)
    elif a.cmd=='providers':
        print('azure: enabled' if s.azure_translate_enabled and s.azure_translator_key else 'azure: not configured')
        print('deepl: enabled' if s.deepl_api_key else 'deepl: not configured')
    elif a.cmd=='export':
        store=ProgressStore(s.progress_dir,Path(a.input)); export_from_progress(Path(a.input),Path(a.output_dir),store,force_export=a.force)
    else:
        res=validate_lines(parse_file(Path(a.original)),parse_file(Path(a.translated))); print('OK' if res.validation_passed else 'FALHOU')

if __name__ == '__main__':
    main()
