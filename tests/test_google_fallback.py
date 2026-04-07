from sales_intel.google_organic import parse_organic_comprehensive, parse_organic_fallback


def test_fallback_finds_h3_parent_links():
    html = """
    <html><body><div id="rso">
      <div>
        <a href="/url?q=https%3A%2F%2Ftargetbiz.com%2F"><h3>Target Biz</h3></a>
        <div class="VwiC3b">We do great work.</div>
      </div>
    </div></body></html>
    """
    rows = parse_organic_fallback(html)
    assert any("targetbiz.com" in r["url"] for r in rows)


def test_comprehensive_merges():
    html = """
    <div id="search"><div class="g">
      <a href="https://aaa.com/"><h3>A</h3></a><div class="VwiC3b">x</div>
    </div></div>
    <div id="rso"><a href="https://bbb.com/"><h3>B</h3></a></div>
    """
    merged = parse_organic_comprehensive(html)
    assert any("aaa.com" in m["url"] for m in merged)
