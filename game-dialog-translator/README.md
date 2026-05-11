# Game Dialog Translator PT-BR (DeepL)

Traduz arquivos no padrão `chinês|inglês` para `chinês|português` usando **DeepL API**, preservando estrutura, separador, linha e placeholders.

## DeepL
- Crie conta DeepL API (Free ou Pro).
- Free: `https://api-free.deepl.com/v2/translate`
- Pro: `https://api.deepl.com/v2/translate`
- Configure chave em `.env`.

## Instalação
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração
Copie `.env.example` para `.env` e ajuste `DEEPL_API_KEY`.

## Streamlit
```bash
streamlit run app.py
```
Permite: testar conexão DeepL, selecionar arquivos, ver progresso/ETA/chars/logs e exportar.

## CLI
```bash
python cli.py test-deepl --deepl-plan free
python cli.py translate --input "arquivo.txt" --output-dir "saida" --batch-size 20 --deepl-plan free
python cli.py translate --input "arquivo.txt" --output-dir "saida" --batch-size 20 --deepl-plan pro
python cli.py resume --input "arquivo.txt" --output-dir "saida"
python cli.py validate --original "arquivo.txt" --translated "arquivo.pt-BR.txt"
```

## Segurança
- Nunca altera o chinês.
- Sempre usa `split("|", 1)`.
- Não altera número de linhas.
- Não sobrescreve original.
- Preserva placeholders.
- Não expõe API key em logs.

## Quota/erros DeepL
- Em quota/rate limit, o lote tenta retry.
- Em quota excedida, registra erro e permite retomar.

## Integração futura com GPT personalizado
Futuramente pode-se expor a lógica por FastAPI + OpenAPI para acoplar a GPT personalizado.
