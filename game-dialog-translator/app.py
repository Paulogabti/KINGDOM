from __future__ import annotations
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from src.config import Settings, ensure_dirs, DEEPL_FREE_URL, DEEPL_PRO_URL
from src.parser import parse_file
from src.placeholders import protect_placeholders, restore_placeholders, placeholders_preserved
from src.translator import DeepLTranslationSettings, translate_batch_with_deepl, test_deepl_connection
from src.exporter import export_translated
from src.utils import now_ts, calc_lines_per_minute, calc_eta_seconds, calc_percent, fmt_duration, eta_finish_time

load_dotenv(); s=Settings(); ensure_dirs(s)
st.title("Game Dialog Translator PT-BR (DeepL)")
files = st.file_uploader("Selecione .txt", type=["txt"], accept_multiple_files=True)
out_dir = Path(st.text_input("Pasta de saída", "output"))
api_key = st.text_input("DeepL API Key (opcional, usa .env se vazio)", type="password")
plan = st.selectbox("Plano DeepL", ["free", "pro", "custom"])
custom_url = st.text_input("URL customizada") if plan=="custom" else ""
endpoint = custom_url or (DEEPL_PRO_URL if plan=="pro" else DEEPL_FREE_URL)
st.caption(f"Endpoint: {endpoint}")
source_lang = st.text_input("Source", s.deepl_source_lang)
target_lang = st.text_input("Target", s.deepl_target_lang)
formality = st.text_input("Formality", s.default_formality)
batch = st.selectbox("Lote", [10,20,30,50,"custom"])
if batch=="custom": batch=int(st.number_input("Valor custom", min_value=1, value=s.default_batch_size))
if st.button("Testar conexão com DeepL"):
    ok,msg=test_deepl_connection(DeepLTranslationSettings(api_key=api_key or s.deepl_api_key, api_url=endpoint, source_lang=source_lang, target_lang=target_lang, formality=formality))
    (st.success if ok else st.error)(msg)
start_btn = st.button("Iniciar tradução")
progress=st.progress(0.0); stats=st.empty(); logs=st.empty(); table=st.empty()
if start_btn and files:
    cfg=DeepLTranslationSettings(api_key=api_key or s.deepl_api_key, api_url=endpoint, source_lang=source_lang, target_lang=target_lang, formality=formality)
    if not cfg.api_key: st.error("DEEPL_API_KEY ausente")
    for f in files:
        p=Path('/tmp')/f.name; p.write_bytes(f.getbuffer()); lines=parse_file(p); trans=[x for x in lines if x.separator=='|']
        done=0; chars=0; start=now_ts(); ev=[]
        for i in range(0,len(trans),int(batch)):
            b=trans[i:i+int(batch)]; items=[]; maps={}
            for l in b:
                pp=protect_placeholders(l.english_part); maps[l.line_number]=pp.mapping; items.append({"line_number":l.line_number,"text":pp.text})
            r=translate_batch_with_deepl(items,cfg); rb={x['line_number']:x['translation'] for x in r}
            for l in b:
                txt=rb.get(l.line_number,"")
                if not txt: l.status='error'; l.error_message='Falha DeepL'; continue
                restored=restore_placeholders(txt,maps[l.line_number])
                if not placeholders_preserved(restored,maps[l.line_number]): l.status='error'; l.error_message='Placeholder alterado'; continue
                l.portuguese_translation=restored; l.status='translated'; done+=1; chars += len(l.english_part)
            elapsed=now_ts()-start; spd=calc_lines_per_minute(done,elapsed); eta=calc_eta_seconds(len(trans)-done,spd)
            ev.append(f"arquivo={f.name} lote={(i//int(batch))+1} traduzidas={done} pendentes={len(trans)-done} erros={sum(1 for x in lines if x.status=='error')} chars={chars}")
            ev=ev[-50:]; logs.code('\n'.join(ev)); progress.progress(done/max(1,len(trans)))
            stats.write({"arquivo":f.name,"linhas_totais":len(lines),"traduziveis":len(trans),"traduzidas":done,"pendentes":len(trans)-done,"ignoradas":sum(1 for x in lines if x.status=='skipped_no_separator'),"erros":sum(1 for x in lines if x.status=='error'),"progresso":f"{calc_percent(done,len(trans)):.2f}%","velocidade":f"{spd:.1f} linhas/min","chars":chars,"eta":fmt_duration(eta),"fim_previsto":eta_finish_time(eta)})
            table.dataframe([{"line":x.line_number,"chinese":x.chinese_part,"english":x.english_part,"pt":x.portuguese_translation,"status":x.status,"erro":x.error_message} for x in lines if x.status in {'translated','error'}][-20:])
        out,_ = export_translated(p,out_dir,lines); st.success(f"Exportado: {out}")
