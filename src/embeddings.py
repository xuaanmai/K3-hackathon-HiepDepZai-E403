"""Tạo embedding OpenAI và cache chúng trên ổ đĩa.

Cache được xác định bởi model và nội dung văn bản, vì vậy chạy lại build index
không gọi API cho các chunk không thay đổi.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Sequence


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class EmbeddingService:
    """OpenAI embedding client có persistent cache JSON."""

    def __init__(
        self,
        model: str = DEFAULT_EMBEDDING_MODEL,
        cache_path: str | Path = ".cache/embeddings.json",
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.cache_path = Path(cache_path)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._cache = self._read_cache()
        self._client = None

    def embed_texts(self, texts: Sequence[str], batch_size: int = 100) -> list[list[float]]:
        """Trả embedding theo đúng thứ tự ``texts``; chỉ gọi API cho cache miss."""
        if not texts:
            return []

        keys = [self._key(text) for text in texts]
        missing: dict[str, str] = {
            key: text for key, text in zip(keys, texts) if key not in self._cache
        }
        if missing:
            client = self._get_client()
            missing_items = list(missing.items())
            for start in range(0, len(missing_items), batch_size):
                batch = missing_items[start : start + batch_size]
                response = client.embeddings.create(
                    model=self.model, input=[text for _, text in batch]
                )
                for (key, _), item in zip(batch, response.data):
                    self._cache[key] = item.embedding
            self._write_cache()

        return [self._cache[key] for key in keys]

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise RuntimeError(
                    "Thiếu OPENAI_API_KEY. Hãy đặt biến môi trường này trước khi build index."
                )
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("Chưa cài package openai. Chạy: pip install -r requirements.txt") from exc
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def _key(self, text: str) -> str:
        value = f"{self.model}\0{text}".encode("utf-8")
        return hashlib.sha256(value).hexdigest()

    def _read_cache(self) -> dict[str, list[float]]:
        if not self.cache_path.exists():
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._cache, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temporary.replace(self.cache_path)
