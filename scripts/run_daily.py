from __future__ import annotations

import sys
from pathlib import Path

# Garante que o projeto esteja no PYTHONPATH mesmo quando o script é iniciado via atalho.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.mktfeeder_greyhounds.pipeline.daily_scrape import run as run_scrape
from src.mktfeeder_greyhounds.pipeline.build_outputs import run as run_outputs
from src.mktfeeder_greyhounds.pipeline.build_marketfeeder_import import run as run_marketfeeder
from src.mktfeeder_greyhounds.logger import get_logger


def main() -> None:
    logger = get_logger()
    scrape_stats = run_scrape()
    df_top3, df_forecast = run_outputs()
    (
        fixed_path,
        hist_txt,
        audit_csv,
        total_lines,
        skipped_forecast_incomplete,
        races_exported,
        counts_by_strategy,
        races_by_strategy,
        exported_category_counts,
        ignored_by_category_total,
        ignored_category_counts,
    ) = run_marketfeeder()

    logger.info(
        "Arquivos gerados: TOP3={} | FORECAST={} | MF_Fixo={} | MF_Hist={} | Audit={}",
        df_top3.shape if hasattr(df_top3, 'shape') else None,
        df_forecast.shape if hasattr(df_forecast, 'shape') else None,
        fixed_path,
        hist_txt,
        audit_csv,
    )
    skipped_past = scrape_stats.get("skipped_past") if isinstance(scrape_stats, dict) else None
    processed = scrape_stats.get("processed") if isinstance(scrape_stats, dict) else None
    counts_str = counts_by_strategy if isinstance(counts_by_strategy, dict) else {}
    races_str = races_by_strategy if isinstance(races_by_strategy, dict) else {}
    cat_exported_str = exported_category_counts if isinstance(exported_category_counts, dict) else {}
    ignored_cat_str = ignored_category_counts if isinstance(ignored_category_counts, dict) else {}

    logger.info("Total de selecoes exportadas: {}", total_lines)
    logger.info(
        "Resumo: corridas futuras exportadas={} | corridas ignoradas (passadas)={} | corridas ignoradas (forecast incompleto)={} | selecoes={}",
        races_exported,
        skipped_past,
        skipped_forecast_incomplete,
        total_lines,
    )
    logger.info("Selecoes por strategy_tag: {}", counts_str)
    logger.info(
        "Corridas por strategy_tag: BACK={} | LAY={}",
        races_str.get("BACK", 0),
        races_str.get("LAY", 0),
    )
    logger.info(
        "Selecoes por strategy_tag: BACK={} | LAY={}",
        counts_str.get("BACK", 0),
        counts_str.get("LAY", 0),
    )
    logger.info("Categorias exportadas (forecast elegível): {}", cat_exported_str)
    logger.info(
        "Corridas ignoradas por categoria não elegível: {} | categorias: {}",
        ignored_by_category_total,
        ignored_cat_str,
    )
    if processed is not None:
        logger.info("Corridas processadas pelo scrape: {}", processed)


if __name__ == "__main__":
    main()

