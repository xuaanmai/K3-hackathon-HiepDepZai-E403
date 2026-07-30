"""Shared data contracts between retrieval, Tutor, citation guard, and UI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Decision = Literal["answer", "clarify", "not_found"]


class SourceChunk(BaseModel):
    """A transcript passage returned by the retrieval module."""

    model_config = ConfigDict(extra="ignore")

    source_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    lesson: str = ""
    section: str = ""
    score: float | None = None


class TutorResponse(BaseModel):
    """Structured decision and grounded response produced by the Tutor."""

    model_config = ConfigDict(extra="forbid")

    decision: Decision
    answer: str | None = None
    citations: list[str] = Field(default_factory=list)
    clarification: str | None = None
    reason: str = Field(
        min_length=1,
        description="Short internal explanation of why this decision was chosen.",
    )
    corrected_premise: str | None = Field(
        default=None,
        description="Correction when the learner's question contains a false premise.",
    )

    @model_validator(mode="after")
    def validate_decision_contract(self) -> "TutorResponse":
        if len(self.citations) != len(set(self.citations)):
            raise ValueError("citations must not contain duplicates")

        if self.decision == "answer":
            if not self.answer or not self.answer.strip():
                raise ValueError("answer is required when decision='answer'")
            if not self.citations:
                raise ValueError("at least one citation is required when decision='answer'")
            if self.clarification is not None:
                raise ValueError("clarification must be null when decision='answer'")

        elif self.decision == "clarify":
            if not self.clarification or not self.clarification.strip():
                raise ValueError("clarification is required when decision='clarify'")
            if self.answer is not None or self.citations:
                raise ValueError("clarify must not include an answer or citations")

        elif self.decision == "not_found":
            if self.answer is not None or self.citations or self.clarification is not None:
                raise ValueError("not_found must not include answer, citations, or clarification")

        return self

