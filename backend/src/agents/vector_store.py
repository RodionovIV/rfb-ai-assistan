from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np

try:  # pragma: no cover - optional runtime dependency
    import faiss  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback when FAISS is unavailable
    faiss = None  # type: ignore


@dataclass
class VectorDocument:
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


class BaseVectorStore:
    def add_texts(self, documents: Sequence[VectorDocument]) -> None:
        raise NotImplementedError

    def similarity_search(self, query: str, k: int = 3) -> List[VectorDocument]:
        raise NotImplementedError


class SimpleVectorStore(BaseVectorStore):
    """Pure Python similarity search used as a fallback when FAISS is not available."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension
        self._documents: List[VectorDocument] = []
        self._vectors: List[np.ndarray] = []

    def add_texts(self, documents: Sequence[VectorDocument]) -> None:
        for document in documents:
            self._documents.append(document)
            self._vectors.append(self._embed(document.text))

    def similarity_search(self, query: str, k: int = 3) -> List[VectorDocument]:
        if not self._documents:
            return []

        query_vector = self._embed(query)
        scores = [self._cosine_similarity(query_vector, vector) for vector in self._vectors]
        ranked = sorted(zip(scores, self._documents), key=lambda item: item[0], reverse=True)
        return [doc for _, doc in ranked[:k]]

    def _embed(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimension, dtype=np.float32)
        for token in text.split():
            idx = hash(token) % self.dimension
            vector[idx] += 1.0
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector

    @staticmethod
    def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        denominator = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
        if denominator == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / denominator)


class FaissVectorStore(BaseVectorStore):
    """FAISS backed vector search using a simple hashing embedding."""

    def __init__(self, dimension: int = 384) -> None:
        if faiss is None:  # pragma: no cover - executed when dependency missing
            raise RuntimeError("faiss-cpu must be installed to use FaissVectorStore")
        self.dimension = dimension
        self._index = faiss.IndexFlatIP(dimension)
        self._documents: List[VectorDocument] = []

    def add_texts(self, documents: Sequence[VectorDocument]) -> None:
        embeddings = np.vstack([self._embed(document.text) for document in documents]).astype(np.float32)
        self._index.add(embeddings)
        self._documents.extend(documents)

    def similarity_search(self, query: str, k: int = 3) -> List[VectorDocument]:
        if not self._documents:
            return []
        query_vector = self._embed(query).reshape(1, -1).astype(np.float32)
        _, indices = self._index.search(query_vector, min(k, len(self._documents)))
        return [self._documents[i] for i in indices[0] if i != -1]

    def _embed(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimension, dtype=np.float32)
        for token in text.split():
            idx = hash(token) % self.dimension
            vector[idx] += 1.0
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector


def create_vector_store(dimension: int = 384) -> BaseVectorStore:
    if faiss is not None:
        try:
            return FaissVectorStore(dimension=dimension)
        except RuntimeError:
            pass
    return SimpleVectorStore(dimension=dimension)

