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


# ---------------------------------------------------------------------------
# Citation Guard schemas
# ---------------------------------------------------------------------------

IssueType = Literal["missing", "fabricated", "unsupported"]


class CitationIssue(BaseModel):
    """A single problem detected during citation validation."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    issue_type: IssueType
    detail: str = Field(min_length=1)


class ValidationResult(BaseModel):
    """Aggregate result of citation validation for one TutorResponse."""

    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    issues: list[CitationIssue] = Field(default_factory=list)
    verified_source_ids: list[str] = Field(default_factory=list)
    response: TutorResponse

    @model_validator(mode="after")
    def consistency_check(self) -> "ValidationResult":
        if self.is_valid and self.issues:
            raise ValueError("is_valid=True but issues list is not empty")
        if not self.is_valid and not self.issues:
            raise ValueError("is_valid=False but no issues were recorded")
        return self


# ---------------------------------------------------------------------------
# Mini Quiz schemas
# ---------------------------------------------------------------------------


class QuizOption(BaseModel):
    """One selectable choice in a quiz question."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, description="A, B, C, or D")
    text: str = Field(min_length=1)


class Quiz(BaseModel):
    """A single multiple-choice quiz question derived from verified sources."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    options: list[QuizOption] = Field(min_length=3, max_length=4)
    correct_label: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_quiz_integrity(self) -> "Quiz":
        labels = {opt.label for opt in self.options}

        if len(labels) != len(self.options):
            raise ValueError("Quiz option labels must be unique")

        if self.correct_label not in labels:
            raise ValueError(
                f"correct_label '{self.correct_label}' does not match any option label"
            )

        return self

