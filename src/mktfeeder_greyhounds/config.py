from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def project_root() -> Path:
    """Retorna o diretório raiz do projeto (pasta MktFeeder)."""
    return Path(__file__).resolve().parents[2]


def ensure_dir(*parts: str | Path) -> Path:
    path = project_root().joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class Settings:
    # Paths
    DATA_DIR: Path = ensure_dir("data")
    RAW_TIMEFORM_FORECAST_DIR: Path = ensure_dir("data", "raw", "timeform_forecast")
    OUTPUT_TOP3_DIR: Path = ensure_dir("data", "output", "top3")
    OUTPUT_FORECAST_DIR: Path = ensure_dir("data", "output", "forecast")
    MARKETFEEDER_DIR: Path = ensure_dir("data", "output", "marketfeeder")
    MARKETFEEDER_HISTORY_DIR: Path = ensure_dir("data", "output", "marketfeeder", "history")

    # Scraping
    BETFAIR_BASE_URL: str = "https://www.betfair.com/exchange/plus/"
    BETFAIR_GREYHOUND_RACING_URL: str = "https://www.betfair.com/exchange/plus/en/greyhound-racing-betting-4339"
    TIMEFORM_BASE_URL: str = "https://www.timeform.com/greyhound-racing"
    SELENIUM_HEADLESS: bool = False
    SELENIUM_PAGELOAD_TIMEOUT_SEC: int = 45
    SELENIUM_IMPLICIT_WAIT_SEC: int = 5
    SELENIUM_EXPLICIT_WAIT_SEC: int = 15
    TIMEFORM_MIN_DELAY_SEC: float = 0.5
    TIMEFORM_MAX_DELAY_SEC: float = 1.0

    # Export
    CSV_ENCODING: str = "utf-8-sig"
    LOG_LEVEL: str = "INFO"

    # Estratégia configurável
    STAKE_BACK: float = 1.0
    STAKE_LAY: float = 1.0
    BACK_CATEGORY_PREFIXES: tuple[str, ...] = ("A", "OR")
    LAY_CATEGORY_PREFIXES: tuple[str, ...] = ("D", "HP")
    KEEP_ALL_ACTIVE: bool = False

    # Filtro de corridas passadas
    SKIP_PAST_RACES: bool = True
    PAST_RACE_GRACE_MINUTES: int = 2


settings = Settings()

__all__ = ["settings", "Settings", "ensure_dir", "project_root"]

