from __future__ import annotations

import inspect
import json
import math
import uuid
from typing import Any, Iterable

from redis.asyncio import Redis
from redis.exceptions import ResponseError
from redisvl.index import SearchIndex


def _ensure_float_list(values: Iterable[float]) -> list[float]:
    return [float(v) for v in values]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


class VectorIndexRepository:
    def __init__(self, redis_client: Redis, index: SearchIndex) -> None:
        self._redis = redis_client
        self._index = index
        prefix = getattr(index.schema, "prefix", "chunk")
        if isinstance(prefix, (list, tuple)):
            prefix = prefix[0]
        self._prefix = str(prefix)
        self._ids_key = f"{self._prefix}:ids"

    def _chunk_key(self, chunk_id: uuid.UUID | str) -> str:
        return f"{self._prefix}:{chunk_id}"

    async def ensure_index(self, overwrite: bool = False) -> None:
        exists = False
        exists_method = getattr(self._index, "exists", None)
        if callable(exists_method):
            maybe_exists = exists_method()
            if inspect.isawaitable(maybe_exists):
                exists = await maybe_exists  # type: ignore[assignment]
            else:
                exists = bool(maybe_exists)
        if exists and not overwrite:
            return
        try:
            result = self._index.create(overwrite=overwrite)
            if inspect.isawaitable(result):
                await result  # type: ignore[misc]
        except ResponseError as exc:  # pragma: no cover - depends on Redis configuration
            if overwrite:
                raise
            message = str(exc).lower()
            if "exists" not in message:
                raise

    async def upsert_chunk(
        self,
        *,
        chunk_id: uuid.UUID,
        project_id: uuid.UUID,
        file_id: uuid.UUID,
        content: str,
        embedding: Iterable[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "chunk_id": str(chunk_id),
            "project_id": str(project_id),
            "file_id": str(file_id),
            "content": content,
            "embedding": json.dumps(_ensure_float_list(embedding)),
        }
        if metadata:
            payload["metadata"] = json.dumps(metadata)
        key = self._chunk_key(chunk_id)
        await self._redis.hset(key, mapping=payload)
        await self._redis.sadd(self._ids_key, str(chunk_id))

    async def remove_chunk(self, chunk_id: uuid.UUID) -> None:
        await self._redis.delete(self._chunk_key(chunk_id))
        await self._redis.srem(self._ids_key, str(chunk_id))

    async def fetch_chunk_payload(self, chunk_id: uuid.UUID | str) -> dict[str, Any] | None:
        key = self._chunk_key(chunk_id)
        raw = await self._redis.hgetall(key)
        if not raw:
            return None
        return self._deserialize_payload(raw)

    async def search_similar(
        self,
        embedding: Iterable[float],
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        target = _ensure_float_list(embedding)
        chunk_ids = await self._redis.smembers(self._ids_key)
        results: list[tuple[float, dict[str, Any]]] = []
        for chunk_id in chunk_ids:
            if isinstance(chunk_id, bytes):
                chunk_id = chunk_id.decode("utf-8")
            try:
                chunk_uuid = uuid.UUID(str(chunk_id))
            except ValueError:
                continue
            payload = await self.fetch_chunk_payload(chunk_uuid)
            if not payload:
                continue
            stored_embedding = payload.get("embedding")
            if not stored_embedding:
                continue
            score = _cosine_similarity(target, stored_embedding)
            results.append((score, payload))
        results.sort(key=lambda item: item[0], reverse=True)
        return [payload | {"score": score} for score, payload in results[:limit]]

    def _deserialize_payload(self, raw: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in raw.items():
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            if key in {"chunk_id", "project_id", "file_id"}:
                payload[key] = value
            elif key == "embedding":
                payload[key] = _ensure_float_list(json.loads(value))
            elif key == "metadata":
                payload[key] = json.loads(value)
            else:
                payload[key] = value
        return payload
