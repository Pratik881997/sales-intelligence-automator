"""Parse Google SERP HTML: organic links only (ads stripped). Primary + fallback parsers."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

# Domains we never treat as the company's own site when picking organic links.
THIRD_PARTY_DOMAINS = (
    "google.com",
    "gstatic.com",
    "youtube.com",
    "youtu.be",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "yelp.com",
    "bbb.org",
    "yellowpages.com",
    "manta.com",
    "mapquest.com",
    "bing.com",
    "pinterest.com",
    "tiktok.com",
)


def normalize_google_href(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("/url?"):
        qs = parse_qs(urlparse(href).query)
        if "q" in qs:
            return unquote(qs["q"][0])
        if "url" in qs:
            return unquote(qs["url"][0])
    if not href.startswith("http"):
        return ""
    if "google.com/url?" in href:
        qs = parse_qs(urlparse(href).query)
        if "q" in qs:
            return unquote(qs["q"][0])
    return href.split("#")[0]


def _host(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().replace("www.", "")
    except Exception:
        return ""


def is_plausible_organic_url(url: str) -> bool:
    if not url.startswith("http"):
        return False
    low = url.lower()
    bad_path = (
        "google.com/search",
        "google.com/maps",
        "webcache.googleusercontent",
        "support.google.com",
        "policies.google.com",
        "accounts.google",
    )
    if any(b in low for b in bad_path):
        return False
    host = _host(url)
    if not host:
        return False
    if any(tp == host or host.endswith("." + tp) for tp in THIRD_PARTY_DOMAINS):
        return False
    return True


def strip_sponsored_regions(soup: BeautifulSoup) -> None:
    for sel in (
        "#tads",
        "#tadsb",
        "#bottomads",
        "#tvcap",
        "#taw",
        ".commercial-unit",
        "[data-text-ad]",
    ):
        for node in soup.select(sel):
            node.decompose()


def parse_organic_results(html: str) -> list[dict[str, str]]:
    """Primary: classic div.g blocks."""
    soup = BeautifulSoup(html, "html.parser")
    strip_sponsored_regions(soup)

    seen: set[str] = set()
    out: list[dict[str, str]] = []

    selectors = (
        "#search div.g",
        "#rso div.g",
        "#center_col div.g",
        "#rso div.MjjYud",
        "div[data-hveid] div.g",
    )
    seen_blocks: set[int] = set()
    for sel in selectors:
        for block in soup.select(sel):
            bid = id(block)
            if bid in seen_blocks:
                continue
            link = block.select_one('a[href^="http"], a[href^="/url"]')
            if not link:
                continue
            href = normalize_google_href(link.get("href") or "")
            if not href or not is_plausible_organic_url(href):
                continue
            if href in seen:
                continue
            h3 = block.select_one("h3")
            title = h3.get_text(strip=True) if h3 else ""
            snip_el = block.select_one(
                ".VwiC3b, .lyLwlc, span.aCOpRe, .IsZvec, .lEBKkf, [data-sncf], .aCOpRe"
            )
            snippet = snip_el.get_text(strip=True) if snip_el else ""
            seen.add(href)
            seen_blocks.add(bid)
            out.append({"url": href, "title": title, "snippet": snippet})

    return out


def parse_organic_fallback(html: str) -> list[dict[str, str]]:
    """
    Fallback when div.g is empty: walk h3→parent a in #rso / #search (organic titles).
    """
    soup = BeautifulSoup(html, "html.parser")
    strip_sponsored_regions(soup)

    roots = soup.select("#rso, #search")
    if not roots:
        roots = [soup]

    seen: set[str] = set()
    out: list[dict[str, str]] = []

    for root in roots:
        for h3 in root.select("h3"):
            a = h3.find_parent("a")
            if not a or not a.get("href"):
                continue
            href = normalize_google_href(a["href"])
            if not href or not is_plausible_organic_url(href) or href in seen:
                continue
            title = h3.get_text(strip=True)
            parent = h3.find_parent("div")
            snippet = ""
            if parent:
                sn = parent.select_one(".VwiC3b, .lyLwlc, span.aCOpRe, .IsZvec")
                if sn:
                    snippet = sn.get_text(strip=True)
            seen.add(href)
            out.append({"url": href, "title": title, "snippet": snippet})

    return out


def parse_organic_comprehensive(html: str) -> list[dict[str, str]]:
    """Merge primary + fallback; dedupe by URL."""
    primary = parse_organic_results(html)
    if len(primary) >= 5:
        return primary
    fb = parse_organic_fallback(html)
    by_url = {r["url"]: r for r in primary}
    for r in fb:
        if r["url"] not in by_url:
            by_url[r["url"]] = r
    return list(by_url.values())
