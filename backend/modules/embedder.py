import asyncio
import logging
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from backend.pipeline.metadata import ModuleMeta

from .base import ProcessingModule

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        offline: bool = True,
        cache_dir: Optional[str] = None,
    ):
        self._model_name = model_name
        self._device = device
        self._offline = offline
        self._cache_dir = cache_dir
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

        kwargs = {"device": self._device}
        if self._cache_dir:
            kwargs["cache_folder"] = self._cache_dir

        if self._offline:
            kwargs["local_files_only"] = True
            try:
                logger.info(
                    "Loading %s from local cache (offline mode)", self._model_name
                )
                self._model = SentenceTransformer(self._model_name, **kwargs)
            except Exception:
                logger.info(
                    "Model not found in local cache, downloading %s from HuggingFace",
                    self._model_name,
                )
                kwargs["local_files_only"] = False
                self._model = SentenceTransformer(self._model_name, **kwargs)
        else:
            logger.info("Loading %s (online mode)", self._model_name)
            self._model = SentenceTransformer(self._model_name, **kwargs)

        self._dim = self._model.get_embedding_dimension()
        logger.info(
            "Embedding model ready: %s (dim=%d, device=%s)",
            self._model_name,
            self._dim,
            self._device,
        )

    def preload(self) -> None:
        self.load()

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
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        offline: bool = True,
        cache_dir: Optional[str] = None,
    ):
        self._service = EmbeddingService(
            model_name=model_name,
            device=device,
            offline=offline,
            cache_dir=cache_dir,
        )

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
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="embedder",
            description="Encodes text into 384-dimensional float32 vectors",
            category="perception",
            always_run=True,
        )
