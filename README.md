# MktFeeder Greyhounds

Pipeline em Python para gerar diariamente os arquivos consumidos pelo MarketFeeder via **reimport file every X seconds**.  
O código não executa estratégia ao vivo; apenas prepara a lista diária (TOP3) para ser usada pelo MarketFeeder.

## Requisitos
- Python 3.10+
- Google Chrome instalado (usado pelo Selenium)

Instale as dependências:
```
pip install -r requirements.txt
```

## Como rodar
Executa todo o fluxo (scrape Timeform + outputs + arquivo do MarketFeeder):
```
python scripts\run_daily.py
```

Gerar apenas TOP3/FORECAST (a partir do raw timeform_forecast do dia):
```
python scripts\build_outputs.py
```

Gerar apenas os arquivos do MarketFeeder (a partir do FORECAST do dia):
```
python scripts\build_marketfeeder_file.py
```

## Estrutura de dados gerados
- `data/raw/timeform_forecast/timeform_forecast_YYYY-MM-DD.csv` (Betting Forecast + Analyst Verdict)
- `data/output/top3/top3_YYYY-MM-DD.csv` (Analyst Verdict TOP3)
- `data/output/forecast/forecast_YYYY-MM-DD.csv` (Betting Forecast TOP3 + odds)
- `data/output/marketfeeder/import_selections.txt` (arquivo fixo sobrescrito diariamente)
- `data/output/marketfeeder/history/import_selections_YYYY-MM-DD.txt`
- `data/output/marketfeeder/history/import_selections_YYYY-MM-DD_audit.csv`

## Formato do arquivo fixo (MarketFeeder)
Uma seleção por linha, com TABs reais entre colunas. As 3 linhas por corrida vêm do Betting Forecast (top3):
```
[HH:MM Track]Dog Name\t"STRATEGY_TAG"\tSTAKE
```
Exemplo:
```
[14:15 Hove]Dog Name 1\t"BACK"\t5.0
```
- `strategy_tag` fica em `imported_1` e `stake` em `imported_2` dentro do MarketFeeder.
- Sempre 3 linhas por corrida elegível (TOP3).
- Para evitar leitura no meio da escrita, o código grava primeiro em `import_selections.tmp` e depois substitui/renomeia para `import_selections.txt`.

## Lógica de categorias e stakes
Configuração em `src/mktfeeder_greyhounds/config.py`:
- `BACK_CATEGORY_PREFIXES = ["A", "OR"]`
- `LAY_CATEGORY_PREFIXES  = ["D", "HP"]`
- `STAKE_BACK = 1.0`
- `STAKE_LAY  = 1.0`
- Se `category_norm` começar com qualquer prefixo de BACK → `"BACK"` / stake `STAKE_BACK`.
- Se começar com prefixo de LAY → `"LAY"` / stake `STAKE_LAY`.
- Caso contrário a corrida é ignorada.
- `KEEP_ALL_ACTIVE = False` (se `True`, adiciona a linha `#all_active#` ao final do TXT).

## Configurar o MarketFeeder
1. Aponte o reimport para `data/output/marketfeeder/import_selections.txt`.
2. Habilite reimport periódico.
3. Use `imported_1` (strategy_tag) e `imported_2` (stake) nas triggers/regras.

## Observações
- Diretórios são criados automaticamente.
- Encoding CSV: `utf-8-sig`.
- Logs com `loguru` respeitando `LOG_LEVEL` no config.
- O scraping usa Selenium + Chrome; mantenha o Chrome atualizado.

## Logs
- Logs são exibidos no terminal (stdout/stderr).
- Logs também são gravados em `data/logs/mktfeeder.log` com rotação diária, retenção de 7 dias e compressão zip.
- Diretório `data/logs/` é criado automaticamente.

## Categorias e Prefixos (BACK/LAY)
- A decisão BACK/LAY é por prefixo (`startswith`) em `category_norm`.
- Se `BACK_CATEGORY_PREFIXES` contém "I", cobre `IV`, `IT` e qualquer categoria que comece com `I`.
- Se `LAY_CATEGORY_PREFIXES` contém "HP", cobre apenas `HP` (não inclui `HC`). Para incluir `HC`, adicione "HC". Para cobrir `HP` e `HC`, use prefixo "H".
- Exemplos:
  - `BACK_CATEGORY_PREFIXES = ["A","OR","I"]` → cobre `A1..A10`, `OR/OR2/OR3`, `IV/IT`.
  - `LAY_CATEGORY_PREFIXES = ["D","HP"]` → cobre `D1..D6` e `HP` apenas.
- Recomendações: use prefixos curtos para incluir subcategorias automaticamente e prefixos específicos para controle fino.
