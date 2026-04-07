from __future__ import annotations

import csv
import html
import re
from io import StringIO


URL_RE = re.compile(r"^https?://", re.IGNORECASE)
# Bare domain: example.com, sub.example.co.uk (no spaces — company names have spaces)
DOMAIN_ONLY_RE = re.compile(
    r"^([\w-]+\.)+[\w-]{2,}$",
    re.IGNORECASE,
)


def normalize_lead(raw: str) -> str:
    text = html.unescape(raw or "").replace("\uFFFD", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,")


def parse_leads_text(text: str) -> list[str]:
    leads: list[str] = []
    for line in text.splitlines():
        cleaned = normalize_lead(line)
        if cleaned:
            leads.append(cleaned)
    return deduplicate(leads)


def parse_csv_text(csv_text: str) -> list[str]:
    rows = csv.DictReader(StringIO(csv_text))
    leads: list[str] = []
    for row in rows:
        value = normalize_lead(row.get("leads", ""))
        if value:
            leads.append(value)
    return deduplicate(leads)


def deduplicate(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def is_url(lead: str) -> bool:
    return bool(URL_RE.match(lead))


def is_direct_website_input(lead: str) -> bool:
    """
    True → skip Google; open URL directly in Selenium.
    - http(s)://...
    - bare domain without spaces (e.g. example.com, www.foo.bar.com)
    """
    return resolve_direct_url(lead) is not None


def is_string_search_input(lead: str) -> bool:
    """True → Google search flow (up to 3 pages), then crawl chosen site."""
    return not is_direct_website_input(lead)


def resolve_direct_url(lead: str) -> str | None:
    """If lead is http(s) or a bare domain (no spaces), return normalized https URL."""
    s = (lead or "").strip().rstrip("/")
    if not s:
        return None
    if is_url(s):
        return s
    if " " in s:
        return None
    if DOMAIN_ONLY_RE.match(s):
        return "https://" + s.lstrip("/")
    return None
