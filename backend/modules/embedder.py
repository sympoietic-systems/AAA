import asyncio
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from backend.skills.metadata import SkillMeta

from .base import ProcessingModule


class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        self._model_name = model_name
        self._device = device
        self._model: Optional[SentenceTransformer] = None
        self._dim: int = 0

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        return self._dim

    def load(self) -> None:
        if self._model is not None:
            return
        self._model = SentenceTransformer(self._model_name, device=self._device)
        self._dim = self._model.get_embedding_dimension()

    def encode(self, text: str) -> np.ndarray:
        if self._model is None:
            self.load()
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.astype("float32")

    async def encode_async(self, text: str) -> np.ndarray:
        return await asyncio.to_thread(self.encode, text)

    @staticmethod
    def serialize(embedding: np.ndarray) -> bytes:
        return embedding.tobytes()

    @staticmethod
    def deserialize(blob: bytes) -> np.ndarray:
        return np.frombuffer(blob, dtype="float32")


class EmbedderModule(ProcessingModule):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        self._service = EmbeddingService(model_name=model_name, device=device)

    @property
    def name(self) -> str:
        return "embedder"

    def validate(self) -> bool:
        try:
            self._service.load()
            return self._service.is_loaded
        except Exception:
            return False

    async def process(self, payload: dict) -> dict:
        self._service.load()
        content = payload.get("content", "")
        embedding = await self._service.encode_async(content)
        blob = self._service.serialize(embedding)
        payload["embedding"] = blob
        payload["embedding_model"] = self._service.model_name
        payload["embedding_dim"] = self._service.dim
        return payload

    @property
    def service(self) -> EmbeddingService:
        return self._service

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="embedder",
            description="Encodes text into 384-dimensional float32 vectors",
            category="perception",
            always_run=True,
        )
