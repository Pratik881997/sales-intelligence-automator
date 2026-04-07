from sales_intel.google_organic import normalize_google_href, parse_organic_results


def test_normalize_google_redirect():
    assert "example.com" in normalize_google_href(
        "/url?q=https%3A%2F%2Fwww.example.com%2Fpath"
    )


def test_parse_organic_skips_ads_block():
    html = """
    <html><body>
    <div id="tads"><div class="g"><a href="https://ad.com"><h3>Ad</h3></a></div></div>
    <div id="search">
      <div class="g">
        <a href="https://realcompany.com/"><h3>Real Co</h3></a>
        <div class="VwiC3b">We sell roofs.</div>
      </div>
    </div>
    </body></html>
    """
    rows = parse_organic_results(html)
    urls = [r["url"] for r in rows]
    assert "https://realcompany.com/" in urls
    assert "https://ad.com/" not in urls
