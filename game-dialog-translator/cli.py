from __future__ import annotations
import argparse
import time
import traceback
from collections import deque
from datetime import datetime, timedelta
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
from src.providers.base import ProviderRateLimitError, ProviderTemporaryError, ProviderPermanentError, ProviderInvalidResponseError, ProviderNotConfiguredError, ProviderQuotaExceededError

def _build_combined_batch(translatable, start_idx: int, max_lines: int, max_chars: int):
    batch = []
    total_chars = 0
    idx = start_idx
    while idx < len(translatable) and len(batch) < max_lines:
        line = translatable[idx]
        protected = protect_placeholders(line.english_part)
        line_chars = len(protected.text)
        if batch and total_chars + line_chars > max_chars:
            break
        batch.append((line, protected))
        total_chars += line_chars
        idx += 1
        if line_chars > max_chars:
            break
    return batch, total_chars

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

def _friendly_provider_error(exc: Exception) -> str:
    if isinstance(exc, ProviderRateLimitError):
        return f"Rate limit do provider: {exc}"
    if isinstance(exc, ProviderTemporaryError):
        return f"Erro temporário de rede/serviço: {exc}"
    if isinstance(exc, ProviderNotConfiguredError):
        return f"Provider não configurado/chave inválida: {exc}"
    if isinstance(exc, ProviderQuotaExceededError):
        return f"Quota excedida: {exc}"
    if isinstance(exc, ProviderInvalidResponseError):
        return f"Resposta inválida do provider: {exc}"
    if isinstance(exc, ProviderPermanentError):
        return f"Erro permanente do provider: {exc}"
    return f"Erro inesperado: {exc}"

def run_translate(args):
    s = Settings(); ensure_dirs(s)
    source = Path(args.input); lines = parse_file(source, delimiter=args.delimiter); store = ProgressStore(s.progress_dir, source)
    existing_db = store.db_path.exists() and store.db_path.stat().st_size > 0
    backup_path = store.backup()
    if backup_path:
        print(f"Backup SQLite criado: {backup_path}")
    if args.overwrite:
        store.reset_progress(); existing_db = False

    if args.resume and existing_db:
        store.apply_existing(lines)
        if len(store.load_progress()) == 0:
            raise RuntimeError(f"--resume solicitado e SQLite existente em {store.db_path}, mas nenhum progresso foi carregado.")
    else:
        store.initialize_progress(lines); store.apply_existing(lines)
    if args.retry_errors:
        store.mark_errors_for_retry(); store.apply_existing(lines)

    provider, enable_fallback, deepl, azure = build_providers(args, s)
    if provider == "azure" and (not s.azure_translate_enabled or not (args.azure_key or s.azure_translator_key) or not (args.azure_endpoint or s.azure_translator_endpoint) or not (args.azure_region or s.azure_translator_region)):
        raise RuntimeError("Nenhum provider disponível. Verifique AZURE_TRANSLATOR_KEY, AZURE_TRANSLATOR_ENDPOINT e AZURE_TRANSLATOR_REGION.")

    translatable = [l for l in lines if l.separator in ("|", "=") and l.status in ({"error"} if args.retry_errors else {"pending", "error"})]
    summary = store.get_summary()
    total_file = summary['total_lines']
    total_batches_est = max(1, (len(translatable) + args.batch_size - 1) // args.batch_size)
    print(f"Arquivo: {source.name}\nProvider: {provider}\nTraduzidas total: {summary['translated_lines']}/{total_file}\nPendentes: {summary['pending_lines']}")

    start = time.time(); rate_limit_events = 0; translated_session = 0; chars_session = 0
    max_lines_limit = max(s.azure_min_lines_per_batch, min(s.azure_max_lines_per_batch, args.batch_size))
    current_lines_limit = max(s.azure_min_lines_per_batch, min(max_lines_limit, args.batch_size))
    start_chars = args.start_chars_per_batch or s.azure_start_chars_per_batch
    max_chars_limit = args.max_chars_per_batch or s.azure_max_chars_per_batch
    current_chars_limit = max(s.azure_min_chars_per_batch, min(start_chars, max_chars_limit))
    delay_between = args.delay_between_batches if args.delay_between_batches is not None else s.azure_delay_between_batches_seconds
    success_streak = 0; i = 0; batch_idx = 0
    recent_events = deque(maxlen=8); recent_speeds = deque(maxlen=10)
    try:
        while i < len(translatable):
            batch_idx += 1
            combined, batch_chars = _build_combined_batch(translatable, i, current_lines_limit, current_chars_limit)
            batch = [line for line, _ in combined]
            items=[]; maps={}
            for l, p in combined:
                maps[l.line_number]=p.mapping; l.protected_english=p.text
                items.append(TranslationItem(line_number=l.line_number,text=p.text))

            retry = 0
            while True:
                try:
                    t0 = time.time()
                    results, meta = translate_with_fallback(items, deepl=deepl, azure=azure, enable_fallback=enable_fallback)
                    elapsed_batch = time.time() - t0
                    break
                except ProviderRateLimitError as e:
                    retry += 1; rate_limit_events += 1; success_streak = 0
                    if s.azure_dynamic_batching:
                        old_lines, old_chars = current_lines_limit, current_chars_limit
                        current_lines_limit = max(s.azure_min_lines_per_batch, int(current_lines_limit * s.azure_batch_shrink_factor))
                        current_chars_limit = max(s.azure_min_chars_per_batch, int(current_chars_limit * s.azure_batch_shrink_factor))
                        print(f"Rate limit detectado. Reduzindo lote: linhas {old_lines}→{current_lines_limit}, chars {old_chars}→{current_chars_limit}.")
                        delay_between = min(s.azure_max_backoff_seconds, max(delay_between * 1.5, s.azure_delay_between_batches_seconds))
                    if retry > s.azure_max_retries:
                        raise
                    wait_s = e.retry_after if getattr(e, "retry_after", None) else min(s.azure_max_backoff_seconds, s.azure_initial_backoff_seconds * (2 ** (retry - 1)))
                    print(f"Rate limit Azure detectado no lote {batch_idx}.\nAguardando {int(wait_s)}s antes de tentar novamente...\nTentativa {retry}/{s.azure_max_retries}")
                    recent_events.append(f"rate_limit lote={batch_idx} retry={retry} wait={wait_s}s")
                    time.sleep(wait_s)
                except ProviderPermanentError as e:
                    msg = str(e)
                    if "400077" in msg or "maximum request size" in msg.lower():
                        success_streak = 0
                        if len(batch) == 1:
                            line = batch[0]
                            line.status = 'error'
                            line.error_message = 'Linha excede tamanho máximo da Azure'
                            store.save_batch([line], batch_number=batch_idx)
                            i += 1
                            print("Tamanho máximo excedido em linha única. Marcando erro individual e continuando.")
                            break
                        old_chars = current_chars_limit
                        current_chars_limit = max(s.azure_min_chars_per_batch, int(current_chars_limit * s.azure_batch_shrink_factor))
                        print(f"Tamanho máximo excedido. Dividindo lote atual em sublotes menores. chars {old_chars}→{current_chars_limit}.")
                        combined, batch_chars = _build_combined_batch(translatable, i, max(s.azure_min_lines_per_batch, len(batch)//2), current_chars_limit)
                        batch = [line for line, _ in combined]
                        items=[]; maps={}
                        for l, p in combined:
                            maps[l.line_number]=p.mapping; l.protected_english=p.text
                            items.append(TranslationItem(line_number=l.line_number,text=p.text))
                        retry += 1
                        if retry > s.azure_max_retries:
                            raise
                        continue
                    raise

            by_ln={x.line_number:x for x in results}
            for l in batch:
                r=by_ln.get(l.line_number)
                if not r or not r.translation: l.status='error'; l.error_message='Falha providers'; continue
                rt=restore_placeholders(r.translation,maps[l.line_number])
                if not placeholders_preserved(rt,maps[l.line_number]): l.status='error'; l.error_message='Placeholder alterado'; continue
                l.portuguese_translation=rt; l.status='translated'; l.characters_count=len(l.english_part); l.provider=r.provider; l.fallback_used=meta['fallback_used']; l.provider_chain_attempted=','.join(meta['provider_chain_attempted']); l.characters_sent=r.characters_sent
                translated_session += 1; chars_session += len(l.english_part)
            store.save_batch(batch,batch_number=batch_idx)
            i += len(batch)
            success_streak += 1
            if s.azure_dynamic_batching and success_streak >= s.azure_grow_after_successful_batches:
                old_lines, old_chars = current_lines_limit, current_chars_limit
                current_lines_limit = min(max_lines_limit, max(s.azure_min_lines_per_batch, int(current_lines_limit * s.azure_batch_growth_factor)))
                current_chars_limit = min(max_chars_limit, max(s.azure_min_chars_per_batch, int(current_chars_limit * s.azure_batch_growth_factor)))
                success_streak = 0
                if old_lines != current_lines_limit or old_chars != current_chars_limit:
                    print(f"Estável por {s.azure_grow_after_successful_batches} lotes. Aumentando lote: linhas {old_lines}→{current_lines_limit}, chars {old_chars}→{current_chars_limit}.")
            speed_avg = translated_session / max((time.time() - start) / 60, 1e-6)
            recent_speeds.append((len(batch) / max(elapsed_batch / 60, 1e-6)))
            speed_10 = sum(recent_speeds) / len(recent_speeds)
            fresh_summary = store.get_summary(); pending = fresh_summary['pending_lines']
            eta_minutes = pending / speed_avg if speed_avg > 0 else 0
            eta_time = (datetime.now() + timedelta(minutes=eta_minutes)).strftime('%H:%M:%S') if speed_avg > 0 else '--:--:--'
            print(f"Arquivo: {source.name}\nProvider: {provider}\nLote: {batch_idx}/{total_batches_est}\nTraduzidas nesta execução: {translated_session}\nTraduzidas total: {fresh_summary['translated_lines']}/{total_file}\nPendentes: {pending}\nErros: {fresh_summary['error_lines']}\nProgresso total: {(fresh_summary['translated_lines']/max(total_file,1))*100:.2f}%\nProgresso desta sessão: {(translated_session/max(total_file,1))*100:.2f}%\nVelocidade média: {speed_avg:.1f} linhas/min\nVelocidade últimos 10 lotes: {speed_10:.1f} linhas/min\nCaracteres traduzidos nesta sessão: {chars_session}\nTempo decorrido: {str(timedelta(seconds=int(time.time()-start)))}\nETA: {eta_time}\nConclusão prevista: {(datetime.now()+timedelta(minutes=eta_minutes)).strftime('%d/%m/%Y %H:%M:%S') if speed_avg > 0 else '--'}\nÚltimo lote: sucesso em {elapsed_batch:.1f}s\nRate limit: {rate_limit_events} eventos")
            print(f"lote={batch_idx}/{total_batches_est} provider={provider} linhas={len(batch)} chars={batch_chars} limit_linhas={current_lines_limit} limit_chars={current_chars_limit} total_translated={fresh_summary['translated_lines']} pending={pending} speed={speed_avg:.1f}/min eta={eta_time} status=ok")
            recent_events.append(f"lote={batch_idx} ok {elapsed_batch:.1f}s")
            time.sleep(delay_between)
    except KeyboardInterrupt:
        fresh_summary = store.get_summary()
        print("Tradução interrompida pelo usuário.\nProgresso salvo.")
        print(f"Traduzidas nesta sessão: {translated_session}\nTotal traduzidas: {fresh_summary['translated_lines']}\nPendentes: {fresh_summary['pending_lines']}")
        print("Para continuar:\npython cli.py translate --input ... --resume --provider azure --no-fallback")
        if args.auto_export:
            export_from_progress(source, Path(args.output_dir), store, force_export=True)
        return

def main():
    load_dotenv(); p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    s = Settings()
    t=sub.add_parser('translate'); t.add_argument('--input',required=True); t.add_argument('--output-dir',required=True); t.add_argument('--batch-size',type=int,default=20); t.add_argument('--max-chars-per-batch', type=int, default=None); t.add_argument('--start-chars-per-batch', type=int, default=None); t.add_argument('--delay-between-batches', type=float, default=None); t.add_argument('--deepl-plan',choices=['free','pro'],default='free'); t.add_argument('--deepl-api-url'); t.add_argument('--source-lang',default='EN'); t.add_argument('--target-lang',default='PT-BR'); t.add_argument('--formality',default='prefer_more'); t.add_argument('--resume',action='store_true'); t.add_argument('--overwrite',action='store_true'); t.add_argument('--retry-errors',action='store_true'); t.add_argument('--provider',choices=['deepl','azure'],default=s.translation_provider); t.add_argument('--no-fallback',action='store_true'); t.add_argument('--azure-key'); t.add_argument('--azure-endpoint'); t.add_argument('--azure-region'); t.add_argument('--auto-export', action='store_true'); t.add_argument('--debug', action='store_true'); t.add_argument('--delimiter', choices=['auto','pipe','equals'], default='auto')
    sub.add_parser('validate').add_argument('--original',required=False)
    v=sub.choices['validate']; v.add_argument('--translated',required=True); v.add_argument('--delimiter', choices=['auto','pipe','equals'], default='auto')
    e=sub.add_parser('export'); e.add_argument('--input',required=True); e.add_argument('--output-dir',required=True); e.add_argument('--force',action='store_true'); e.add_argument('--delimiter', choices=['auto','pipe','equals'], default='auto')
    td=sub.add_parser('test-deepl'); td.add_argument('--deepl-plan',choices=['free','pro'],default='free'); td.add_argument('--deepl-api-url')
    sub.add_parser('test-azure'); sub.add_parser('providers')
    a=p.parse_args(); s=Settings(); ensure_dirs(s)
    try:
        if a.cmd=='translate':
            run_translate(a); store=ProgressStore(s.progress_dir,Path(a.input));
            if a.auto_export: export_from_progress(Path(a.input),Path(a.output_dir),store,force_export=True,metadata={"provider":a.provider,"batch_size":a.batch_size}, delimiter=a.delimiter)
        elif a.cmd=='test-deepl':
            ok,msg=test_deepl_connection(DeepLTranslationSettings(api_key=s.deepl_api_key,api_url=resolve_url(a.deepl_plan,a.deepl_api_url))); print(msg); raise SystemExit(0 if ok else 1)
        elif a.cmd=='test-azure':
            res=test_azure_connection(AzureProvider(s.azure_translator_key,s.azure_translator_endpoint,s.azure_translator_region,s.azure_source_lang,s.azure_target_lang)); print(res.message); raise SystemExit(0 if res.ok else 1)
        elif a.cmd=='providers':
            print('azure: enabled' if s.azure_translate_enabled and s.azure_translator_key else 'azure: not configured')
            print('deepl: enabled' if s.deepl_api_key else 'deepl: not configured')
        elif a.cmd=='export':
            store=ProgressStore(s.progress_dir,Path(a.input)); export_from_progress(Path(a.input),Path(a.output_dir),store,force_export=a.force, delimiter=a.delimiter)
        else:
            res=validate_lines(parse_file(Path(a.original), delimiter=a.delimiter),parse_file(Path(a.translated), delimiter=a.delimiter)); print('OK' if res.validation_passed else 'FALHOU')
    except Exception as exc:
        if getattr(a, 'debug', False):
            traceback.print_exc()
        else:
            print(_friendly_provider_error(exc))
        raise SystemExit(1)

if __name__ == '__main__':
    main()
