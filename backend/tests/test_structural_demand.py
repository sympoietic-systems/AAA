from backend.utils.structural_demand import detect_structural_demand


def test_no_demand_on_plain_text():
    d = detect_structural_demand("The document discusses sampling methods in general terms.")
    assert d["demanded"] is False


def test_unmet_section_citation():
    d = detect_structural_demand("This claim depends on §2.3, which I could not retrieve.")
    assert d["unmet_section_citation"] is True
    assert d["demanded"] is True
    assert "2.3" in d["cited_sections"]


def test_citation_met_when_section_retrieved():
    d = detect_structural_demand(
        "As shown in section 2.1, the sampling is stratified.",
        retrieved_heading_paths=[["Method", "2.1 Sampling"]],
    )
    assert d["unmet_section_citation"] is False
    assert d["demanded"] is False


def test_request_more_context():
    d = detect_structural_demand("I would need more from section 4 to answer this.")
    assert d["requested_more_context"] is True
    assert d["demanded"] is True


def test_follow_thread():
    d = detect_structural_demand("To proceed I should drill into the adjacent sections.")
    assert d["follow_thread"] is True
    assert d["demanded"] is True
