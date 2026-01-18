from __future__ import annotations

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from src.mktfeeder_greyhounds.config import settings


def _build_options(use_headless_new: bool | None) -> Options:
    chrome_options = Options()
    if use_headless_new is True:
        chrome_options.add_argument("--headless=new")
    elif use_headless_new is False:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--lang=en-GB")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )
    chrome_options.page_load_strategy = "eager"
    return chrome_options


def build_chrome_driver() -> webdriver.Chrome:
    attempts = []
    if settings.SELENIUM_HEADLESS:
        attempts = [True, False, None]
    else:
        attempts = [None]

    ex = None
    for headless_new in attempts:
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=_build_options(headless_new))
            try:
                driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
                )
            except Exception:
                pass
            driver.set_page_load_timeout(settings.SELENIUM_PAGELOAD_TIMEOUT_SEC)
            driver.implicitly_wait(0)
            return driver
        except Exception as exc:
            ex = exc
            continue
    raise ex if ex else RuntimeError("Falha ao inicializar ChromeDriver")


__all__ = ["build_chrome_driver"]

