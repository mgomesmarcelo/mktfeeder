from __future__ import annotations

from datetime import date
import pandas as pd

from src.mktfeeder_greyhounds.config import settings
from src.mktfeeder_greyhounds.logger import get_logger
from src.mktfeeder_greyhounds.utils.dates import iso_to_hhmm
from src.mktfeeder_greyhounds.utils.files import read_csv, write_dataframe
from src.mktfeeder_greyhounds.utils.text import normalize_category, normalize_spaces


def _load_today_timeform() -> pd.DataFrame:
    today_str = date.today().isoformat()
    path = settings.RAW_TIMEFORM_FORECAST_DIR / f"timeform_forecast_{today_str}.csv"
    df = read_csv(path)
    if df.empty:
        logger.warning("Arquivo de timeform_forecast vazio ou inexistente: {}", path)
    return df


def _build_top3(df_raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df_raw.iterrows():
        dog1 = normalize_spaces(str(row.get("TimeformTop1") or "")).strip()
        dog2 = normalize_spaces(str(row.get("TimeformTop2") or "")).strip()
        dog3 = normalize_spaces(str(row.get("TimeformTop3") or "")).strip()
        if not (dog1 and dog2 and dog3):
            logger.warning("Corrida ignorada (top3 incompleto): {} {}", row.get("track"), row.get("hhmm") or row.get("race_time_iso"))
            continue
        hhmm_val = str(row.get("hhmm") or "") or iso_to_hhmm(str(row.get("race_time_iso") or ""))
        rows.append(
            {
                "date": str(row.get("date") or date.today().isoformat()),
                "track": normalize_spaces(str(row.get("track") or "")),
                "hhmm": hhmm_val,
                "category_raw": normalize_spaces(str(row.get("category_raw") or "")),
                "category_norm": normalize_category(str(row.get("category_norm") or "")),
                "dog_1": dog1,
                "dog_2": dog2,
                "dog_3": dog3,
            }
        )
    return pd.DataFrame(rows)


def _build_forecast(df_raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df_raw.iterrows():
        f1 = row.get("Forecast1") or row.get("forecast_1") or ""
        f2 = row.get("Forecast2") or row.get("forecast_2") or ""
        f3 = row.get("Forecast3") or row.get("forecast_3") or ""
        if not f1:
            logger.warning("Corrida ignorada (forecast vazio): {} {}", row.get("track"), row.get("hhmm"))
            continue
        if not (f2 and f3):
            logger.warning("Corrida ignorada (forecast incompleto): {} {}", row.get("track"), row.get("hhmm"))
            continue
        rows.append(
            {
                "date": row.get("date"),
                "track": row.get("track"),
                "hhmm": row.get("hhmm"),
                "category_raw": row.get("category_raw"),
                "category_norm": row.get("category_norm"),
                "forecast_1": f1,
                "forecast_2": f2,
                "forecast_3": f3,
                "forecast_1_odds": row.get("Forecast1Odds") or row.get("forecast_1_odds"),
                "forecast_2_odds": row.get("Forecast2Odds") or row.get("forecast_2_odds"),
                "forecast_3_odds": row.get("Forecast3Odds") or row.get("forecast_3_odds"),
            }
        )
    return pd.DataFrame(rows)


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    logger = get_logger()
    today_str = date.today().isoformat()

    df_raw = _load_today_timeform()
    if df_raw.empty:
        logger.warning("Sem dados de timeform_forecast para gerar outputs.")
        return pd.DataFrame(), pd.DataFrame()

    df_top3 = _build_top3(df_raw)
    df_forecast = _build_forecast(df_raw)

    top3_path = settings.OUTPUT_TOP3_DIR / f"top3_{today_str}.csv"
    forecast_path = settings.OUTPUT_FORECAST_DIR / f"forecast_{today_str}.csv"

    write_dataframe(df_top3, top3_path)
    write_dataframe(df_forecast, forecast_path)

    logger.info("TOP3 salvo em {}", top3_path)
    logger.info("FORECAST salvo em {}", forecast_path)

    return df_top3, df_forecast


if __name__ == "__main__":
    run()

