from __future__ import annotations

import math

from src.settings.general import config


def build_embedding(text: str, *, dimension: int | None = None) -> list[float]:
    """Generate a deterministic pseudo-embedding for the provided text."""

    dim = dimension or config.vector_index.dimension
    vector = [0.0] * dim
    if not text:
        return vector
    for idx, byte in enumerate(text.encode("utf-8")):
        vector[idx % dim] += byte / 255.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector
