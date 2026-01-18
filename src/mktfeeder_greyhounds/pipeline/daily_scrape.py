from __future__ import annotations

from datetime import date
import pandas as pd

from src.mktfeeder_greyhounds.config import settings
from src.mktfeeder_greyhounds.logger import get_logger
from src.mktfeeder_greyhounds.scrapers.timeform import build_timeform_forecast_df, scrape_timeform_forecast
from src.mktfeeder_greyhounds.utils.files import write_dataframe


def run() -> dict:
    logger = get_logger()
    today_str = date.today().isoformat()

    logger.info("Coletando Timeform (forecast + verdict)...")
    updates, scrape_stats = scrape_timeform_forecast()
    df_forecast = build_timeform_forecast_df(updates)
    forecast_raw_path = settings.RAW_TIMEFORM_FORECAST_DIR / f"timeform_forecast_{today_str}.csv"
    write_dataframe(df_forecast, forecast_raw_path)
    logger.info("timeform_forecast salvo em {}", forecast_raw_path)
    return scrape_stats


if __name__ == "__main__":
    run()

