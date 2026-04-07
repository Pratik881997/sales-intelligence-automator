from __future__ import annotations

import json
import re
from typing import Any

import requests

from sales_intel.models import SalesBrief, SectionItem


OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"


def _ollama_generate(
    prompt: str,
    model: str,
    *,
    use_json: bool = True,
    timeout: int = 240,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 4096},
    }
    if use_json:
        payload["format"] = "json"
    r = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=timeout)
    r.raise_for_status()
    return (r.json().get("response") or "").strip()


def _parse_json_loose(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
        if m:
            raw = m.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        a, b = raw.find("{"), raw.rfind("}")
        if a >= 0 and b > a:
            return json.loads(raw[a : b + 1])
        raise


def _llm_pick_index(lead: str, organic: list[dict[str, str]], model: str) -> int | None:
    if not organic:
        return None
    lines = []
    for i, r in enumerate(organic):
        sn = (r.get("snippet") or "")[:400]
        lines.append(f"{i}. {r.get('url','')}\n   Title: {r.get('title','')}\n   Snippet: {sn}")
    block = "\n".join(lines)
    prompt = f"""Select the official company website for this sales lead from the ORGANIC Google results below.
Ads/sponsored links were removed — these are natural search results only.

Lead: {lead}

Results:
{block}

Valid index range: 0 through {len(organic) - 1}.
Respond with JSON only: {{"chosen_index": N}} where N is an integer, or {{"chosen_index": null}} if none are the business's own official site.
Prefer the company's primary domain. Reject Yelp, Facebook, LinkedIn, directories, and social profiles.
"""
    raw = _ollama_generate(prompt, model, use_json=True)
    try:
        data = _parse_json_loose(raw)
    except Exception:
        return None
    idx = data.get("chosen_index")
    if idx is None:
        return None
    try:
        i = int(idx)
    except (TypeError, ValueError):
        return None
    if 0 <= i < len(organic):
        return i
    return None


def heuristic_pick_url(lead: str, organic: list[dict[str, str]]) -> str | None:
    """If the LLM fails, pick best organic row by keyword overlap, else first result."""
    if not organic:
        return None
    tokens = [t.lower() for t in re.findall(r"[a-zA-Z]{4,}", lead)]
    best_url: str | None = None
    best = -1
    for r in organic:
        blob = f"{r.get('url', '')} {r.get('title', '')}".lower()
        score = sum(1 for t in tokens if t in blob)
        if score > best:
            best = score
            best_url = r["url"]
    if best >= 1 and best_url:
        return best_url
    return organic[0]["url"]


def pick_relevant_url(lead: str, organic: list[dict[str, str]], model: str) -> str | None:
    """LLM first; if null or error, heuristic from organic list."""
    if not organic:
        return None
    idx = _llm_pick_index(lead, organic, model)
    if idx is not None:
        return organic[idx]["url"]
    return heuristic_pick_url(lead, organic)


def format_crawl_for_prompt(texts: dict[str, str]) -> str:
    order = ("landing", "about", "services", "contact")
    labels = {
        "landing": "HOME / LANDING",
        "about": "ABOUT",
        "services": "SERVICES",
        "contact": "CONTACT",
    }
    parts = []
    for k in order:
        if k in texts and texts[k]:
            parts.append(f"=== {labels[k]} ===\n{texts[k][:12000]}")
    for k, v in texts.items():
        if k not in order and v:
            parts.append(f"=== {k.upper()} ===\n{v[:8000]}")
    return "\n\n".join(parts)


def summarize_from_crawl(
    lead_input: str,
    resolved_url: str,
    crawled_pages: list[str],
    texts: dict[str, str],
    model: str,
) -> SalesBrief:
    blob = format_crawl_for_prompt(texts)
    prompt = f"""You are a B2B sales researcher. Using ONLY the crawled website text below, produce a detailed JSON summary.

Lead: {lead_input}
Resolved URL: {resolved_url}
Pages fetched: {", ".join(crawled_pages[:25])}

Required JSON keys:
- company_name
- company_overview (2-6 sentences)
- services_offered (what they offer)
- core_product_or_service
- target_customer_or_audience
- contact_details (phones, emails, address if present in text)
- sections: array of {{"title","content"}} for About, Services, Contact, Audience as appropriate
- b2b_qualified (boolean), b2b_confidence (0-100)
- sales_questions: exactly 3 strings
- rationale, signals (array of strings), research_notes

Crawled text:
{blob[:28000]}
"""
    raw = _ollama_generate(prompt, model, use_json=True)
    try:
        data = _parse_json_loose(raw)
    except Exception:
        return SalesBrief(
            lead_input=lead_input,
            resolved_url=resolved_url,
            research_notes=f"LLM JSON parse failed. Raw (truncated): {raw[:500]}",
            rationale="Model output was not valid JSON; see research_notes.",
        )
    return brief_from_json(lead_input, resolved_url, data)


def brief_from_json(lead_input: str, resolved_url: str, brief_json: dict[str, Any]) -> SalesBrief:
    sales_questions = brief_json.get("sales_questions") or []
    if not isinstance(sales_questions, list):
        sales_questions = []
    sales_questions = [str(q).strip() for q in sales_questions if str(q).strip()][:3]

    raw_sections = brief_json.get("sections") or []
    sections: list[SectionItem] = []
    if isinstance(raw_sections, list):
        for item in raw_sections:
            if not isinstance(item, dict):
                continue
            t = str(item.get("title", "")).strip()
            c = str(item.get("content", "")).strip()
            if t or c:
                sections.append(SectionItem(title=t or "Section", content=c))

    return SalesBrief(
        lead_input=lead_input,
        resolved_url=resolved_url,
        company_name=str(brief_json.get("company_name", "") or ""),
        company_overview=str(brief_json.get("company_overview", "") or ""),
        core_product_or_service=str(brief_json.get("core_product_or_service", "") or ""),
        target_customer_or_audience=str(brief_json.get("target_customer_or_audience", "") or ""),
        contact_details=str(brief_json.get("contact_details", "") or ""),
        services_offered=str(brief_json.get("services_offered", "") or ""),
        sections=sections,
        b2b_qualified=bool(brief_json.get("b2b_qualified", False)),
        b2b_confidence=max(0, min(100, int(brief_json.get("b2b_confidence") or 0))),
        sales_questions=sales_questions,
        rationale=str(brief_json.get("rationale", "") or ""),
        signals=[str(s).strip() for s in (brief_json.get("signals") or []) if str(s).strip()],
        research_notes=str(brief_json.get("research_notes", "") or ""),
    )


def safe_json_parse(raw: str) -> dict[str, Any]:
    return _parse_json_loose(raw)
