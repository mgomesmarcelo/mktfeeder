# MktFeeder Greyhounds

Pipeline em Python para gerar diariamente arquivos consumidos pelo MarketFeeder via reimport automático (arquivo fixo). Não executa estratégia ao vivo; apenas prepara a lista diária.

## Requisitos
- Windows
- Python 3.10+
- Google Chrome instalado
- Dependências: `pip install -r requirements.txt`

## Instalação
```
pip install -r requirements.txt
```

## Como rodar (sempre como módulo)
- Fluxo completo (scrape Timeform + outputs + arquivo do MarketFeeder):
```
python -m scripts.run_daily
```
- Apenas gerar TOP3/FORECAST (a partir do raw timeform_forecast do dia):
```
python -m scripts.build_outputs
```
- Apenas gerar arquivos do MarketFeeder (a partir do FORECAST do dia):
```
python -m scripts.build_marketfeeder_file
```

## O que o projeto gera
- Raw Timeform: `data/raw/timeform_forecast/timeform_forecast_YYYY-MM-DD.csv` (Betting Forecast + Analyst Verdict)
- TOP3: `data/output/top3/top3_YYYY-MM-DD.csv` (Analyst Verdict TOP3)
- FORECAST: `data/output/forecast/forecast_YYYY-MM-DD.csv` (Betting Forecast TOP3 + odds)
- MarketFeeder (fixo): `data/output/marketfeeder/import_selections.txt` (sobrescrito diariamente, escrito em `.tmp` e depois replace)
- Histórico: `data/output/marketfeeder/history/import_selections_YYYY-MM-DD.txt`
- Auditoria: `data/output/marketfeeder/history/import_selections_YYYY-MM-DD_audit.csv`

## Categorias e Prefixos (BACK/LAY)
- Decisão por `category_norm.startswith(prefix)`.
- Prefixos curtos incluem subcategorias.
- Exemplos:
  - Se `BACK_CATEGORY_PREFIXES` contém "I", inclui `IV` e `IT`.
  - Se `LAY_CATEGORY_PREFIXES` contém "HP", inclui apenas `HP` (não `HC`).
  - Para incluir `HC`, adicione "HC".
  - Para incluir `HP` e `HC`, use prefixo "H".
- Recomendações: use prefixos curtos para incluir subcategorias automaticamente e prefixos específicos para controle fino.

## Configuração (config.py)
- `STAKE_BACK` / `STAKE_LAY`: stake fixa.
- `BACK_CATEGORY_PREFIXES` / `LAY_CATEGORY_PREFIXES`: prefixos de categoria.
- `SKIP_PAST_RACES` + `PAST_RACE_GRACE_MINUTES`: filtro de corridas já iniciadas.
- Diretórios de saída: `data/raw/`, `data/output/`, `data/logs/` (criados automaticamente).

## Logs
- Logs no console.
- Logs em `data/logs/mktfeeder.log` com rotação diária, retenção 7 dias, compressão zip.
- Diretório `data/logs/` é criado automaticamente.

## Rodando 24/7 (recomendado)
- Manual (PowerShell) na raiz do projeto:
```
python -m scripts.run_daily
```
- Agendado (Windows Task Scheduler): criar tarefa chamando `python -m scripts.run_daily` e definir “Start in” como a pasta raiz do projeto.
