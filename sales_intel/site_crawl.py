"""Load pages with Selenium, extract readable text with BeautifulSoup."""

from __future__ import annotations

import re
import time
from urllib.parse import urljoin, urlparse

import requests
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


def _fetch_html_requests(url: str, timeout: int = 25) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r.text


def _candidate_urls(start_url: str) -> list[str]:
    """Try practical host/protocol variants for blocked/broken direct URLs."""
    u = start_url.strip()
    p = urlparse(u if "://" in u else f"https://{u}")
    host = (p.netloc or p.path).strip("/")
    path = p.path if p.netloc else ""
    host_no_www = host[4:] if host.startswith("www.") else host
    host_www = host if host.startswith("www.") else f"www.{host}"
    variants = [
        f"https://{host}{path}",
        f"https://{host_no_www}{path}",
        f"https://{host_www}{path}",
        f"http://{host}{path}",
        f"http://{host_no_www}{path}",
        f"http://{host_www}{path}",
    ]
    out: list[str] = []
    seen: set[str] = set()
    for v in variants:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def crawl_company_pages_requests(start_url: str) -> tuple[dict[str, str], list[str]]:
    """
    Fallback crawler when Selenium content is blocked/empty.
    Uses requests + BS4 on landing/about/contact/services pages.
    """
    texts: dict[str, str] = {}
    fetched: list[str] = []

    landing_html = ""
    chosen_url = start_url
    last_error: Exception | None = None
    for candidate in _candidate_urls(start_url):
        try:
            landing_html = _fetch_html_requests(candidate)
            chosen_url = candidate
            break
        except Exception as exc:
            last_error = exc
            continue
    if not landing_html:
        if last_error:
            raise last_error
        raise RuntimeError("Could not fetch landing page via requests fallback.")

    fetched.append(chosen_url)
    texts["landing"] = extract_page_text(landing_html)

    internal = discover_internal_urls(chosen_url, landing_html)
    for role, url in internal.items():
        if url in fetched:
            continue
        try:
            html = _fetch_html_requests(url)
            fetched.append(url)
            texts[role] = extract_page_text(html)
        except Exception:
            continue

    return texts, fetched
