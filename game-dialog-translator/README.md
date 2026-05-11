# Game Dialog Translator PT-BR

Ferramenta para traduzir diálogos de jogos (`chinês|inglês`) para PT-BR com **DeepL**, preservando estrutura, placeholders e número de linhas.

## O que faz
- Lê `.txt` linha a linha.
- **Nunca envia a parte chinesa** ao provedor.
- Traduz apenas a parte inglesa após `|`.
- Salva progresso em SQLite por hash em `.progress/{sha256}.sqlite`.
- Permite retomar, sobrescrever, retentar erros, validar e exportar.
- Gera `arquivo.pt-BR.txt` e `arquivo.translation_report.json`.

## DeepL API (Free vs Pro)
- **Free:** endpoint `https://api-free.deepl.com/v2/translate`.
- **Pro:** endpoint `https://api.deepl.com/v2/translate`.
- API key: painel da conta DeepL API.

## Configuração
1. Crie conta DeepL API.
2. Copie `.env.example` para `.env`.
3. Preencha:
```env
DEEPL_API_KEY=...
DEEPL_API_URL=https://api-free.deepl.com/v2/translate
DEEPL_SOURCE_LANG=EN
DEEPL_TARGET_LANG=PT-BR
DEFAULT_BATCH_SIZE=20
DEFAULT_FORMALITY=prefer_more
```

## Instalação
```bash
pip install -r requirements.txt
```

## Testes
```bash
pytest -q
```

## Streamlit
```bash
streamlit run app.py
```
Recursos: upload múltiplo, plano Free/Pro/Custom, teste de conexão, tradução com progresso em tempo real, validação, exportação e download de arquivo/relatório.

## CLI
### Testar conexão
```bash
python cli.py test-deepl
```

### Traduzir
```bash
python cli.py translate --input "arquivo.txt" --output-dir "saida" --batch-size 20 --deepl-plan free
python cli.py translate --input "arquivo.txt" --output-dir "saida" --batch-size 20 --deepl-plan pro
python cli.py translate --input "arquivo.txt" --output-dir "saida" --resume
python cli.py translate --input "arquivo.txt" --output-dir "saida" --overwrite
python cli.py translate --input "arquivo.txt" --output-dir "saida" --retry-errors
python cli.py resume --input "arquivo.txt" --output-dir "saida"
```

### Validar e exportar
```bash
python cli.py validate --original "arquivo.txt" --translated "arquivo.pt-BR.txt"
python cli.py export --input "arquivo.txt" --output-dir "saida"
python cli.py export --input "arquivo.txt" --output-dir "saida" --force
```

## Logs em tempo real
- Arquivos em `logs/translation_YYYYMMDD_HHMMSS.log`.
- Streamlit mostra últimos logs e últimas linhas traduzidas.

## ETA e métricas
- ETA = tempo estimado para linhas pendentes.
- Previsão de conclusão = hora atual + ETA.
- Relatório traz linhas/min e caracteres/min.

## Relatório JSON
Campos: origem/destino, hash, totais, pendências/erros, validação, tempos, velocidades, chars, endpoint, idiomas, batch e `force_export`.

## Troubleshooting
- **quota exceeded:** aguarde reset de cota ou migre Free→Pro.
- **dependência ausente:** rode `pip install -r requirements.txt`.

## Segurança
- Não envia chinês para DeepL.
- Não altera chinês.
- Não altera número de linhas.
- Preserva placeholders e tokens.
- Não sobrescreve original.
- Não salva/imprime API key em logs.

## Integração futura com GPT personalizado
Planejado: pós-edição opcional de estilo PT-BR após DeepL, mantendo as mesmas regras de segurança/validação estrutural.
