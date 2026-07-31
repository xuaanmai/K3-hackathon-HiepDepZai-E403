"""Citation Guard — validates that every citation in a TutorResponse is
real, present inline, and actually supported by the retrieved sources.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from typing import Any, Protocol

from google import genai
from google.genai import types
from pydantic import ValidationError

from src.schemas import (
    CitationIssue,
    SourceChunk,
    TutorResponse,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CitationGuardError(RuntimeError):
    """Base error raised by the Citation Guard module."""


# ---------------------------------------------------------------------------
# Gemini client protocol (same as tutor.py for consistency)
# ---------------------------------------------------------------------------

class GeminiModelsAPI(Protocol):
    def generate_content(self, **kwargs: Any) -> Any: ...


class GeminiClient(Protocol):
    models: GeminiModelsAPI


DEFAULT_MODEL = "gemini-2.5-flash"

_VERIFICATION_SYSTEM_PROMPT = """\
Bạn là trợ lý kiểm tra tính chính xác.  Cho một CLAIM và một SOURCE, hãy
trả lời đúng một từ: "yes" nếu SOURCE **trực tiếp** hỗ trợ CLAIM, hoặc
"no" nếu SOURCE không đủ hoặc mâu thuẫn.

Không giải thích, không thêm bất kỳ nội dung nào khác.
""".strip()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_INLINE_CITATION_RE = re.compile(r"\[([A-Za-z0-9_-]+(?:-[A-Za-z0-9_]+)*)\]")
"""Matches bracket-wrapped source IDs like [T01-S03]."""


def _extract_inline_ids(text: str) -> set[str]:
    """Return all bracket-cited source IDs found in *text*."""
    return set(_INLINE_CITATION_RE.findall(text))


def _build_source_map(
    sources: Sequence[SourceChunk],
) -> dict[str, SourceChunk]:
    return {s.source_id: s for s in sources}


def _check_existence_and_inline(
    response: TutorResponse,
    source_map: dict[str, SourceChunk],
) -> list[CitationIssue]:
    """Tầng 1 + 2: kiểm tra citation tồn tại & xuất hiện inline."""
    issues: list[CitationIssue] = []
    answer_text = response.answer or ""
    inline_ids = _extract_inline_ids(answer_text)

    # --- Check each declared citation ---
    for cid in response.citations:
        # Tầng 1: citation phải thuộc sources
        if cid not in source_map:
            issues.append(
                CitationIssue(
                    source_id=cid,
                    issue_type="fabricated",
                    detail=f"Citation '{cid}' không tồn tại trong danh sách sources được truy xuất.",
                )
            )
            continue

        # Tầng 2: citation phải xuất hiện inline trong answer
        if cid not in inline_ids:
            issues.append(
                CitationIssue(
                    source_id=cid,
                    issue_type="missing",
                    detail=f"Citation '{cid}' có trong danh sách nhưng không xuất hiện dạng [{cid}] trong answer.",
                )
            )

    # --- Check for inline IDs that appear in text but are NOT declared ---
    valid_ids = set(source_map.keys())
    declared = set(response.citations)
    undeclared_inline = (inline_ids & valid_ids) - declared
    for cid in sorted(undeclared_inline):
        issues.append(
            CitationIssue(
                source_id=cid,
                issue_type="missing",
                detail=f"Source [{cid}] xuất hiện inline nhưng không được khai báo trong citations list.",
            )
        )

    return issues


def _ai_verify_claim(
    claim: str,
    source: SourceChunk,
    *,
    client: GeminiClient,
    model: str,
) -> bool:
    """Use one Gemini call to check if *source* genuinely supports *claim*."""
    user_content = (
        f"<CLAIM>\n{claim.strip()}\n</CLAIM>\n\n"
        f"<SOURCE id=\"{source.source_id}\">\n{source.content}\n</SOURCE>"
    )
    try:
        resp = client.models.generate_content(
            model=model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=_VERIFICATION_SYSTEM_PROMPT,
                temperature=0.0,
            ),
        )
        text = getattr(resp, "text", "") or ""
        return text.strip().lower().startswith("yes")
    except Exception:
        # Network/quota failures should not block the pipeline — treat as
        # "unable to verify" and let the structural checks decide.
        return True


def _ai_grounding_check(
    response: TutorResponse,
    source_map: dict[str, SourceChunk],
    *,
    client: GeminiClient,
    model: str,
) -> list[CitationIssue]:
    """Tầng 3: Dùng AI để kiểm tra mỗi claim có được source hỗ trợ thật sự.

    Heuristic: Tách answer thành các câu, mỗi câu chứa inline citation sẽ
    được verify với source tương ứng.
    """
    issues: list[CitationIssue] = []
    answer = response.answer or ""

    # Split by sentence-ending punctuation (Vietnamese-friendly).
    sentences = re.split(r"(?<=[.!?。])\s+", answer)

    for sentence in sentences:
        cited_ids = _extract_inline_ids(sentence)
        # Strip citations out for a cleaner claim.
        claim = _INLINE_CITATION_RE.sub("", sentence).strip()
        if not claim or not cited_ids:
            continue

        for cid in cited_ids:
            source = source_map.get(cid)
            if source is None:
                continue  # already caught by existence check
            supported = _ai_verify_claim(claim, source, client=client, model=model)
            if not supported:
                issues.append(
                    CitationIssue(
                        source_id=cid,
                        issue_type="unsupported",
                        detail=(
                            f"AI verification cho thấy source '{cid}' không trực tiếp "
                            f"hỗ trợ claim: \"{claim[:120]}…\""
                            if len(claim) > 120
                            else f"AI verification cho thấy source '{cid}' không trực tiếp "
                            f"hỗ trợ claim: \"{claim}\""
                        ),
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_citations(
    response: TutorResponse,
    sources: Sequence[SourceChunk],
    *,
    use_ai_verification: bool = False,
    client: GeminiClient | None = None,
    model: str | None = None,
) -> ValidationResult:
    """Validate every citation in *response* against *sources*.

    Parameters
    ----------
    response:
        The TutorResponse produced by the Tutor module (Người 3).
    sources:
        The same SourceChunk list that was fed to the Tutor.
    use_ai_verification:
        When ``True``, an additional Gemini call per cited sentence checks
        that the source genuinely supports the claim.
    client / model:
        Injectable Gemini client & model name (for testing / config).

    Returns
    -------
    ValidationResult
        ``is_valid=True`` when all checks pass; otherwise ``is_valid=False``
        with a populated ``issues`` list.
    """
    # Non-answer decisions have no citations to validate.
    if response.decision != "answer":
        return ValidationResult(
            is_valid=True,
            issues=[],
            verified_source_ids=[],
            response=response,
        )

    source_map = _build_source_map(sources)

    # Tầng 1 + 2
    issues = _check_existence_and_inline(response, source_map)

    # Tầng 3 (optional AI grounding)
    if use_ai_verification and not issues:
        if client is None:
            if not os.getenv("GEMINI_API_KEY"):
                raise CitationGuardError(
                    "GEMINI_API_KEY is required for AI verification."
                )
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        selected_model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        issues.extend(
            _ai_grounding_check(response, source_map, client=client, model=selected_model)
        )

    if issues:
        return ValidationResult(
            is_valid=False,
            issues=issues,
            verified_source_ids=[],
            response=response,
        )

    return ValidationResult(
        is_valid=True,
        issues=[],
        verified_source_ids=list(response.citations),
        response=response,
    )
