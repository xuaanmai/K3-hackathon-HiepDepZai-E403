"""Grounded Tutor decision module backed by the Gemini API."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from google import genai
from google.genai import types
from pydantic import ValidationError

from src.prompts.tutor_prompt import TUTOR_SYSTEM_PROMPT, format_tutor_input
from src.schemas import SourceChunk, TutorResponse


DEFAULT_MODEL = "gemini-2.5-flash"


class TutorError(RuntimeError):
    """Base error raised by the Tutor module."""


class TutorConfigurationError(TutorError):
    """The Tutor is missing required configuration."""


class TutorOutputError(TutorError):
    """The model response is missing, malformed, or violates grounding rules."""


class GeminiModelsAPI(Protocol):
    def generate_content(self, **kwargs: Any) -> Any: ...


class GeminiClient(Protocol):
    models: GeminiModelsAPI


def _normalize_sources(
    sources: Sequence[SourceChunk | Mapping[str, Any]],
) -> list[SourceChunk]:
    normalized = [
        source if isinstance(source, SourceChunk) else SourceChunk.model_validate(source)
        for source in sources
    ]
    source_ids = [source.source_id for source in normalized]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("retrieved sources must have unique source_id values")
    return normalized


def _safe_no_sources_response() -> TutorResponse:
    return TutorResponse(
        decision="not_found",
        answer=None,
        citations=[],
        clarification=None,
        reason="Không có đoạn transcript nào được truy xuất.",
        corrected_premise=None,
    )


def _validate_grounding(
    response: TutorResponse,
    sources: Sequence[SourceChunk],
) -> TutorResponse:
    valid_source_ids = {source.source_id for source in sources}
    unknown = set(response.citations) - valid_source_ids
    if unknown:
        raise TutorOutputError(
            "Model returned citations that were not supplied: "
            + ", ".join(sorted(unknown))
        )

    if response.decision == "answer":
        missing_inline = [
            source_id
            for source_id in response.citations
            if f"[{source_id}]" not in (response.answer or "")
        ]
        if missing_inline:
            # The model occasionally returns valid `citations` in structured
            # output but forgets to repeat them inside `answer`. Unknown IDs
            # were already rejected above, so appending the verified IDs is a
            # safe formatting repair rather than inventing a source.
            citation_suffix = " ".join(
                f"[{source_id}]" for source_id in missing_inline
            )
            response = response.model_copy(
                update={
                    "answer": f"{(response.answer or '').rstrip()} {citation_suffix}"
                }
            )

    return response


def answer_question(
    question: str,
    sources: Sequence[SourceChunk | Mapping[str, Any]],
    *,
    history: Sequence[Mapping[str, str]] = (),
    client: GeminiClient | None = None,
    model: str | None = None,
) -> TutorResponse:
    """Choose answer/clarify/not_found and return a grounded Tutor response.

    `client` is injectable so unit tests can run without network calls.
    """
    cleaned_question = question.strip()
    if not cleaned_question:
        return TutorResponse(
            decision="clarify",
            answer=None,
            citations=[],
            clarification="Bạn muốn hỏi điều gì trong phần bài học này?",
            reason="Câu hỏi đang để trống.",
            corrected_premise=None,
        )

    normalized_sources = _normalize_sources(sources)
    if not normalized_sources:
        return _safe_no_sources_response()

    if client is None:
        if not os.getenv("GEMINI_API_KEY"):
            raise TutorConfigurationError(
                "GEMINI_API_KEY is not configured. Set it in the environment before calling the Tutor."
            )
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    selected_model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    try:
        api_response = client.models.generate_content(
            model=selected_model,
            contents=format_tutor_input(
                cleaned_question,
                normalized_sources,
                history=history,
            ),
            config=types.GenerateContentConfig(
                system_instruction=TUTOR_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_json_schema=TutorResponse.model_json_schema(),
                temperature=0.1,
            ),
        )
    except (ValidationError, ValueError) as exc:
        raise TutorOutputError(f"Invalid structured Tutor response: {exc}") from exc
    except Exception as exc:
        raise TutorError(f"Gemini request failed: {exc}") from exc

    response_text = getattr(api_response, "text", None)
    if not response_text:
        raise TutorOutputError("Gemini response did not contain structured text output")

    try:
        response = TutorResponse.model_validate_json(response_text)
    except (ValidationError, ValueError) as exc:
        raise TutorOutputError(f"Invalid structured Tutor response: {exc}") from exc

    if (
        response.decision == "answer"
        and response.corrected_premise is None
        and re.search(r"\b(đúng không|phải không)\s*\??$", cleaned_question, re.IGNORECASE)
        and re.match(r"^\s*(không|chưa đúng)", response.answer or "", re.IGNORECASE)
    ):
        first_sentence = re.split(r"(?<=[.!?])\s+", response.answer or "", maxsplit=1)[0]
        response = response.model_copy(update={"corrected_premise": first_sentence})

    return _validate_grounding(response, normalized_sources)
