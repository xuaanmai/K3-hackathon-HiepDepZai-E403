"""Mini Quiz generator — produces a multiple-choice quiz only when the
TutorResponse has passed Citation Guard validation.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any, Protocol

from google import genai
from google.genai import types
from pydantic import ValidationError

from src.citation_guard import validate_citations
from src.prompts.quiz_prompt import QUIZ_SYSTEM_PROMPT, format_quiz_input
from src.schemas import Quiz, SourceChunk, TutorResponse


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class QuizGenerationError(RuntimeError):
    """Quiz could not be generated (citation failure or malformed output)."""


# ---------------------------------------------------------------------------
# Gemini client protocol
# ---------------------------------------------------------------------------

class GeminiModelsAPI(Protocol):
    def generate_content(self, **kwargs: Any) -> Any: ...


class GeminiClient(Protocol):
    models: GeminiModelsAPI


DEFAULT_MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _post_validate_quiz(quiz: Quiz, valid_source_ids: set[str]) -> Quiz:
    """Extra runtime checks beyond Pydantic schema validation."""
    # All source_ids in the quiz must come from verified sources.
    unknown = set(quiz.source_ids) - valid_source_ids
    if unknown:
        raise QuizGenerationError(
            "Quiz references source_ids not in verified set: "
            + ", ".join(sorted(unknown))
        )
    return quiz


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_quiz(
    response: TutorResponse,
    sources: Sequence[SourceChunk],
    *,
    client: GeminiClient | None = None,
    model: str | None = None,
) -> Quiz:
    """Generate a Mini Quiz from a **validated** TutorResponse.

    Flow
    ----
    1. Run ``validate_citations`` — reject if invalid.
    2. Filter sources to only verified IDs.
    3. Call Gemini with structured output (Quiz schema).
    4. Post-validate the returned quiz.

    Parameters
    ----------
    response:
        TutorResponse from the Tutor module (Người 3).
    sources:
        The same SourceChunk list that was fed to the Tutor.
    client / model:
        Injectable Gemini client & model name.

    Returns
    -------
    Quiz

    Raises
    ------
    QuizGenerationError
        When citation validation fails, the model returns bad output,
        or the quiz references unknown sources.
    """
    # ── Step 1: Citation Guard gate ──────────────────────────────────────
    validation = validate_citations(response, sources)
    if not validation.is_valid:
        issue_summary = "; ".join(
            f"[{i.source_id}] {i.issue_type}: {i.detail}"
            for i in validation.issues
        )
        raise QuizGenerationError(
            f"Citation validation failed — quiz not generated. Issues: {issue_summary}"
        )

    # Non-answer decisions produce no quiz.
    if response.decision != "answer":
        raise QuizGenerationError(
            f"Cannot generate quiz for decision='{response.decision}' "
            "(only 'answer' responses produce quizzes)."
        )

    # ── Step 2: Filter to verified sources only ──────────────────────────
    verified_ids = set(validation.verified_source_ids)
    source_map = {s.source_id: s for s in sources}
    verified_sources = [source_map[sid] for sid in validation.verified_source_ids if sid in source_map]

    if not verified_sources:
        raise QuizGenerationError("No verified sources available to generate quiz.")

    # ── Step 3: Call Gemini ──────────────────────────────────────────────
    if client is None:
        if not os.getenv("GEMINI_API_KEY"):
            raise QuizGenerationError(
                "GEMINI_API_KEY is not configured. Set it in the environment."
            )
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    selected_model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    try:
        api_response = client.models.generate_content(
            model=selected_model,
            contents=format_quiz_input(response, verified_sources),
            config=types.GenerateContentConfig(
                system_instruction=QUIZ_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=Quiz,
                temperature=0.3,
            ),
        )
    except Exception as exc:
        raise QuizGenerationError(f"Gemini request failed: {exc}") from exc

    response_text = getattr(api_response, "text", None)
    if not response_text:
        raise QuizGenerationError(
            "Gemini response did not contain structured text output."
        )

    # ── Step 4: Parse & post-validate ────────────────────────────────────
    try:
        quiz = Quiz.model_validate_json(response_text)
    except (ValidationError, ValueError) as exc:
        raise QuizGenerationError(
            f"Invalid structured Quiz response: {exc}"
        ) from exc

    return _post_validate_quiz(quiz, verified_ids)
