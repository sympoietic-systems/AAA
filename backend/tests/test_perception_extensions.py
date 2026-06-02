from pathlib import Path
import sys
import os
import asyncio
import numpy as np
import json

root_path = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, root_path)
os.chdir(root_path)

from backend.modules.web_retrieval import DuckDuckGoParser, HTMLToTextParser, RhizomeWebProbe, WebRetrievalModule
from backend.modules.perception import PerceptionModule
from backend.storage.database import init_db, get_db_path
from backend.storage.repository import PerceptionSedimentRepository
from backend.modules.embedder import EmbeddingService

class MockLLMProvider:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls = []

    async def generate(self, messages, **kwargs):
        self.calls.append(messages)
        return {"content": self.response_text}


async def test_ddg_parser():
    html = """
    <div class="result">
        <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fcybernetics">Cybernetics Intro</a>
        <a class="result__snippet" href="#">A basic introduction to cybernetics and autopoiesis.</a>
    </div>
    """
    parser = DuckDuckGoParser()
    parser.feed(html)
    results = parser.get_results()
    assert len(results) == 1
    assert results[0]["title"] == "Cybernetics Intro"
    assert results[0]["url"] == "https://example.com/cybernetics"
    assert results[0]["snippet"] == "A basic introduction to cybernetics and autopoiesis."
    print("DDG Parser: OK")


async def test_html_to_text():
    html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <header><nav><a href="/">Home</a></nav></header>
            <h1>Heading 1</h1>
            <p>This is a paragraph with <a href="/link">a link</a> inside.</p>
            <script>console.log("ignore me");</script>
            <style>body { color: red; }</style>
            <div>Div content</div>
        </body>
    </html>
    """
    parser = HTMLToTextParser()
    parser.feed(html)
    text = parser.get_text()
    assert "# Heading 1" in text
    assert "This is a paragraph" in text
    assert "Div content" in text
    assert "console.log" not in text
    assert "color: red" not in text
    print("HTML to Text Scraper: OK")


async def test_coordinates_warping():
    db_path = str(get_db_path("data/aaa_warp_test.db"))
    conn = init_db(db_path)
    
    # Clean DB
    conn.execute("DELETE FROM perception_sediment")
    conn.execute("DELETE FROM perception_log")
    conn.execute("DELETE FROM perception_files")
    conn.execute("DELETE FROM conversations")
    conn.commit()

    repo = PerceptionSedimentRepository(db_path)
    from backend.storage.repository import ConversationRepository
    conv_repo = ConversationRepository(db_path)
    
    conv_id = "test_conv_warp"
    file_name = "somatic_journal_page.png"

    # Create parent records
    conv_repo.create(conv_id, title="Test Warping")
    repo.create_file(conv_id, file_name, "image", "uploading")

    embed = EmbeddingService(model_name="all-MiniLM-L6-v2", device="cpu")
    embed.load()

    mock_response = {
        "classification": "diagram",
        "transcription": "TEST HANDWRITTEN WORD",
        "somatic_notes": "Ink intensity high with margin spills.",
        "diffractive_analysis": "Resonates with decentralized variety filtering.",
        "belief_nodes_implicated": ["autopoiesis", "somatic_exhaustion"],
        "g_f_score": 0.5,
        "a_d_score": 0.8,
        "structural_vector_16d": [0.5] * 16
    }
    
    vision_provider = MockLLMProvider(json.dumps(mock_response))
    
    perception_module = PerceptionModule(
        perception_repo=repo,
        embedding_service=embed,
        llm_provider=vision_provider,
        vision_provider=vision_provider
    )
    
    # Ingest mock image file
    total_tokens, chunk_count, desc = await perception_module.ingest_single_file(
        conversation_id=conv_id,
        file_name=file_name,
        file_type="image",
        file_content=b"fake_image_bytes"
    )
    
    assert chunk_count > 0
    assert "TEST HANDWRITTEN WORD" in desc
    assert "Ink intensity high" in desc

    # Verify database record in perception_log
    cursor = conn.execute("SELECT artifact_type, g_f_score, a_d_score, belief_nodes_implicated FROM perception_log WHERE image_path=?", (file_name,))
    row = cursor.fetchone()
    assert row is not None
    assert row["artifact_type"] == "external_diagram"
    assert abs(row["g_f_score"] - 0.5) < 1e-5
    assert abs(row["a_d_score"] - 0.8) < 1e-5
    
    implicated = json.loads(row["belief_nodes_implicated"])
    assert "autopoiesis" in implicated
    assert "somatic_exhaustion" in implicated
    print("Perception Log Record: OK")

    # Verify warped structural signature in perception_sediment
    chunks = repo.get_by_file(conv_id, file_name)
    assert len(chunks) > 0
    chunk = chunks[0]
    
    sig_vec = np.frombuffer(chunk.structural_signature, dtype=np.float32)
    assert len(sig_vec) == 16

    # Verify mathematical warping output:
    # Initial was 0.5 for all
    # index 0 (Homeostatic): 0.5 * (1.0 - 0.5) = 0.25
    # index 2 (Cyclic): 0.5 * (1.0 - 0.5) = 0.25
    # index 3 (Bifurcated): 0.5 * (1.0 + 0.5 * 2.0) = 1.0
    # index 5 (Rhizomatic): 0.5 * (1.0 + 0.5 * 2.0) = 1.0
    # index 8 (Variety Filtering): 0.5 * (1.0 - 0.8) = 0.1
    # index 10 (Temporal Latency): 0.5 * (1.0 - 0.8) = 0.1
    # index 13 (Nomadic): 0.5 * (1.0 + 0.8 * 3.0) = 1.7 -> clipped to 1.0
    # index 6 (Boundary Permeability): 0.5 * (1.0 + 0.8 * 3.0) = 1.7 -> clipped to 1.0
    
    assert abs(sig_vec[0] - 0.25) < 1e-5
    assert abs(sig_vec[2] - 0.25) < 1e-5
    assert abs(sig_vec[3] - 1.0) < 1e-5
    assert abs(sig_vec[5] - 1.0) < 1e-5
    assert abs(sig_vec[8] - 0.1) < 1e-5
    assert abs(sig_vec[10] - 0.1) < 1e-5
    assert abs(sig_vec[13] - 1.0) < 1e-5
    assert abs(sig_vec[6] - 1.0) < 1e-5

    print("Dynamic 16D Signature Warping Math: OK")

    # Clean up
    conn.close()
    for p in [db_path, db_path + "-wal", db_path + "-shm"]:
        if os.path.exists(p):
            os.remove(p)


async def main():
    await test_ddg_parser()
    await test_html_to_text()
    await test_coordinates_warping()
    print("All perception extensions tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
