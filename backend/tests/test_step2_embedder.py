import sys, asyncio

sys.path.insert(0, "D:/AAA")

from backend.modules.embedder import EmbeddingService, EmbedderModule


async def test_embedder():
    svc = EmbeddingService(model_name="all-MiniLM-L6-v2", device="cpu")
    svc.load()

    vec = svc.encode("Hello, world!")
    print(f"Vector shape: {vec.shape}, dtype: {vec.dtype}")

    blob = EmbeddingService.serialize(vec)
    restored = EmbeddingService.deserialize(blob)
    print(f"Restored shape: {restored.shape}, dtype: {restored.dtype}")
    print(f"Match: {np.allclose(vec, restored)}")

    mod = EmbedderModule(model_name="all-MiniLM-L6-v2", device="cpu")
    assert mod.validate(), "Module validation failed"

    payload = {"content": "What is the meaning of life?", "speaker": "human"}
    result = await mod.process(payload)
    print(f"Has embedding: {'embedding' in result}")
    print(f"Model: {result.get('embedding_model')}")
    print(f"Dim: {result.get('embedding_dim')}")
    print(f"Blob size: {len(result.get('embedding', b''))} bytes")
    print("All embedding tests passed!")

import numpy as np
asyncio.run(test_embedder())
