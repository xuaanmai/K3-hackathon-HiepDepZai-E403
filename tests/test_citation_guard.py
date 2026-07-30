"""Tests for the Citation Guard module — all use mock data, no API key needed."""

import pytest

from src.schemas import CitationIssue, SourceChunk, TutorResponse, ValidationResult
from src.citation_guard import validate_citations, _extract_inline_ids


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MOCK_SOURCES = [
    SourceChunk(
        source_id="T01-S03",
        lesson="Transcript 01",
        section="RAG",
        content="RAG truy xuất đoạn tài liệu liên quan trước khi tạo câu trả lời.",
        score=0.91,
    ),
    SourceChunk(
        source_id="T01-S04",
        lesson="Transcript 01",
        section="Chunking",
        content="Chunking chia tài liệu thành các đoạn nhỏ để truy xuất hiệu quả.",
        score=0.85,
    ),
]


def _make_answer_response(
    answer: str,
    citations: list[str],
    **overrides,
) -> TutorResponse:
    """Helper to build a valid answer-type TutorResponse."""
    defaults = dict(
        decision="answer",
        answer=answer,
        citations=citations,
        clarification=None,
        reason="Test response.",
    )
    defaults.update(overrides)
    return TutorResponse(**defaults)


# ---------------------------------------------------------------------------
# _extract_inline_ids
# ---------------------------------------------------------------------------


class TestExtractInlineIds:
    def test_single_id(self):
        assert _extract_inline_ids("Nội dung [T01-S03] ở đây.") == {"T01-S03"}

    def test_multiple_ids(self):
        assert _extract_inline_ids("[T01-S03] và [T01-S04].") == {
            "T01-S03",
            "T01-S04",
        }

    def test_no_ids(self):
        assert _extract_inline_ids("Không có citation nào.") == set()


# ---------------------------------------------------------------------------
# validate_citations — non-answer decisions
# ---------------------------------------------------------------------------


class TestNonAnswerDecisions:
    def test_clarify_auto_passes(self):
        response = TutorResponse(
            decision="clarify",
            answer=None,
            citations=[],
            clarification="Bạn muốn hỏi phần nào?",
            reason="Mơ hồ.",
        )
        result = validate_citations(response, MOCK_SOURCES)
        assert result.is_valid is True
        assert result.issues == []

    def test_not_found_auto_passes(self):
        response = TutorResponse(
            decision="not_found",
            answer=None,
            citations=[],
            clarification=None,
            reason="Không tìm thấy.",
        )
        result = validate_citations(response, MOCK_SOURCES)
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_citations — happy path
# ---------------------------------------------------------------------------


class TestValidCitations:
    def test_single_valid_citation(self):
        response = _make_answer_response(
            answer="RAG truy xuất tài liệu trước khi trả lời [T01-S03].",
            citations=["T01-S03"],
        )
        result = validate_citations(response, MOCK_SOURCES)
        assert result.is_valid is True
        assert result.verified_source_ids == ["T01-S03"]
        assert result.issues == []

    def test_multiple_valid_citations(self):
        response = _make_answer_response(
            answer="RAG [T01-S03] kết hợp chunking [T01-S04] hiệu quả.",
            citations=["T01-S03", "T01-S04"],
        )
        result = validate_citations(response, MOCK_SOURCES)
        assert result.is_valid is True
        assert set(result.verified_source_ids) == {"T01-S03", "T01-S04"}


# ---------------------------------------------------------------------------
# validate_citations — fabricated citations
# ---------------------------------------------------------------------------


class TestFabricatedCitations:
    def test_citation_not_in_sources(self):
        response = _make_answer_response(
            answer="Nội dung bịa [FAKE-01].",
            citations=["FAKE-01"],
        )
        result = validate_citations(response, MOCK_SOURCES)
        assert result.is_valid is False
        assert len(result.issues) == 1
        assert result.issues[0].issue_type == "fabricated"
        assert result.issues[0].source_id == "FAKE-01"

    def test_mix_valid_and_fabricated(self):
        response = _make_answer_response(
            answer="Có [T01-S03] và bịa [FAKE-99].",
            citations=["T01-S03", "FAKE-99"],
        )
        result = validate_citations(response, MOCK_SOURCES)
        assert result.is_valid is False
        fabricated = [i for i in result.issues if i.issue_type == "fabricated"]
        assert len(fabricated) == 1
        assert fabricated[0].source_id == "FAKE-99"


# ---------------------------------------------------------------------------
# validate_citations — missing inline citations
# ---------------------------------------------------------------------------


class TestMissingInlineCitations:
    def test_citation_declared_but_not_inline(self):
        response = _make_answer_response(
            answer="RAG truy xuất tài liệu trước khi trả lời.",
            citations=["T01-S03"],
        )
        result = validate_citations(response, MOCK_SOURCES)
        assert result.is_valid is False
        missing = [i for i in result.issues if i.issue_type == "missing"]
        assert len(missing) == 1
        assert missing[0].source_id == "T01-S03"


# ---------------------------------------------------------------------------
# validate_citations — undeclared inline citations
# ---------------------------------------------------------------------------


class TestUndeclaredInlineCitations:
    def test_inline_present_but_not_declared(self):
        """A source ID appears inline but wasn't listed in response.citations."""
        response = _make_answer_response(
            answer="RAG [T01-S03] kết hợp chunking [T01-S04] hiệu quả.",
            citations=["T01-S03"],
        )
        result = validate_citations(response, MOCK_SOURCES)
        assert result.is_valid is False
        undeclared = [
            i
            for i in result.issues
            if i.source_id == "T01-S04" and i.issue_type == "missing"
        ]
        assert len(undeclared) == 1


# ---------------------------------------------------------------------------
# ValidationResult schema invariants
# ---------------------------------------------------------------------------


class TestValidationResultSchema:
    def test_valid_true_with_issues_raises(self):
        with pytest.raises(ValueError, match="is_valid=True but issues"):
            ValidationResult(
                is_valid=True,
                issues=[
                    CitationIssue(
                        source_id="X",
                        issue_type="fabricated",
                        detail="test",
                    )
                ],
                verified_source_ids=[],
                response=TutorResponse(
                    decision="not_found",
                    reason="test",
                ),
            )

    def test_valid_false_without_issues_raises(self):
        with pytest.raises(ValueError, match="is_valid=False but no issues"):
            ValidationResult(
                is_valid=False,
                issues=[],
                verified_source_ids=[],
                response=TutorResponse(
                    decision="not_found",
                    reason="test",
                ),
            )
