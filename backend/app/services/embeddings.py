import hashlib
import math
import re
from collections.abc import Iterable
from functools import lru_cache

from app.core.config import Settings, get_settings


class EmbeddingError(RuntimeError):
    pass


class EmbeddingService:
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class LocalEmbeddingService(EmbeddingService):
    """Stable feature-hashing fallback used only by tests and offline development."""

    model_name = "local-feature-hash-v1"

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 else -1.0
            vector[index] += sign * (1 + math.log1p(len(token)))
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]


class FastEmbedEmbeddingService(EmbeddingService):
    """CPU-only ONNX embeddings; the configured model is downloaded once into the cache."""

    def __init__(self, settings: Settings):
        if settings.embedding_dimension != 384:
            raise EmbeddingError(
                f"{settings.embedding_model} is configured for EMBEDDING_DIMENSION=384"
            )
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise EmbeddingError(
                "Install the fastembed dependency to use local model embeddings"
            ) from exc
        self.model_name = settings.embedding_model
        self.dimensions = settings.embedding_dimension
        try:
            self.model = TextEmbedding(
                model_name=self.model_name,
                cache_dir=settings.embedding_cache_dir,
            )
        except Exception as exc:
            raise EmbeddingError(f"Could not load embedding model {self.model_name}") from exc

    @staticmethod
    def _lists(vectors: Iterable[object]) -> list[list[float]]:
        return [vector.tolist() for vector in vectors]  # type: ignore[attr-defined]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._lists(self.model.embed(texts))
        except Exception as exc:
            raise EmbeddingError("Local embedding generation failed") from exc

    def embed_query(self, text: str) -> list[float]:
        try:
            return self._lists(self.model.query_embed(text))[0]
        except Exception as exc:
            raise EmbeddingError("Local query embedding failed") from exc


@lru_cache(maxsize=4)
def _cached_fastembed(model: str, dimensions: int, cache_dir: str) -> EmbeddingService:
    settings = Settings(
        embedding_provider="fastembed",
        embedding_model=model,
        embedding_dimension=dimensions,
        embedding_cache_dir=cache_dir,
    )
    return FastEmbedEmbeddingService(settings)


def get_embedding_service(settings: Settings | None = None) -> EmbeddingService:
    settings = settings or get_settings()
    if settings.embedding_provider == "fastembed":
        return _cached_fastembed(
            settings.embedding_model,
            settings.embedding_dimension,
            settings.embedding_cache_dir,
        )
    return LocalEmbeddingService(settings.embedding_dimension)
