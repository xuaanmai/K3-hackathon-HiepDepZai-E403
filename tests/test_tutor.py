import json
from types import SimpleNamespace

import pytest

from src.schemas import TutorResponse
from src.tutor import TutorOutputError, answer_question


SOURCES = [
    {
        "source_id": "T01-S03",
        "lesson": "Transcript 01",
        "section": "RAG",
        "content": "RAG truy xuất đoạn tài liệu liên quan trước khi tạo câu trả lời.",
        "score": 0.91,
    }
]


class FakeModels:
    def __init__(self, parsed):
        self.parsed = parsed
        self.last_request = None

    def generate_content(self, **kwargs):
        self.last_request = kwargs
        if self.parsed is None:
            return SimpleNamespace(text=None)
        payload = (
            self.parsed.model_dump(mode="json")
            if isinstance(self.parsed, TutorResponse)
            else self.parsed
        )
        return SimpleNamespace(text=json.dumps(payload, ensure_ascii=False))


class FakeClient:
    def __init__(self, parsed):
        self.models = FakeModels(parsed)


def test_answer_branch_accepts_valid_inline_citation():
    expected = TutorResponse(
        decision="answer",
        answer="RAG truy xuất tài liệu trước khi trả lời [T01-S03].",
        citations=["T01-S03"],
        clarification=None,
        reason="Nguồn trực tiếp trả lời câu hỏi.",
    )
    client = FakeClient(expected)

    result = answer_question("RAG hoạt động thế nào?", SOURCES, client=client)

    assert result == expected
    request = client.models.last_request
    assert request["config"].response_schema is TutorResponse
    assert request["config"].response_mime_type == "application/json"
    assert "T01-S03" in request["contents"]


def test_clarify_branch():
    expected = TutorResponse(
        decision="clarify",
        answer=None,
        citations=[],
        clarification="Bạn muốn hỏi về bước Retrieve hay Generate?",
        reason="Câu hỏi có nhiều cách hiểu.",
    )
    result = answer_question("Giải thích đoạn này", SOURCES, client=FakeClient(expected))
    assert result.decision == "clarify"
    assert result.clarification


def test_no_sources_returns_not_found_without_api_call():
    result = answer_question("RAG hoạt động thế nào?", [], client=FakeClient(None))
    assert result.decision == "not_found"
    assert result.answer is None


def test_empty_question_returns_clarification_without_api_call():
    result = answer_question("  ", SOURCES, client=FakeClient(None))
    assert result.decision == "clarify"


def test_unknown_citation_is_rejected():
    response = TutorResponse(
        decision="answer",
        answer="Nội dung không có nguồn [FAKE-01].",
        citations=["FAKE-01"],
        clarification=None,
        reason="Sai citation.",
    )
    with pytest.raises(TutorOutputError, match="not supplied"):
        answer_question("Câu hỏi", SOURCES, client=FakeClient(response))


def test_missing_inline_citation_is_rejected():
    response = TutorResponse(
        decision="answer",
        answer="RAG truy xuất tài liệu trước khi trả lời.",
        citations=["T01-S03"],
        clarification=None,
        reason="Có nguồn nhưng chưa chèn citation.",
    )
    with pytest.raises(TutorOutputError, match="missing inline"):
        answer_question("Câu hỏi", SOURCES, client=FakeClient(response))


def test_schema_rejects_answer_without_citation():
    with pytest.raises(ValueError):
        TutorResponse(
            decision="answer",
            answer="Câu trả lời không có nguồn.",
            citations=[],
            clarification=None,
            reason="Thiếu nguồn.",
        )
