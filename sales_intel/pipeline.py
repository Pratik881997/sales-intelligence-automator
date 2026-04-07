from __future__ import annotations

from dataclasses import dataclass

from sales_intel.driver_factory import create_chrome_driver
from sales_intel.google_organic import parse_organic_comprehensive
from sales_intel.lead_sources import resolve_direct_url
from sales_intel.llm import pick_relevant_url, summarize_from_crawl
from sales_intel.models import SalesBrief
from sales_intel.selenium_google import fetch_organic_results_html, search_google_query
from sales_intel.site_crawl import crawl_company_pages, crawl_company_pages_requests


@dataclass
class PipelineConfig:
    model_name: str = "mistral:latest"
    headless: bool = True


def not_found_brief(lead: str) -> SalesBrief:
    return SalesBrief(
        lead_input=lead,
        resolved_url="",
        company_name="",
        company_overview="",
        rationale="No relevant website found: no usable organic Google results in the first 3 pages, or crawl failed before summary.",
        research_notes="NOT_FOUND_IN_SEARCH",
    )


def crawl_failed_brief(lead: str, url: str, msg: str) -> SalesBrief:
    return SalesBrief(
        lead_input=lead,
        resolved_url=url,
        rationale=msg,
        research_notes="CRAWL_FAILED",
    )


def process_lead(lead: str, config: PipelineConfig, driver) -> SalesBrief:
    lead = (lead or "").strip()
    if not lead:
        return not_found_brief("")

    direct = resolve_direct_url(lead)
    # A) Website: http(s) or bare domain → load URL directly (no Google).
    if direct:
        chosen = direct
    else:
        # B) String (company name, etc.) → google.com search box on page 1, then &start= for pages 2–3.
        chosen = None
        query = f"{lead} official website"
        for page in range(3):
            search_google_query(driver, query, page)
            html = fetch_organic_results_html(driver)
            organic = parse_organic_comprehensive(html)
            if not organic:
                continue
            chosen = pick_relevant_url(lead, organic, config.model_name)
            if chosen:
                break

        if not chosen:
            return not_found_brief(lead)

    used_requests_fallback = False
    selenium_error = ""
    try:
        texts, pages = crawl_company_pages(driver, chosen)
    except Exception as exc:
        texts, pages = {}, []
        selenium_error = str(exc)

    landing = (texts.get("landing") or "").strip()
    if not landing:
        # Fallback: try direct HTTP fetch for bot-protected Selenium pages.
        try:
            req_texts, req_pages = crawl_company_pages_requests(chosen)
            req_landing = (req_texts.get("landing") or "").strip()
            if req_landing:
                texts, pages = req_texts, req_pages
                landing = req_landing
                used_requests_fallback = True
        except Exception:
            pass

    if not landing:
        err_blob = selenium_error.lower()
        if "err_name_not_resolved" in err_blob or "name_not_resolved" in err_blob:
            return SalesBrief(
                lead_input=lead,
                resolved_url=chosen,
                rationale="Domain could not be resolved (DNS lookup failed).",
                research_notes="DNS_UNRESOLVED",
            )
        return crawl_failed_brief(
            lead,
            chosen,
            "Could not extract text from landing page via Selenium or requests fallback.",
        )

    brief = summarize_from_crawl(lead, chosen, pages, texts, config.model_name)
    path_note = "direct_url" if direct else "google_search"
    extra = (brief.research_notes or "").strip()
    note = f"{path_note} | {extra}" if extra else path_note
    if used_requests_fallback:
        note = f"{note} | requests_fallback"
    brief = brief.model_copy(update={"research_notes": note})
    return brief


def run_pipeline(leads: list[str], config: PipelineConfig) -> tuple[list[SalesBrief], list[str]]:
    results: list[SalesBrief] = []
    errors: list[str] = []
    driver = create_chrome_driver(headless=config.headless)
    try:
        for lead in leads:
            try:
                results.append(process_lead(lead, config, driver))
            except Exception as exc:
                msg = str(exc).splitlines()[0][:280]
                errors.append(f"{lead}: {msg}")
    finally:
        driver.quit()
    return results, errors
