from __future__ import annotations

import random
import re
import time
from datetime import date, datetime, time as dt_time, timedelta
from typing import Dict, Iterable, List, Tuple

import pandas as pd
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib.parse import urljoin

from src.mktfeeder_greyhounds.config import settings
from src.mktfeeder_greyhounds.utils.dates import hhmm_to_today_iso
from src.mktfeeder_greyhounds.utils.selenium_driver import build_chrome_driver
from src.mktfeeder_greyhounds.utils.text import clean_dog_name, normalize_category, normalize_track_name

_TIMEFORM_HOME = settings.TIMEFORM_BASE_URL
_TIMEFORM_BASE = "https://www.timeform.com/greyhound-racing"
GRADE_RE = re.compile(r"Grade:\s*\(([A-Z]{1,3}\d{0,2})\)", re.IGNORECASE)


def _sleep_jitter(label: str = "") -> None:
    low = max(0.0, settings.TIMEFORM_MIN_DELAY_SEC)
    high = max(low, settings.TIMEFORM_MAX_DELAY_SEC)
    delay = random.uniform(low, high)
    logger.debug("Delay{}: {:.2f}s", f" {label}" if label else "", delay)
    time.sleep(delay)


def _accept_cookies(driver) -> None:
    try:
        wait = WebDriverWait(driver, settings.SELENIUM_EXPLICIT_WAIT_SEC)
        banner = None
        try:
            banner = wait.until(EC.presence_of_element_located((By.ID, "onetrust-banner-sdk")))
        except Exception:
            banner = None

        if banner and banner.is_displayed():
            try:
                btn = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
                btn.click()
            except Exception:
                try:
                    driver.execute_script("document.getElementById('onetrust-accept-btn-handler')?.click();")
                except Exception:
                    logger.debug("Falha ao clicar no botao de cookies do Timeform.")

            try:
                WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.ID, "onetrust-banner-sdk")))
            except Exception:
                logger.debug("Banner de cookies ainda visivel apos clique.")
            _sleep_jitter("cookies")
        else:
            logger.debug("Banner de cookies (Timeform) nao presente.")
    except Exception:
        logger.debug("Botao/banner de cookies (Timeform) nao encontrado ou ja aceito.")


def _list_cards(driver) -> List[Dict[str, str]]:
    cards: List[Dict[str, str]] = []
    try:
        container_list = driver.find_elements(By.CSS_SELECTOR, ".wfr-bytrack-content")
        for container in container_list:
            meetings = container.find_elements(By.CSS_SELECTOR, ".wfr-meeting")
            for section in meetings:
                try:
                    track_name = section.find_element(By.CSS_SELECTOR, "b.wfr-track").text.strip()
                    links = section.find_elements(By.CSS_SELECTOR, "ul li a.wfr-race")
                    for anchor in links:
                        hhmm = anchor.text.strip()
                        link = anchor.get_attribute("href") or anchor.get_attribute("ng-href")
                        if link and not link.startswith("http"):
                            link = urljoin(_TIMEFORM_BASE, link)
                        cards.append(
                            {
                                "track_name": track_name,
                                "track_key": normalize_track_name(track_name),
                                "hhmm": hhmm,
                                "url": link,
                            }
                        )
                except Exception:
                    continue
    except Exception:
        pass

    if not cards:
        sections = driver.find_elements(By.CSS_SELECTOR, ".w-cards-results section")
        for section in sections:
            try:
                track_name = section.find_element(By.TAG_NAME, "h3").text.strip()
                links = section.find_elements(By.CSS_SELECTOR, "li a")
                for anchor in links:
                    hhmm = anchor.text.strip()
                    link = anchor.get_attribute("href") or anchor.get_attribute("ng-href")
                    if link and not link.startswith("http"):
                        link = urljoin(_TIMEFORM_BASE, link)
                    cards.append(
                        {
                            "track_name": track_name,
                            "track_key": normalize_track_name(track_name),
                            "hhmm": hhmm,
                            "url": link,
                        }
                    )
            except Exception:
                continue
    return cards


def _extract_top3(driver) -> List[str]:
    try:
        container = driver.find_element(By.CSS_SELECTOR, ".rpf-verdict-container")
        selections = container.find_elements(By.CSS_SELECTOR, ".rpf-verdict-selection")
        top_names: List[str] = []
        for selection in selections[:3]:
            try:
                name_el = selection.find_element(By.CSS_SELECTOR, ".rpf-verdict-selection-name a")
                name = name_el.text.strip()
                if name:
                    top_names.append(clean_dog_name(name))
            except Exception:
                continue
        return top_names
    except Exception:
        return []


def _fractional_to_decimal(odd_txt: str) -> float | None:
    if not odd_txt:
        return None
    txt = odd_txt.strip().lower()
    if txt in {"evs", "evens"}:
        return 2.0
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", txt)
    if not m:
        return None
    num = int(m.group(1))
    den = int(m.group(2)) if int(m.group(2)) != 0 else 1
    return round((num / den) + 1.0, 2)


def _parse_forecast_items(forecast_text: str) -> List[Dict[str, object]]:
    parts = [p.strip() for p in forecast_text.split(",") if p.strip()]
    out: List[Dict[str, object]] = []
    for part in parts:
        match = re.match(r"^(?P<odd>(?:\d+\s*/\s*\d+|evs|evens))\s+(?P<name>.+)$", part, flags=re.IGNORECASE)
        if not match:
            match = re.match(r"^(?P<name>.+?)\s+(?P<odd>(?:\d+\s*/\s*\d+|evs|evens))$", part, flags=re.IGNORECASE)
        if not match:
            continue
        odd_raw = match.group("odd")
        name_raw = match.group("name")
        odd_val = _fractional_to_decimal(odd_raw)
        out.append({"name": clean_dog_name(name_raw), "odds": odd_val})
    return out


def _extract_betting_forecast(driver) -> List[Dict[str, object]]:
    texts: List[str] = []
    xpaths = [
        "//p[b[contains(., 'Betting Forecast')]]",
        "//p[contains(., 'Betting Forecast')]",
        "//*[contains(text(), 'Betting Forecast')]",
    ]
    for xp in xpaths:
        try:
            el = driver.find_element(By.XPATH, xp)
            txt = el.text.strip()
            if txt:
                texts.append(txt)
                break
        except Exception:
            continue
    if not texts:
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "Betting Forecast" in body_text:
                texts.append(body_text)
        except Exception:
            pass

    if not texts:
        return []

    raw = texts[0]
    if "Betting Forecast" in raw:
        raw = raw.split("Betting Forecast", 1)[1]
    raw = raw.lstrip(":").strip()
    if "\n" in raw:
        raw = raw.splitlines()[0].strip()

    return _parse_forecast_items(raw)


def _extract_category(driver) -> str:
    texts: List[str] = []
    try:
        el = driver.find_element(By.XPATH, "//*[contains(., 'Grade:')]")
        if el and el.text:
            texts.append(el.text)
    except Exception:
        pass

    body_text = ""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if body_text:
            texts.append(body_text)
    except Exception:
        body_text = ""

    for txt in texts:
        match = GRADE_RE.search(txt or "")
        if match:
            return match.group(1).upper().replace(" ", "")

    if body_text and "open race" in body_text.lower():
        return "OR"

    return "UNK"


def scrape_timeform_forecast() -> Tuple[List[Dict[str, object]], Dict[str, int]]:
    logger.info("Iniciando raspagem Timeform (cards do dia).")
    driver = build_chrome_driver()
    try:
        driver.get(_TIMEFORM_HOME)
        _accept_cookies(driver)
        _sleep_jitter("home")

        cards = _list_cards(driver)
        logger.debug("Total de cards Timeform capturados: {}", len(cards))

        count_top3 = 0
        count_forecast = 0
        count_processed = 0
        skipped_past = 0
        today_date = date.today()
        category_counts: Dict[str, int] = {}

        rows: List[Dict[str, object]] = []

        for card in cards:
            track = card.get("track_name", "")
            hhmm = card.get("hhmm", "")
            url = card.get("url", "")
            if not (track and hhmm and url):
                continue

            race_dt = None
            try:
                hh, mm = [int(x) for x in hhmm.split(":")[:2]]
                race_dt = datetime.combine(today_date, dt_time(hh, mm))
            except Exception:
                race_dt = None

            if settings.SKIP_PAST_RACES and race_dt:
                now = datetime.now()
                if race_dt < now - timedelta(minutes=settings.PAST_RACE_GRACE_MINUTES):
                    skipped_past += 1
                    continue

            count_processed += 1
            driver.get(url)
            _sleep_jitter("race")

            top3 = _extract_top3(driver)
            category_raw = _extract_category(driver)
            category_norm = normalize_category(category_raw)
            if category_norm == "UNK":
                logger.warning("Categoria UNK (1ª tentativa), tentando novamente: {} {}", track, hhmm)
                time.sleep(1.5)
                category_raw = _extract_category(driver)
                category_norm = normalize_category(category_raw)
                if category_norm == "UNK":
                    logger.warning("Categoria UNK persistente (2ª tentativa): {} {}", track, hhmm)
            forecast_list = _extract_betting_forecast(driver)

            if not forecast_list:
                logger.warning("Betting Forecast não encontrado: {} {}", track, hhmm)

            out_row: Dict[str, object] = {
                "date": date.today().isoformat(),
                "track": track,
                "track_key": normalize_track_name(track),
                "hhmm": hhmm,
                "race_time_iso": hhmm_to_today_iso(hhmm) if hhmm else "",
                "category_raw": category_raw,
                "category_norm": category_norm,
                "TimeformTop1": top3[0] if len(top3) > 0 else "",
                "TimeformTop2": top3[1] if len(top3) > 1 else "",
                "TimeformTop3": top3[2] if len(top3) > 2 else "",
                "Forecast1": forecast_list[0]["name"] if len(forecast_list) > 0 else "",
                "Forecast2": forecast_list[1]["name"] if len(forecast_list) > 1 else "",
                "Forecast3": forecast_list[2]["name"] if len(forecast_list) > 2 else "",
                "Forecast1Odds": forecast_list[0]["odds"] if len(forecast_list) > 0 else None,
                "Forecast2Odds": forecast_list[1]["odds"] if len(forecast_list) > 1 else None,
                "Forecast3Odds": forecast_list[2]["odds"] if len(forecast_list) > 2 else None,
            }
            cat_norm = out_row["category_norm"]
            if cat_norm:
                category_counts[cat_norm] = category_counts.get(cat_norm, 0) + 1

            if len(top3) >= 3:
                count_top3 += 1
            if len(forecast_list) >= 3:
                count_forecast += 1

            rows.append(out_row)
            _sleep_jitter("post-race")

        stats = {
            "processed": count_processed,
            "with_top3": count_top3,
            "with_forecast": count_forecast,
            "skipped_past": skipped_past,
        }

        logger.info(
            "Raspagem Timeform concluida. Corridas processadas: {} | com top3: {} | com betting forecast: {} | puladas (passadas): {}",
            count_processed,
            count_top3,
            count_forecast,
            skipped_past,
        )
        logger.info("Distribuição de categorias (processadas): {}", category_counts)
        return rows, stats
    finally:
        driver.quit()


def build_timeform_forecast_df(rows: Iterable[Dict[str, object]]) -> pd.DataFrame:
    columns = [
        "date",
        "track",
        "track_key",
        "hhmm",
        "race_time_iso",
        "category_raw",
        "category_norm",
        "TimeformTop1",
        "TimeformTop2",
        "TimeformTop3",
        "Forecast1",
        "Forecast2",
        "Forecast3",
        "Forecast1Odds",
        "Forecast2Odds",
        "Forecast3Odds",
    ]
    data = []
    for row in rows:
        data.append({col: row.get(col) for col in columns})
    if not data:
        return pd.DataFrame([], columns=columns)
    return pd.DataFrame(data, columns=columns)


__all__ = ["scrape_timeform_forecast", "build_timeform_forecast_df"]

