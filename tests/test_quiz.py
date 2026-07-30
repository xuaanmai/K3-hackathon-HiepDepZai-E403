"""Tests for the Mini Quiz generator — all use mock Gemini client."""

import json
from types import SimpleNamespace

import pytest

from src.schemas import Quiz, QuizOption, QuizSet, SourceChunk, TutorResponse
from src.quiz import (
    QuizGenerationError,
    generate_lesson_quiz,
    generate_quiz,
    grade_quiz,
)


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

VALID_QUIZ = Quiz(
    question="Điều nào mô tả đúng nhất vai trò của RAG?",
    options=[
        QuizOption(label="A", text="Huấn luyện lại mô hình sau mỗi câu hỏi"),
        QuizOption(label="B", text="Truy xuất tài liệu liên quan trước khi tạo câu trả lời"),
        QuizOption(label="C", text="Đảm bảo mọi câu trả lời đều chính xác"),
    ],
    correct_label="B",
    explanation="RAG truy xuất đoạn tài liệu liên quan trước khi tạo câu trả lời [T01-S03].",
    source_ids=["T01-S03"],
)


def _make_answer_response(
    answer: str = "RAG truy xuất tài liệu trước khi trả lời [T01-S03].",
    citations: list[str] | None = None,
) -> TutorResponse:
    return TutorResponse(
        decision="answer",
        answer=answer,
        citations=citations or ["T01-S03"],
        clarification=None,
        reason="Test response.",
    )


# ---------------------------------------------------------------------------
# Fake Gemini client (reuses pattern from test_tutor.py)
# ---------------------------------------------------------------------------


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
            if hasattr(self.parsed, "model_dump")
            else self.parsed
        )
        return SimpleNamespace(text=json.dumps(payload, ensure_ascii=False))


class FakeClient:
    def __init__(self, parsed):
        self.models = FakeModels(parsed)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestQuizGeneration:
    def test_valid_quiz_generated(self):
        response = _make_answer_response()
        client = FakeClient(VALID_QUIZ)
        quiz = generate_quiz(response, MOCK_SOURCES, client=client)

        assert quiz.question == VALID_QUIZ.question
        assert quiz.correct_label == "B"
        assert len(quiz.options) == 3
        assert quiz.source_ids == ["T01-S03"]

    def test_request_uses_quiz_schema(self):
        response = _make_answer_response()
        client = FakeClient(VALID_QUIZ)
        generate_quiz(response, MOCK_SOURCES, client=client)

        request = client.models.last_request
        assert request["config"].response_json_schema == Quiz.model_json_schema()
        assert request["config"].response_mime_type == "application/json"

    def test_verified_sources_only_in_prompt(self):
        response = _make_answer_response()
        client = FakeClient(VALID_QUIZ)
        generate_quiz(response, MOCK_SOURCES, client=client)

        contents = client.models.last_request["contents"]
        assert "T01-S03" in contents
        # T01-S04 is not cited, so should NOT appear in prompt
        assert "T01-S04" not in contents


class TestLessonQuizGeneration:
    def test_generates_requested_lesson_quiz_set(self):
        questions = [
            Quiz(
                question=f"Câu tổng hợp số {index + 1}?",
                options=[
                    QuizOption(label="A", text="Đáp án đúng"),
                    QuizOption(label="B", text="Đáp án nhiễu 1"),
                    QuizOption(label="C", text="Đáp án nhiễu 2"),
                    QuizOption(label="D", text="Đáp án nhiễu 3"),
                ],
                correct_label="A",
                explanation="Dựa trên nội dung bài học.",
                source_ids=["T01-S03"],
            )
            for index in range(10)
        ]
        expected = QuizSet(title="Quiz tổng hợp", questions=questions)
        client = FakeClient(expected)

        result = generate_lesson_quiz(MOCK_SOURCES, 10, client=client)

        assert len(result.questions) == 10
        config = client.models.last_request["config"]
        assert config.response_json_schema is None
        assert config.response_mime_type == "application/json"
        assert "<QUESTION_COUNT>10</QUESTION_COUNT>" in (
            client.models.last_request["contents"]
        )
        assert "T01-S03" in client.models.last_request["contents"]
        assert "T01-S04" in client.models.last_request["contents"]

    def test_rejects_unsupported_question_count(self):
        with pytest.raises(QuizGenerationError, match="10, 20, or 30"):
            generate_lesson_quiz(MOCK_SOURCES, 15, client=FakeClient(None))

    def test_accepts_direct_question_array_from_gemini(self):
        questions = [
            Quiz(
                question=f"Câu tổng hợp trực tiếp {index + 1}?",
                options=[
                    QuizOption(label="A", text="Đúng"),
                    QuizOption(label="B", text="Sai 1"),
                    QuizOption(label="C", text="Sai 2"),
                    QuizOption(label="D", text="Sai 3"),
                ],
                correct_label="A",
                explanation="Dựa trên nguồn.",
                source_ids=["T01-S03"],
            ).model_dump(mode="json")
            for index in range(10)
        ]

        result = generate_lesson_quiz(
            MOCK_SOURCES,
            10,
            client=FakeClient(questions),
        )

        assert result.title == "Quiz tổng hợp buổi học"
        assert len(result.questions) == 10

    def test_normalizes_option_map_and_answer_field(self):
        questions = [
            {
                "question": f"Câu theo định dạng Gemini {index + 1}?",
                "options": {
                    "A": "Đúng",
                    "B": "Sai 1",
                    "C": "Sai 2",
                    "D": "Sai 3",
                },
                "answer": "A",
                "explanation": "Dựa trên nguồn.",
                "source_ids": ["T01-S03"],
            }
            for index in range(10)
        ]

        result = generate_lesson_quiz(
            MOCK_SOURCES,
            10,
            client=FakeClient(questions),
        )

        assert result.questions[0].correct_label == "A"
        assert [item.label for item in result.questions[0].options] == [
            "A",
            "B",
            "C",
            "D",
        ]

    def test_rejects_unknown_lesson_source(self):
        question = Quiz(
            question="Câu hỏi có nguồn giả?",
            options=[
                QuizOption(label="A", text="A"),
                QuizOption(label="B", text="B"),
                QuizOption(label="C", text="C"),
                QuizOption(label="D", text="D"),
            ],
            correct_label="A",
            explanation="Giải thích.",
            source_ids=["UNKNOWN"],
        )
        quiz_set = QuizSet(
            title="Quiz tổng hợp",
            questions=[
                question.model_copy(update={"question": f"Câu {index + 1}?"})
                for index in range(10)
            ],
        )
        with pytest.raises(QuizGenerationError, match="not in verified set"):
            generate_lesson_quiz(MOCK_SOURCES, 10, client=FakeClient(quiz_set))


class TestQuizGrading:
    def test_blank_answers_are_reported_and_counted_wrong(self):
        quiz_set = QuizSet(
            title="Bài kiểm tra",
            questions=[
                VALID_QUIZ.model_copy(update={"question": f"Câu {index + 1}?"})
                for index in range(3)
            ],
        )

        score, unanswered = grade_quiz(quiz_set, ["B", None, "A"])

        assert score == 1
        assert unanswered == [2]

    def test_answer_count_must_match_questions(self):
        quiz_set = QuizSet(title="Bài kiểm tra", questions=[VALID_QUIZ])
        with pytest.raises(ValueError, match="answers length"):
            grade_quiz(quiz_set, [])


# ---------------------------------------------------------------------------
# Citation validation gate
# ---------------------------------------------------------------------------


class TestCitationGate:
    def test_fabricated_citation_blocks_quiz(self):
        response = _make_answer_response(
            answer="Nội dung bịa [FAKE-01].",
            citations=["FAKE-01"],
        )
        with pytest.raises(QuizGenerationError, match="Citation validation failed"):
            generate_quiz(response, MOCK_SOURCES, client=FakeClient(None))

    def test_missing_inline_blocks_quiz(self):
        response = _make_answer_response(
            answer="RAG truy xuất tài liệu trước khi trả lời.",
            citations=["T01-S03"],
        )
        with pytest.raises(QuizGenerationError, match="Citation validation failed"):
            generate_quiz(response, MOCK_SOURCES, client=FakeClient(None))

    def test_non_answer_decision_blocks_quiz(self):
        response = TutorResponse(
            decision="clarify",
            answer=None,
            citations=[],
            clarification="Bạn muốn hỏi phần nào?",
            reason="Mơ hồ.",
        )
        with pytest.raises(QuizGenerationError, match="decision='clarify'"):
            generate_quiz(response, MOCK_SOURCES, client=FakeClient(None))

    def test_not_found_decision_blocks_quiz(self):
        response = TutorResponse(
            decision="not_found",
            answer=None,
            citations=[],
            clarification=None,
            reason="Không tìm thấy.",
        )
        with pytest.raises(QuizGenerationError, match="decision='not_found'"):
            generate_quiz(response, MOCK_SOURCES, client=FakeClient(None))


# ---------------------------------------------------------------------------
# Quiz post-validation
# ---------------------------------------------------------------------------


class TestQuizPostValidation:
    def test_quiz_with_unknown_source_ids_rejected(self):
        """Quiz references a source_id not in the verified set."""
        bad_quiz = Quiz(
            question="Câu hỏi?",
            options=[
                QuizOption(label="A", text="Lựa chọn A"),
                QuizOption(label="B", text="Lựa chọn B"),
                QuizOption(label="C", text="Lựa chọn C"),
            ],
            correct_label="A",
            explanation="Giải thích.",
            source_ids=["T01-S03", "UNKNOWN-99"],
        )
        response = _make_answer_response()
        with pytest.raises(QuizGenerationError, match="not in verified set"):
            generate_quiz(response, MOCK_SOURCES, client=FakeClient(bad_quiz))

    def test_gemini_returns_empty_text_raises(self):
        response = _make_answer_response()
        with pytest.raises(QuizGenerationError, match="did not contain"):
            generate_quiz(response, MOCK_SOURCES, client=FakeClient(None))


# ---------------------------------------------------------------------------
# Quiz schema validation (Pydantic level)
# ---------------------------------------------------------------------------


class TestQuizSchema:
    def test_too_few_options_rejected(self):
        with pytest.raises(ValueError):
            Quiz(
                question="Câu hỏi?",
                options=[
                    QuizOption(label="A", text="Chỉ có 1"),
                    QuizOption(label="B", text="Chỉ có 2"),
                ],
                correct_label="A",
                explanation="Giải thích.",
                source_ids=["T01-S03"],
            )

    def test_too_many_options_rejected(self):
        with pytest.raises(ValueError):
            Quiz(
                question="Câu hỏi?",
                options=[
                    QuizOption(label="A", text="A"),
                    QuizOption(label="B", text="B"),
                    QuizOption(label="C", text="C"),
                    QuizOption(label="D", text="D"),
                    QuizOption(label="E", text="E"),
                ],
                correct_label="A",
                explanation="Giải thích.",
                source_ids=["T01-S03"],
            )

    def test_correct_label_must_match_option(self):
        with pytest.raises(ValueError, match="does not match"):
            Quiz(
                question="Câu hỏi?",
                options=[
                    QuizOption(label="A", text="A"),
                    QuizOption(label="B", text="B"),
                    QuizOption(label="C", text="C"),
                ],
                correct_label="Z",
                explanation="Giải thích.",
                source_ids=["T01-S03"],
            )

    def test_duplicate_labels_rejected(self):
        with pytest.raises(ValueError, match="labels must be unique"):
            Quiz(
                question="Câu hỏi?",
                options=[
                    QuizOption(label="A", text="Opt 1"),
                    QuizOption(label="A", text="Opt 2"),
                    QuizOption(label="B", text="Opt 3"),
                ],
                correct_label="A",
                explanation="Giải thích.",
                source_ids=["T01-S03"],
            )

    def test_valid_4_options_quiz(self):
        quiz = Quiz(
            question="Câu hỏi?",
            options=[
                QuizOption(label="A", text="A"),
                QuizOption(label="B", text="B"),
                QuizOption(label="C", text="C"),
                QuizOption(label="D", text="D"),
            ],
            correct_label="C",
            explanation="Giải thích.",
            source_ids=["T01-S03"],
        )
        assert quiz.correct_label == "C"
        assert len(quiz.options) == 4
