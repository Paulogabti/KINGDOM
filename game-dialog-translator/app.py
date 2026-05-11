from __future__ import annotations
from pathlib import Path
import tempfile
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.config import Settings, ensure_dirs, DEEPL_FREE_URL, DEEPL_PRO_URL
from src.exporter import export_from_progress
from src.parser import parse_file
from src.placeholders import protect_placeholders, restore_placeholders, placeholders_preserved
from src.progress import ProgressStore
from src.translator import DeepLTranslationSettings, translate_batch_with_deepl, test_deepl_connection
from src.utils import now_ts, calc_lines_per_minute, calc_eta_seconds, calc_percent, fmt_duration, eta_finish_time

load_dotenv(); s = Settings(); ensure_dirs(s)
st.title("Game Dialog Translator PT-BR")
files = st.file_uploader("Upload .txt", type=["txt"], accept_multiple_files=True)
out_dir = Path(st.text_input("Pasta de saída", "output"))
api_key = st.text_input("DEEPL_API_KEY", value=s.deepl_api_key, type="password")
plan = st.selectbox("Plano", ["free", "pro", "custom"])
custom = st.text_input("Endpoint custom") if plan == "custom" else ""
endpoint = custom or (DEEPL_PRO_URL if plan == "pro" else DEEPL_FREE_URL)
st.info(f"Endpoint efetivo: {endpoint}")
source_lang = st.text_input("source_lang", "EN")
target_lang = st.text_input("target_lang", "PT-BR")
formality = st.text_input("formality", "prefer_more")
batch = st.number_input("batch_size", min_value=1, value=20)
mode = st.radio("Modo", ["Continuar de onde parou", "Recomeçar", "Retentar apenas erros", "Sobrescrever tudo"])

if st.button("Testar conexão DeepL"):
    ok, msg = test_deepl_connection(DeepLTranslationSettings(api_key=api_key, api_url=endpoint, source_lang=source_lang, target_lang=target_lang, formality=formality))
    (st.success if ok else st.error)(msg)

progress = st.progress(0.0); stats = st.empty(); logs_ph = st.empty(); table_ph = st.empty()

if st.button("Iniciar tradução") and files:
    for up in files:
        temp = Path(tempfile.gettempdir()) / up.name
        temp.write_bytes(up.getbuffer())
        lines = parse_file(temp)
        store = ProgressStore(s.progress_dir, temp)
        if mode in {"Recomeçar", "Sobrescrever tudo"}: store.reset_progress()
        store.initialize_progress(lines); store.apply_existing(lines)
        if mode == "Retentar apenas erros": store.mark_errors_for_retry(); store.apply_existing(lines)
        trans = [x for x in lines if x.separator == "|" and x.status in {"pending", "error"}]
        cfg = DeepLTranslationSettings(api_key=api_key, api_url=endpoint, source_lang=source_lang, target_lang=target_lang, formality=formality)
        start = now_ts(); done = 0; chars = 0; recent_logs = []
        for i in range(0, len(trans), int(batch)):
            b = trans[i:i + int(batch)]; items = []; maps = {}
            for l in b:
                pp = protect_placeholders(l.english_part); maps[l.line_number] = pp.mapping
                items.append({"line_number": l.line_number, "text": pp.text})
            resp = translate_batch_with_deepl(items, cfg)
            by_ln = {x["line_number"]: x["translation"] for x in resp}
            for l in b:
                r = by_ln.get(l.line_number, "")
                if not r: l.status = "error"; l.error_message = "Falha DeepL"; continue
                rt = restore_placeholders(r, maps[l.line_number])
                if not placeholders_preserved(rt, maps[l.line_number]): l.status = "error"; l.error_message = "Placeholder alterado"; continue
                l.status = "translated"; l.portuguese_translation = rt; l.characters_count = len(l.english_part); done += 1; chars += len(l.english_part)
            store.save_batch(b, batch_number=(i // int(batch)) + 1)
            summ = store.get_summary()
            elapsed = now_ts() - start; lpm = calc_lines_per_minute(done, elapsed); cpm = calc_lines_per_minute(chars, elapsed)
            eta = calc_eta_seconds(len(trans) - done, lpm)
            progress.progress(min(1.0, done / max(1, len(trans))))
            stats.json({"arquivo_atual": up.name, "hash": store.file_hash, "plano": plan, "endpoint": endpoint, **summ, "percentual": calc_percent(done, max(1,len(trans))), "linhas_por_min": lpm, "chars_por_min": cpm, "tempo_decorrido": fmt_duration(elapsed), "eta": fmt_duration(eta), "previsao_conclusao": eta_finish_time(eta)})
            recent_logs.append(f"lote={(i//int(batch))+1} traduzidas={done} erros={summ['error_lines']} pendentes={summ['pending_lines']}")
            logs_ph.code("\n".join(recent_logs[-50:]))
            sample = [{"line_number": x.line_number, "chinese_part": x.chinese_part, "english_original": x.english_part, "portuguese_translation": x.portuguese_translation, "status": x.status, "error_message": x.error_message} for x in lines if x.status in {"translated", "error"}][-20:]
            table_ph.dataframe(pd.DataFrame(sample), use_container_width=True)
        st.success(f"Tradução concluída: {up.name}")

orig = st.text_input("Arquivo original para validar/exportar")
if st.button("Validar arquivo traduzido") and orig:
    p = Path(orig); store = ProgressStore(s.progress_dir, p)
    _, report, validation = export_from_progress(p, out_dir, store, force_export=False)
    st.json(validation.to_dict()); st.info(f"Relatório: {report}")
if st.button("Exportar arquivo") and orig:
    p = Path(orig); store = ProgressStore(s.progress_dir, p)
    out, report, validation = export_from_progress(p, out_dir, store, force_export=False)
    st.info(f"Arquivo: {out} | Relatório: {report}")
    if out and out.exists():
        st.download_button("Baixar arquivo traduzido", out.read_bytes(), file_name=out.name)
    if report.exists():
        st.download_button("Baixar relatório JSON", report.read_bytes(), file_name=report.name)
