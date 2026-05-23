import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from backend.modules.digester import RhizomaticDigester
from backend.modules.background_tasks.actions.summarize import SummarizeAction, parse_json_safely


def test_rhizomatic_digester_chunking():
    digester = RhizomaticDigester()
    text = (
        "This is paragraph one.\n\n"
        "This is paragraph two. It has more words. We want to see how chunking works.\n\n"
        "This is paragraph three."
    )
    
    # Test paragraph grouping chunker
    chunks = digester.chunk_with_metadata(text, chunk_size=20, overlap=5)
    assert len(chunks) > 0
    for chunk in chunks:
        assert "text" in chunk
        assert "paragraph_indices" in chunk
        # Verify text actually contains corresponding paragraphs
        for idx in chunk["paragraph_indices"]:
            if idx == 0:
                assert "paragraph one" in chunk["text"]
            elif idx == 1:
                assert "paragraph two" in chunk["text"]
            elif idx == 2:
                assert "paragraph three" in chunk["text"]

    # Test get_super_chunks
    super_chunks = digester.get_super_chunks(text, super_chunk_size=10)
    # Since each paragraph has ~4, ~13, ~4 words, they should split
    assert len(super_chunks) >= 2
    assert super_chunks[0]["start_paragraph_idx"] == 0


def test_parse_json_safely():
    # Simple brace parsing
    content_raw = 'Some model chat: {"local_summary": "Test text", "opacity_map": [{"paragraph_index": 1, "reason": "dense"}]} and some ending.'
    parsed = parse_json_safely(content_raw)
    assert parsed["local_summary"] == "Test text"
    assert parsed["opacity_map"][0]["paragraph_index"] == 1

    # Markdown blocks
    markdown_content = '```json\n{"local_summary": "Markdown block"}\n```'
    parsed_md = parse_json_safely(markdown_content)
    assert parsed_md["local_summary"] == "Markdown block"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_summarize_action_execute():


    action = SummarizeAction()
    
    # Mock LLM provider
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = {
        "content": '{"local_summary": "Block Summary 1", "opacity_map": [{"paragraph_index": 2, "reason": "dense metaphor", "shadow_text": "Metaphorical text"}]}',
        "model": "test-model"
    }

    text = "Paragraph 1.\n\nParagraph 2 is opaque.\n\nParagraph 3."
    payload = {"text": text}
    
    res = await action.execute(mock_provider, payload)
    
    assert "content" in res
    assert "opacity_map" in res
    
    # Since there is only 1 super-chunk (<4000 words), it should return local summary directly
    assert res["content"] == "Block Summary 1"
    assert len(res["opacity_map"]) == 1
    # 0-based index for paragraph 2 (local index 2 -> 0-based global index 1)
    assert res["opacity_map"][0]["paragraph_index"] == 1
    assert res["opacity_map"][0]["reason"] == "dense metaphor"
    assert res["opacity_map"][0]["shadow_text"] == "Metaphorical text"
