from sales_intel.llm import safe_json_parse


def test_safe_json_parse_direct_json():
    data = safe_json_parse('{"company_name":"Acme","b2b_qualified":true}')
    assert data["company_name"] == "Acme"
    assert data["b2b_qualified"] is True


def test_safe_json_parse_extracts_embedded_json():
    raw = 'Some intro... {"company_name":"Acme","b2b_confidence":80} trailing'
    data = safe_json_parse(raw)
    assert data["company_name"] == "Acme"
    assert data["b2b_confidence"] == 80


def test_safe_json_parse_fenced_block():
    raw = '```json\n{"company_name":"Zed","company_overview":"Hi"}\n```'
    data = safe_json_parse(raw)
    assert data["company_name"] == "Zed"

