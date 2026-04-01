import hashlib
from typing import Iterable

from huggingface_hub import InferenceClient

from app.core.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self.provider = settings.embedding_provider.lower()
        self.dim = settings.embedding_dim
        self._hf_client = None

        if self.provider == "huggingface":
            self._hf_client = InferenceClient(token=settings.huggingface_api_key or None)

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        text_list = list(texts)
        if not text_list:
            return []
        if self.provider == "huggingface":
            return self._embed_huggingface(text_list)
        return [self._hash_embedding(t) for t in text_list]

    def embed_query(self, text: str) -> list[float]:
        vectors = self.embed_texts([text])
        return vectors[0]

    def _hash_embedding(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < self.dim:
            for byte in digest:
                values.append((byte / 127.5) - 1.0)
                if len(values) >= self.dim:
                    break
            digest = hashlib.sha256(digest).digest()
        return values

    def _embed_huggingface(self, texts: list[str]) -> list[list[float]]:
        if not settings.has_huggingface_key:
            raise RuntimeError("HUGGINGFACE_API_KEY missing while EMBEDDING_PROVIDER=huggingface")
        if self._hf_client is None:
            self._hf_client = InferenceClient(token=settings.huggingface_api_key or None)

        as_list: list[list[float]] = []
        for text in texts:
            vector = self._hf_client.feature_extraction(text=text, model=settings.hf_embedding_model)
            if hasattr(vector, "tolist"):
                vector = vector.tolist()
            if isinstance(vector, list) and len(vector) > 0 and isinstance(vector[0], list):
                vector = vector[0]
            if not isinstance(vector, list):
                raise RuntimeError("Hugging Face embedding response is not a list vector.")
            as_list.append([float(item) for item in vector])

        actual_dim = len(as_list[0]) if as_list else 0
        if actual_dim and actual_dim != self.dim:
            raise RuntimeError(
                f"Embedding dimension mismatch. EMBEDDING_DIM={self.dim}, "
                f"but model '{settings.hf_embedding_model}' outputs {actual_dim}."
            )
        return as_list


embedding_service = EmbeddingService()
