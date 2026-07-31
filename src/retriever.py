"""Tìm các chunk liên quan nhất bằng FAISS cosine similarity."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from src.embeddings import EmbeddingService


class Retriever:
    """Nạp FAISS index và trả về các nguồn theo giao diện của ứng dụng."""

    def __init__(
        self,
        index_path: str | Path = "storage/chunks.faiss",
        metadata_path: str | Path = "storage/chunks.json",
        embedding_service: EmbeddingService | None = None,
        min_score: float | None = None,
    ) -> None:
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.embedding_service = embedding_service or EmbeddingService()
        self.min_score = min_score
        self._index: faiss.Index | None = None
        self._chunks: list[dict[str, Any]] | None = None

    def retrieve(
        self, question: str, top_k: int = 4, min_score: float | None = None
    ) -> list[dict[str, Any]]:
        """Trả tối đa ``top_k`` nguồn có score cosine >= ngưỡng (nếu có)."""
        if not question or not question.strip():
            return []
        if top_k < 1:
            raise ValueError("top_k phải lớn hơn 0")

        index, chunks = self._load()
        if not chunks:
            return []
        query = np.asarray(
            self.embedding_service.embed_texts([question])[0], dtype="float32"
        ).reshape(1, -1)
        faiss.normalize_L2(query)
        scores, positions = index.search(query, min(top_k, len(chunks)))
        threshold = self.min_score if min_score is None else min_score

        results: list[dict[str, Any]] = []
        for score, position in zip(scores[0], positions[0]):
            if position < 0 or (threshold is not None and float(score) < threshold):
                continue
            chunk = chunks[int(position)]
            results.append(
                {
                    "source_id": chunk["source_id"],
                    "content": chunk["content"],
                    "score": round(float(score), 4),
                }
            )
        return results

    def _load(self) -> tuple[faiss.Index, list[dict[str, Any]]]:
        if self._index is None or self._chunks is None:
            if not self.index_path.exists() or not self.metadata_path.exists():
                raise FileNotFoundError(
                    "Chưa có index. Hãy chạy: python scripts/build_index.py --input data/processed/chunks.json"
                )
            self._index = faiss.read_index(str(self.index_path))
            self._chunks = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        return self._index, self._chunks


_default_retriever: Retriever | None = None


def retrieve(question: str, top_k: int = 4, min_score: float | None = None) -> list[dict[str, Any]]:
    """Hàm tiện dụng: ``sources = retrieve(question, top_k=4)``.

    Có thể đặt RETRIEVAL_MIN_SCORE, ví dụ ``0.35``, để loại kết quả yếu.
    """
    global _default_retriever
    if _default_retriever is None:
        value = os.getenv("RETRIEVAL_MIN_SCORE")
        threshold = float(value) if value else None
        _default_retriever = Retriever(min_score=threshold)
    return _default_retriever.retrieve(question, top_k=top_k, min_score=min_score)


def evaluate_retrieval(
    test_cases: list[dict[str, Any]], retriever: Retriever | None = None, top_k: int = 4
) -> list[dict[str, Any]]:
    """Kiểm tra câu nào retrieve đúng nguồn.

    Mỗi test case cần ``question`` và ``expected_source_ids`` (list source id).
    Kết quả từng câu chứa ``is_correct`` để dễ ghi ra báo cáo eval.
    """
    active_retriever = retriever or Retriever()
    report: list[dict[str, Any]] = []
    for case in test_cases:
        question = str(case["question"])
        expected = {str(source_id) for source_id in case["expected_source_ids"]}
        sources = active_retriever.retrieve(question, top_k=top_k)
        actual = [source["source_id"] for source in sources]
        matched = [source_id for source_id in actual if source_id in expected]
        report.append(
            {
                "question": question,
                "expected_source_ids": sorted(expected),
                "retrieved_source_ids": actual,
                "matched_source_ids": matched,
                "is_correct": bool(matched),
            }
        )
    return report
