from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
TRANSCRIPT_DIR = ROOT_DIR / "data" / "vlearn-pack" / "transcript"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "chunks.json"
MAX_CONTENT_LENGTH = 4000


def clean_text(text: str) -> str:
    """Normalize transcript content while keeping the source meaning intact."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = cleaned.strip()

    lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if re.match(r"^#{1,6}\s+", stripped):
            continue
        if re.match(r"^>\s*", stripped):
            continue
        lines.append(stripped)

    cleaned = "\n".join(lines)

    # Remove markdown emphasis wrappers without losing the content itself.
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)

    # Normalize whitespace while preserving paragraph boundaries.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)

    return cleaned.strip()


def infer_section(text: str, position: int) -> str:
    """Find the nearest heading before a given position."""
    lines = text[:position].splitlines()
    current_section = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
        elif stripped.startswith("# ") and not current_section:
            current_section = stripped[2:].strip()
    return current_section or "Tổng quan"


def parse_transcript_file(path: Path) -> List[Dict[str, str]]:
    """Parse one transcript file into standardized chunk dictionaries."""
    content = path.read_text(encoding="utf-8")
    lesson_number = re.search(r"(\d+)", path.name)
    lesson_name = f"Transcript {lesson_number.group(1).zfill(2)}" if lesson_number else path.stem

    matches = list(re.finditer(r"\[(T\d{2}-\d{3})\]", content))
    chunks: List[Dict[str, str]] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        segment_text = content[start:end]
        cleaned_text = clean_text(segment_text)

        if not cleaned_text:
            continue

        source_id = f"{match.group(1)}"
        section = infer_section(content, match.start())
        chunks.append(
            {
                "source_id": source_id,
                "lesson": lesson_name,
                "section": section,
                "content": cleaned_text,
            }
        )

    return chunks


def load_chunks(transcript_dir: Path = TRANSCRIPT_DIR) -> List[Dict[str, str]]:
    """Load and normalize all transcript chunks."""
    transcript_files = sorted(transcript_dir.glob("transcript-*-clean.md"))
    all_chunks: List[Dict[str, str]] = []

    for transcript_file in transcript_files:
        all_chunks.extend(parse_transcript_file(transcript_file))

    return all_chunks


def validate_chunks(chunks: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], Dict[str, List[Dict[str, object]]]]:
    """Remove empty or duplicated chunks and report content length warnings."""
    seen: set[str] = set()
    valid_chunks: List[Dict[str, str]] = []
    issues: Dict[str, List[Dict[str, object]]] = {
        "empty": [],
        "duplicate": [],
        "long": [],
    }

    for chunk in chunks:
        content = chunk["content"].strip()
        if not content:
            issues["empty"].append({"source_id": chunk["source_id"], "lesson": chunk["lesson"]})
            continue

        normalized_content = re.sub(r"\s+", " ", content).lower()
        if normalized_content in seen:
            issues["duplicate"].append({"source_id": chunk["source_id"], "lesson": chunk["lesson"]})
            continue

        seen.add(normalized_content)
        if len(content) > MAX_CONTENT_LENGTH:
            issues["long"].append(
                {"source_id": chunk["source_id"], "lesson": chunk["lesson"], "length": len(content)}
            )

        valid_chunks.append(chunk)

    return valid_chunks, issues


def save_chunks(chunks: List[Dict[str, str]], output_path: Path = OUTPUT_PATH) -> Path:
    """Persist the chunk list as JSON for downstream use."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def prepare_data() -> Tuple[List[Dict[str, str]], Dict[str, List[Dict[str, object]]], Path]:
    """Convenience entrypoint for scripts and downstream consumers."""
    chunks = load_chunks()
    valid_chunks, issues = validate_chunks(chunks)
    output_path = save_chunks(valid_chunks)
    return valid_chunks, issues, output_path
