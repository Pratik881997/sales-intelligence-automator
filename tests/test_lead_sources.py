from sales_intel.lead_sources import deduplicate, normalize_lead, parse_leads_text, resolve_direct_url


def test_normalize_lead_handles_html_and_whitespace():
    raw = "  BrightPlay Turf &amp; Landscaping, Chicago IL  "
    assert normalize_lead(raw) == "BrightPlay Turf & Landscaping, Chicago IL"


def test_parse_leads_text_removes_duplicates():
    text = "Acme Roofing\nacme roofing\nhttps://example.com\n"
    leads = parse_leads_text(text)
    assert leads == ["Acme Roofing", "https://example.com"]


def test_deduplicate_keeps_order():
    assert deduplicate(["A", "a", "B", "b", "C"]) == ["A", "B", "C"]


def test_resolve_direct_url_bare_domain():
    assert resolve_direct_url("example.com") == "https://example.com"
    assert resolve_direct_url("https://foo.bar/") == "https://foo.bar"
    assert resolve_direct_url("Some Company Name") is None

