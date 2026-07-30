from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pdfplumber
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.quiz import generate_lesson_quiz, grade_quiz
from src.schemas import QuizSet, SourceChunk


DEFINITION_PATH = ROOT / "eval" / "quiz_golden_set.json"
RESULTS_DIR = ROOT / "eval" / "results"
LESSON_FILES = {
    "DAY1": ROOT / "tài liệu" / "d1-slide-hackathon.pdf",
    "DAY2": ROOT / "tài liệu" / "d2-slide-hackathon.pdf",
}
STOP_WORDS = {
    "của", "cho", "trong", "được", "những", "một", "với", "theo", "này",
    "đáp", "giải", "thích", "học", "buổi", "trang", "không",
}


def load_sources(lesson_codes: list[str]) -> list[SourceChunk]:
    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    sources: list[SourceChunk] = []
    for lesson_code in lesson_codes:
        with pdfplumber.open(LESSON_FILES[lesson_code]) as pdf:
            for page_number, page in enumerate(pdf.pages, 1):
                text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
                if text:
                    sources.append(
                        SourceChunk(
                            source_id=f"{lesson_code}-P{page_number:02d}",
                            lesson=f"Buổi {int(lesson_code[-1]):02d}",
                            section=f"Trang {page_number}",
                            content=text,
                        )
                    )
    return sources


def normalize_question(text: str) -> str:
    return re.sub(r"\W+", " ", text.casefold()).strip()


def tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
        if len(token) >= 4 and token not in STOP_WORDS
    }


def grounding_proxy(quiz_set: QuizSet, source_map: dict[str, SourceChunk]) -> bool:
    for question in quiz_set.questions:
        correct = next(
            option.text
            for option in question.options
            if option.label == question.correct_label
        )
        answer_tokens = tokens(
            f"{question.question} {correct} {question.explanation}"
        )
        source_text = " ".join(
            source_map[source_id].content for source_id in question.source_ids
        )
        if not (answer_tokens & tokens(source_text)):
            return False
    return True


class VariantModels:
    def generate_content(self, **_: object) -> SimpleNamespace:
        questions = [
            {
                "question": f"Câu JSON biến thể {index + 1}?",
                "options": {
                    "A": "Đáp án đúng",
                    "B": "Đáp án nhiễu 1",
                    "C": "Đáp án nhiễu 2",
                    "D": "Đáp án nhiễu 3"
                },
                "answer": "A",
                "explanation": "Nội dung được hỗ trợ bởi nguồn.",
                "source_ids": ["DAY1-P01"]
            }
            for index in range(10)
        ]
        return SimpleNamespace(text=json.dumps(questions, ensure_ascii=False))


class VariantClient:
    models = VariantModels()


def make_result(case_id: str, passed: bool, detail: str) -> dict[str, object]:
    return {"id": case_id, "passed": passed, "detail": detail}


def run() -> dict[str, object]:
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))
    day1_sources = load_sources(["DAY1"])
    multi_sources = load_sources(["DAY1", "DAY2"])
    day1_quiz = generate_lesson_quiz(day1_sources, 10)
    multi_quiz = generate_lesson_quiz(multi_sources, 10)

    day1_valid = {source.source_id for source in day1_sources}
    multi_valid = {source.source_id for source in multi_sources}
    day1_map = {source.source_id: source for source in day1_sources}
    multi_map = {source.source_id: source for source in multi_sources}
    day1_citations = {
        source_id for quiz in day1_quiz.questions for source_id in quiz.source_ids
    }
    multi_citations = {
        source_id for quiz in multi_quiz.questions for source_id in quiz.source_ids
    }
    all_questions = day1_quiz.questions + multi_quiz.questions
    normalized = [normalize_question(quiz.question) for quiz in all_questions]
    structurally_valid = all(
        len(quiz.options) == 4
        and len({option.label for option in quiz.options}) == 4
        and sum(option.label == quiz.correct_label for option in quiz.options) == 1
        for quiz in all_questions
    )

    variant_quiz = generate_lesson_quiz(
        [day1_sources[0]], 10, client=VariantClient()
    )
    grading_quiz = QuizSet(
        title="Grading regression", questions=day1_quiz.questions[:3]
    )
    score, unanswered = grade_quiz(
        grading_quiz,
        [grading_quiz.questions[0].correct_label, None, "INVALID"],
    )
    cited_lessons = {item.split("-P")[0] for item in multi_citations}

    checks = [
        make_result("QZ-001", len(day1_quiz.questions) == 10, f"{len(day1_quiz.questions)}/10 câu"),
        make_result("QZ-002", len(multi_quiz.questions) == 10, f"{len(multi_quiz.questions)}/10 câu"),
        make_result("QZ-003", bool(day1_citations) and all(item.startswith("DAY1-") for item in day1_citations), ", ".join(sorted(day1_citations))),
        make_result("QZ-004", cited_lessons == {"DAY1", "DAY2"}, "Buổi được cite: " + ", ".join(sorted(cited_lessons))),
        make_result("QZ-005", len(normalized) == len(set(normalized)), f"{len(set(normalized))}/{len(normalized)} câu duy nhất"),
        make_result("QZ-006", structurally_valid, "Mỗi câu có 4 option và 1 correct_label"),
        make_result("QZ-007", day1_citations <= day1_valid and multi_citations <= multi_valid, "Không có source ID lạ"),
        make_result("QZ-008", grounding_proxy(day1_quiz, day1_map) and grounding_proxy(multi_quiz, multi_map), "Lexical support proxy"),
        make_result("QZ-009", len(variant_quiz.questions) == 10 and all(len(item.options) == 4 for item in variant_quiz.questions), "Chuẩn hóa list/object, option map và answer"),
        make_result("QZ-010", score == 1 and unanswered == [2], f"score={score}/3; unanswered={unanswered}"),
    ]
    passed = sum(bool(item["passed"]) for item in checks)
    hard_ids = set(definition["quality_bar"]["hard_requirements"])
    hard_pass = all(
        bool(item["passed"]) for item in checks if item["id"] in hard_ids
    )
    pass_rate = round(passed / len(checks) * 100, 1)
    quality_pass = (
        pass_rate >= definition["quality_bar"]["overall_pass_rate"]
        and hard_pass
    )
    return {
        "run_at": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(timespec="seconds"),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "scope": "2 live Gemini generations + 2 deterministic regressions",
        "summary": {
            "total": len(checks),
            "passed": passed,
            "failed": len(checks) - passed,
            "pass_rate": pass_rate,
            "hard_requirements_passed": hard_pass,
            "quality_bar_passed": quality_pass
        },
        "results": checks
    }


def markdown_report(report: dict[str, object]) -> str:
    summary = report["summary"]
    lines = [
        "# Quiz evaluation report",
        "",
        f"- Run: `{report['run_at']}`",
        f"- Model: `{report['model']}`",
        f"- Scope: {report['scope']}",
        f"- Result: **{summary['passed']}/{summary['total']} ({summary['pass_rate']}%)**",
        f"- Quality bar: **{'PASS' if summary['quality_bar_passed'] else 'FAIL'}**",
        "",
        "| ID | Kết quả | Chi tiết |",
        "|---|:---:|---|"
    ]
    for item in report["results"]:
        lines.append(
            f"| {item['id']} | {'PASS' if item['passed'] else 'FAIL'} | {item['detail']} |"
        )
    lines.extend([
        "",
        "## Diễn giải",
        "",
        "- QZ-001 đến QZ-008 chấm trên hai output Gemini thật.",
        "- QZ-009 tái hiện JSON biến thể mà Gemini từng trả.",
        "- QZ-010 kiểm tra câu bỏ trống được ghi nhận và tính sai khi vẫn nộp.",
        "- QZ-008 là grounding proxy lexical; đánh giá ngữ nghĩa sâu hơn vẫn cần human review.",
        ""
    ])
    return "\n".join(lines)


def main() -> None:
    load_dotenv(ROOT / ".env")
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("Thiếu GEMINI_API_KEY trong .env")
    report = run()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = RESULTS_DIR / f"quiz-run-{stamp}.json"
    md_path = RESULTS_DIR / f"quiz-run-{stamp}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(markdown_report(report), encoding="utf-8")
    (RESULTS_DIR / "quiz-latest.md").write_text(
        markdown_report(report), encoding="utf-8"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Saved: {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
