# Game Dialog Translator PT-BR

Ferramenta para traduzir diálogos de jogos (`chinês|inglês` e `chave=inglês`) para PT-BR com **DeepL**, preservando estrutura, placeholders e número de linhas.

## O que faz
- Lê `.txt` linha a linha.
- **Nunca envia a parte chinesa** ao provedor.
- Traduz apenas a parte inglesa após o delimitador (`|` ou `=`).
- Salva progresso em SQLite por hash em `.progress/{sha256}.sqlite`.
- Permite retomar, sobrescrever, retentar erros, validar e exportar.
- Gera `arquivo.pt-BR.txt` e `arquivo.translation_report.json`.

## DeepL API (Free vs Pro)
- **Free:** base URL `https://api-free.deepl.com`.
- **Pro:** base URL `https://api.deepl.com`.
- API key: painel da conta DeepL API.

## Configuração
1. Crie conta DeepL API.
2. Copie `.env.example` para `.env`.
3. Preencha:
```env
DEEPL_API_KEY=...
DEEPL_API_URL=https://api-free.deepl.com
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
python cli.py translate --input "arquivo.txt" --output-dir "saida" --batch-size 20 --deepl-plan free --delimiter auto
python cli.py translate --input "arquivo.txt" --output-dir "saida" --batch-size 20 --deepl-plan pro
python cli.py translate --input "arquivo.txt" --output-dir "saida" --resume
python cli.py translate --input "arquivo.txt" --output-dir "saida" --overwrite
python cli.py translate --input "arquivo.txt" --output-dir "saida" --retry-errors
python cli.py resume --input "arquivo.txt" --output-dir "saida"
```

### Validar e exportar
```bash
python cli.py validate --original "arquivo.txt" --translated "arquivo.pt-BR.txt" --delimiter auto
python cli.py export --input "arquivo.txt" --output-dir "saida" --delimiter auto
python cli.py export --input "arquivo.txt" --output-dir "saida" --delimiter auto --force
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


## Microsoft Azure Translator como fallback
- DeepL continua como principal.
- Azure entra quando DeepL falha por quota/rate limit e fallback está habilitado.
- Configure .env conforme .env.example (tier F0 Free, Key e Region do recurso Azure Translator).
- O relatório JSON inclui providers_used, lines_by_provider e characters_by_provider.

## Modo Azure estável com progresso em tempo real

Comando recomendado:

```bash
python cli.py translate --input "arquivos\_9999_GameUI.txt" --output-dir "saida" --resume --provider azure --no-fallback --delimiter auto --batch-size 100 --auto-export
```

- O fluxo agora cria backup automático do SQLite antes de iniciar.
- Em HTTP 429, a CLI lê `Retry-After` quando disponível e aplica retry/backoff automático.
- O throttle dinâmico reduz o batch size após rate limit (mínimo 1) e aumenta gradualmente após estabilidade.
- O progresso é salvo por lote no SQLite (sem esperar o fim da execução).
- Sem `--debug`, erros esperados aparecem com mensagem amigável (sem traceback fatal).
- Com `--debug`, traceback completo é exibido para diagnóstico.
- Com `--auto-export`, a exportação com `--force` roda automaticamente ao final (ou após Ctrl+C).
- Para continuar após interrupção, execute novamente com `--resume`.


### Modo rápido Azure (batch adaptativo agressivo)

```bash
python cli.py translate --input "arquivos\_9999_GameUI.txt" --output-dir "saida" --resume --provider azure --no-fallback --delimiter auto --batch-size 100 --auto-export
```

- `--batch-size 100` é o ponto de partida para linhas por lote.
- O limite por caracteres por lote evita erro `400077 maximum request size exceeded`.
- Em `429`, o lote é reduzido automaticamente e o retry/backoff é aplicado sem perder progresso.
- Em estabilidade contínua, o lote cresce novamente até o teto configurado.
- O progresso é persistido a cada lote bem-sucedido; linhas já traduzidas não são retraduzidas em `--resume`.
- Novas flags opcionais: `--max-chars-per-batch`, `--start-chars-per-batch`, `--delay-between-batches`.
