from sales_intel.site_crawl import extract_page_text


def test_extract_page_text_strips_scripts():
    html = "<html><body><script>alert(1)</script><p> Hello  world </p></body></html>"
    t = extract_page_text(html)
    assert "alert" not in t.lower()
    assert "Hello world" in t
