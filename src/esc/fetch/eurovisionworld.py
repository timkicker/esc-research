"""eurovisionworld results for the years after the spijkervet release

the only fetch module that drives a browser, because the scoreboard is rendered
by javascript and the jury/televote switch hangs on a button. the rendered page
lands in data/raw (one file per year and view) and parse works offline from
there
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from esc import config
from esc.fetch import record_provenance

SOURCE_ID = "eurovisionworld"
YEARS = (2024, 2025, 2026)
VIEWS = ("jury", "tele")
PAGE = "https://eurovisionworld.com/eurovision/{year}"
# chrome or chromium, whichever is installed. ESC_CHROME overrides it
BROWSERS = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "chrome",
)
SETTLE = 6
AFTER_CLICK = 3
BETWEEN_PAGES = 4


def _browser() -> str | None:
    if os.environ.get("ESC_CHROME"):
        return os.environ["ESC_CHROME"]
    for name in BROWSERS:
        if found := shutil.which(name):
            return found
    # not on PATH, on windows and mac selenium finds chrome by itself
    return None


def _driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1600,2400")
    options.add_argument(f"--user-agent={config.USER_AGENT}")
    if browser := _browser():
        options.binary_location = browser
    # a chromedriver on PATH wins, otherwise selenium downloads the matching one
    service = Service(shutil.which("chromedriver"))
    try:
        return webdriver.Chrome(service=service, options=options)
    except Exception as e:
        first = (str(e).strip().splitlines() or [""])[0]
        raise SystemExit(
            f"[{SOURCE_ID}] could not start chrome or chromium: {first}\n"
            "install one of them or point ESC_CHROME at the binary"
        ) from e


def _render(driver, year: int, view: str) -> str | None:
    """return the page html with the requested scoreboard showing"""
    switched = driver.execute_script(
        "const b = document.querySelector('[data-button=\"' + arguments[0] + '\"]');"
        "if (!b) return false; b.click(); return true;",
        view,
    )
    if not switched:
        print(f"  {year} {view}: no button, the page layout changed")
        return None
    time.sleep(AFTER_CLICK)
    has_table = driver.execute_script(
        "return !!document.querySelector('table.scoreboard_table');"
    )
    if not has_table:
        print(f"  {year} {view}: no scoreboard table")
        return None
    return driver.execute_script("return document.documentElement.outerHTML;")


def fetch() -> list[Path]:
    target = config.RAW / SOURCE_ID
    target.mkdir(parents=True, exist_ok=True)
    wanted = [(y, v) for y in YEARS for v in VIEWS]
    missing = [(y, v) for y, v in wanted if not (target / f"{y}-{v}.html").exists()]
    print(f"[{SOURCE_ID}] {len(wanted)} page(s), {len(missing)} still to render")

    if missing:
        driver = _driver()
        try:
            for year in sorted({y for y, _ in missing}):
                driver.get(PAGE.format(year=year))
                time.sleep(SETTLE)
                for view in VIEWS:
                    path = target / f"{year}-{view}.html"
                    if path.exists():
                        continue
                    html = _render(driver, year, view)
                    if html is None:
                        continue
                    path.write_text(html, encoding="utf-8")
                    print(f"  {path.name}: {len(html)} chars")
                time.sleep(BETWEEN_PAGES)
        finally:
            driver.quit()

    paths = sorted(target.glob("*.html"))
    record_provenance(SOURCE_ID, paths)
    return paths
