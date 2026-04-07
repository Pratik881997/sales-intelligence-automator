from sales_intel.llm import brief_from_json, safe_json_parse


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


def test_brief_from_json_enforces_it_questions():
    brief = brief_from_json(
        "Acme Roofing",
        "https://acme.example",
        {
            "company_overview": "Roofing company serving Houston.",
            "services_offered": "Roof replacement and repair.",
            "sales_questions": ["What is your primary revenue-generating service?"],
        },
    )
    assert len(brief.sales_questions) == 3
    joined = " ".join(brief.sales_questions).lower()
    assert "automation" in joined or "integration" in joined or "systems" in joined

