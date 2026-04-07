"""Load pages with Selenium, extract readable text with BeautifulSoup."""

from __future__ import annotations

import re
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver


def _same_site(a: str, b: str) -> bool:
    def norm(h: str) -> str:
        h = h.lower().replace("www.", "")
        return h.split(":")[0]

    return norm(a) == norm(b)


def _role_for_path(path: str, anchor: str) -> str | None:
    blob = f"{path.lower()} {anchor.lower()}"
    if re.search(r"/about|/company|/team|/who-we-are|/our-story", blob):
        return "about"
    if re.search(r"/contact|/locations?|/get-in-touch|/visit", blob):
        return "contact"
    if re.search(r"/services?|/solutions?|/products?|/offerings?|/capabilities", blob):
        return "services"
    return None


def extract_page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    for sel in ("nav", "footer", "header", "[role='navigation']"):
        for n in soup.select(sel):
            n.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())


def discover_internal_urls(base_url: str, html: str, max_per_role: int = 1) -> dict[str, str]:
    """Map role -> first matching absolute URL (about, contact, services)."""
    soup = BeautifulSoup(html, "html.parser")
    base = urlparse(base_url)
    base_host = base.netloc
    found: dict[str, str] = {}
    counts = {"about": 0, "contact": 0, "services": 0}

    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        abs_url = urljoin(base_url, href)
        p = urlparse(abs_url)
        if p.scheme not in ("http", "https") or not _same_site(base_host, p.netloc):
            continue
        role = _role_for_path(p.path or "/", a.get_text(strip=True) or "")
        if not role:
            continue
        if counts[role] >= max_per_role:
            continue
        if role not in found:
            found[role] = abs_url
            counts[role] += 1
    return found


def crawl_company_pages(driver: WebDriver, start_url: str) -> tuple[dict[str, str], list[str]]:
    """
    Fetch landing + about/contact/services when discoverable.
    Returns (role -> plain text, list of URLs fetched).
    """
    texts: dict[str, str] = {}
    fetched: list[str] = []

    driver.set_page_load_timeout(45)
    driver.get(start_url)
    time.sleep(1.0)
    landing_html = driver.page_source
    fetched.append(driver.current_url)
    texts["landing"] = extract_page_text(landing_html)

    internal = discover_internal_urls(driver.current_url, landing_html)
    for role, url in internal.items():
        if url in fetched:
            continue
        try:
            driver.get(url)
            time.sleep(0.8)
            fetched.append(driver.current_url)
            texts[role] = extract_page_text(driver.page_source)
        except Exception:
            continue

    return texts, fetched
