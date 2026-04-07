from sales_intel.llm import heuristic_pick_url


def test_heuristic_matches_lead_keywords():
    organic = [
        {"url": "https://other.com/", "title": "Other", "snippet": ""},
        {"url": "https://springhilllandscaping.com/", "title": "Spring Hill", "snippet": "Landscaping"},
    ]
    url = heuristic_pick_url("Spring Hill Landscaping Arizona", organic)
    assert "springhill" in url.lower()
