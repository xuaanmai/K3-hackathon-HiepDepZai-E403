"""Dựng/cập nhật FAISS index từ các chunk do bước xử lý dữ liệu tạo ra."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import faiss
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.embeddings import DEFAULT_EMBEDDING_MODEL, EmbeddingService


def load_chunks(path: Path) -> list[dict[str, Any]]:
    """Đọc JSON array, JSON object có key ``chunks``, hoặc JSONL."""
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        chunks = [json.loads(line) for line in raw.splitlines() if line.strip()]
    else:
        payload = json.loads(raw)
        chunks = payload.get("chunks", []) if isinstance(payload, dict) else payload
    if not isinstance(chunks, list):
        raise ValueError("Dữ liệu chunk phải là một JSON array, {'chunks': [...]}, hoặc JSONL.")

    valid: list[dict[str, Any]] = []
    for number, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict) or not chunk.get("source_id") or not chunk.get("content"):
            raise ValueError(f"Chunk dòng {number} phải có source_id và content không rỗng.")
        normalized = dict(chunk)
        normalized["source_id"] = str(chunk["source_id"])
        normalized["content"] = str(chunk["content"])
        valid.append(normalized)
    return valid


def build_index(chunks: list[dict[str, Any]], output_dir: Path, model: str) -> None:
    service = EmbeddingService(model=model, cache_path=output_dir / "embedding_cache.json")
    vectors = np.asarray(service.embed_texts([chunk["content"] for chunk in chunks]), dtype="float32")
    if vectors.ndim != 2 or not len(vectors):
        raise ValueError("Không tạo được embedding hợp lệ.")
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])  # inner product sau normalize = cosine similarity
    index.add(vectors)
    output_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(output_dir / "chunks.faiss"))
    (output_dir / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã index {len(chunks)} chunks tại {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo FAISS index cho retrieval")
    parser.add_argument("--input", required=True, type=Path, help="chunks.json hoặc chunks.jsonl")
    parser.add_argument("--output-dir", type=Path, default=Path("storage"))
    parser.add_argument("--model", default=DEFAULT_EMBEDDING_MODEL)
    args = parser.parse_args()
    build_index(load_chunks(args.input), args.output_dir, args.model)


if __name__ == "__main__":
    main()
