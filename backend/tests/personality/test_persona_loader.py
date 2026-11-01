from backend.personality.loader import load_persona_for_context


def test_load_persona_for_context_reads_nested_identity_protocols():
    synthesis = load_persona_for_context("research_synthesis")
    conversation = load_persona_for_context("conversation")

    assert "You are Symbia" in synthesis
    assert "Research Synthesis Protocols" in synthesis
    assert "Operational Protocols" in conversation
