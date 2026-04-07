"""Google in Chrome: page 1 via google.com search box; pages 2–3 via search URL + wait for results."""

from __future__ import annotations

import random
import time
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def dismiss_cookie_if_present(driver) -> None:
    time.sleep(0.6)
    selectors = (
        "button#L2AGLb",
        "button[aria-label='Accept all']",
        "button[aria-label='Accept all cookies']",
        "div[aria-label='Accept all']",
        "form[action*='consent'] button",
    )
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            el.click()
            time.sleep(0.4)
            return
        except Exception:
            continue


def search_google_query(driver, query: str, page_index: int) -> None:
    """
    page_index 0: open google.com, type query in the box, submit (real user flow).
    page_index 1–2: navigate to search URL with start=10 / 20 (same query).
    """
    wait = WebDriverWait(driver, 30)

    if page_index == 0:
        driver.get("https://www.google.com/")
        time.sleep(0.5)
        dismiss_cookie_if_present(driver)
        q = wait.until(EC.element_to_be_clickable((By.NAME, "q")))
        try:
            q.clear()
        except Exception:
            pass
        q.send_keys(query)
        q.send_keys(Keys.RETURN)
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#search, #rso, #center_col, div[role='main']")
            )
        )
        time.sleep(random.uniform(1.8, 2.8))
        dismiss_cookie_if_present(driver)
        return

    start = page_index * 10
    url = f"https://www.google.com/search?q={quote_plus(query)}&start={start}&hl=en&pws=0&num=10"
    driver.get(url)
    time.sleep(random.uniform(1.0, 1.8))
    dismiss_cookie_if_present(driver)
    wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#search, #rso, #center_col, div[role='main']")
        )
    )
    time.sleep(random.uniform(0.8, 1.4))


def fetch_organic_results_html(driver) -> str:
    return driver.page_source


# Backwards-compatible name
def open_google_results_page(driver, query: str, page_index: int) -> None:
    search_google_query(driver, query, page_index)
