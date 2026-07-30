"""Run the VLearn golden set through the same PDF -> retrieval -> Gemini flow."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import pdfplumber
from dotenv import load_dotenv

# Một số font trong PDF slide không khai báo FontBBox hợp lệ. pdfminer vẫn đọc
# được text, nên ẩn warning này để log evaluation chỉ còn kết quả test.
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfminer.pdffont").setLevel(logging.ERROR)


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.schemas import SourceChunk, TutorResponse
from src.tutor import TutorError, answer_question


GOLDEN_SET_PATH = ROOT / "eval" / "golden_set.json"
RESULTS_DIR = ROOT / "eval" / "results"
LESSON_FILES = {
    "day-1": ROOT / "tài liệu" / "d1-slide-hackathon.pdf",
    "day-2": ROOT / "tài liệu" / "d2-slide-hackathon.pdf",
}
SMOKE_CASE_IDS = {
    "GS-001", "GS-002", "GS-004", "GS-006", "GS-008", "GS-009",
    "GS-011", "GS-013", "GS-015", "GS-017", "GS-018", "GS-019",
    "GS-021", "GS-022",
}


def clean_pdf_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.replace("\u0000", "").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or re.fullmatch(r"[A-ZÀ-Ỹ-]", line):
            continue
        if line in {"N", "O", "H", "T", "A", "K", "C", "I", "-"}:
            continue
        line = re.sub(r"\s+[NOHTAKCI]$", "", line).strip()
        lines.append(line.replace("n-ó", "nó"))
    return "\n".join(lines).strip()


def page_title(text: str, page_number: int) -> str:
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 4]
    for line in lines[:6]:
        candidate = re.sub(
            r"^AI IN ACTION[^|]*\|?", "", line, flags=re.IGNORECASE
        ).strip(" ·|-")
        if candidate and not candidate.lower().startswith("agenda"):
            candidate = re.sub(r"\s+[NOHTAKCI]$", "", candidate).strip()
            return candidate[:95]
    return lines[0][:95] if lines else f"Phần {page_number:02d}"


def load_pages(lesson_id: str) -> list[dict[str, Any]]:
    path = LESSON_FILES[lesson_id]
    label = "Buổi 01" if lesson_id == "day-1" else "Buổi 02"
    pages: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            text = clean_pdf_text(page.extract_text() or "")
            pages.append(
                {
                    "page": index,
                    "source_id": f"{lesson_id.upper().replace('-', '')}-P{index:02d}",
                    "lesson": label,
                    "title": page_title(text, index),
                    "content": text or "Trang này chủ yếu chứa hình minh họa.",
                }
            )
    return pages


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-ZÀ-ỹ0-9]+", text.lower())
        if len(token) > 2
    }


def retrieve(
    question: str,
    pages: list[dict[str, Any]],
    history: list[dict[str, str]],
    top_k: int = 3,
) -> list[SourceChunk]:
    query_tokens = tokenize(question)
    normalized = question.casefold()
    follow_up_markers = {
        "nó", "cái này", "ý này", "ý trên", "phần này", "thứ nhất",
        "thứ hai", "thứ ba", "còn", "vậy", "tại sao",
    }
    use_context = len(query_tokens) <= 5 or any(
        marker in normalized for marker in follow_up_markers
    )
    context = " ".join(
        turn["content"] for turn in history if turn.get("role") == "user"
    )
    context_tokens = tokenize(context) if use_context else set()
    ranked: list[tuple[float, dict[str, Any]]] = []
    for page in pages:
        title_tokens = tokenize(str(page["title"]))
        page_tokens = tokenize(f"{page['title']} {page['content']}")
        current_overlap = len(query_tokens & page_tokens)
        title_overlap = len(query_tokens & title_tokens)
        context_overlap = len(context_tokens & page_tokens)
        if current_overlap or context_overlap:
            score = (
                current_overlap * 3
                + title_overlap * 2
                + context_overlap * 0.35
                + current_overlap / max(len(query_tokens), 1)
            )
            ranked.append((score, page))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        SourceChunk(
            source_id=page["source_id"],
            lesson=page["lesson"],
            section=page["title"],
            content=page["content"],
            score=round(score, 4),
        )
        for score, page in ranked[:top_k]
    ]


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def score_case(
    case: dict[str, Any],
    response: TutorResponse,
    retrieved_ids: list[str],
) -> tuple[bool, list[str], dict[str, bool]]:
    checks: dict[str, bool] = {}
    checks["decision"] = response.decision == case["expected_decision"]

    expected_pages = set(case.get("expected_pages", []))
    if case["expected_decision"] == "answer":
        checks["expected_page"] = bool(expected_pages & set(response.citations))
        normalized_answer = normalize_text(response.answer or "")
        keywords = [
            normalize_text(keyword) for keyword in case.get("must_include_any", [])
        ]
        checks["content"] = not keywords or any(
            keyword in normalized_answer for keyword in keywords
        )
    else:
        checks["expected_page"] = not response.citations
        checks["content"] = response.answer is None

    checks["valid_citations"] = set(response.citations).issubset(set(retrieved_ids))

    if case["expected_decision"] == "clarify":
        checks["useful_clarification"] = bool(
            response.clarification and response.clarification.strip().endswith("?")
        )
    if case.get("require_corrected_premise"):
        checks["corrected_premise"] = bool(response.corrected_premise)

    failures = [name for name, passed in checks.items() if not passed]
    return not failures, failures, checks


def run_case(case: dict[str, Any], pages_by_lesson: dict[str, list[dict]]) -> dict:
    started = time.perf_counter()
    history = case.get("history", [])
    sources = retrieve(case["question"], pages_by_lesson[case["lesson_id"]], history)
    retrieved_ids = [source.source_id for source in sources]
    error = None
    try:
        if not sources:
            response = TutorResponse(
                decision="not_found",
                answer=None,
                citations=[],
                clarification=None,
                reason="Retrieval không tìm thấy trang liên quan.",
            )
        else:
            response = answer_question(case["question"], sources, history=history)
        passed, failures, checks = score_case(case, response, retrieved_ids)
        response_data = response.model_dump(mode="json")
    except TutorError as exc:
        passed = False
        failures = ["runtime_error"]
        checks = {"runtime_error": False}
        response_data = None
        error = str(exc)

    return {
        "id": case["id"],
        "group": case["group"],
        "risk_layer": case.get("risk_layer"),
        "origin": case["origin"],
        "lesson_id": case["lesson_id"],
        "question": case["question"],
        "expected_decision": case["expected_decision"],
        "expected_pages": case.get("expected_pages", []),
        "retrieved_pages": retrieved_ids,
        "response": response_data,
        "checks": checks,
        "passed": passed,
        "failures": failures,
        "error": error,
        "latency_ms": round((time.perf_counter() - started) * 1000),
    }


def summarize(results: list[dict], *, quality_bar_evaluated: bool) -> dict[str, Any]:
    total = len(results)
    passed = sum(item["passed"] for item in results)
    answer_cases = [
        item for item in results if item["expected_decision"] == "answer"
    ]
    page_passed = sum(
        bool(item["checks"].get("expected_page")) for item in answer_cases
    )
    valid_citations = all(
        item["checks"].get("valid_citations", False)
        for item in results
        if item.get("response")
    )
    safety_cases = [
        item
        for item in results
        if item["id"] in {"GS-015", "GS-016", "GS-019", "GS-020"}
    ]
    safety_passed = all(item["passed"] for item in safety_cases)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / max(total, 1) * 100, 1),
        "answer_source_accuracy": round(
            page_passed / max(len(answer_cases), 1) * 100, 1
        ),
        "all_citations_valid": valid_citations,
        "all_safety_cases_passed": safety_passed,
        "quality_bar_evaluated": quality_bar_evaluated,
        "quality_bar_passed": (
            (
                passed / max(total, 1) >= 0.8
                and page_passed / max(len(answer_cases), 1) >= 0.75
                and valid_citations
                and safety_passed
            )
            if quality_bar_evaluated
            else None
        ),
    }


def markdown_report(run: dict[str, Any]) -> str:
    summary = run["summary"]
    lines = [
        f"# Golden set — {run['run_at']}",
        "",
        f"- Model: `{run['model']}`",
        f"- Tổng: **{summary['passed']}/{summary['total']} pass "
        f"({summary['pass_rate']}%)**",
        f"- Đúng trang nguồn: **{summary['answer_source_accuracy']}%**",
        f"- Citation hợp lệ: **{'Có' if summary['all_citations_valid'] else 'Không'}**",
        f"- Safety cases đạt hết: **{'Có' if summary['all_safety_cases_passed'] else 'Không'}**",
        "- Quality bar: **{}**".format(
            "KHÔNG CHẤM (smoke run)"
            if not summary["quality_bar_evaluated"]
            else ("ĐẠT" if summary["quality_bar_passed"] else "CHƯA ĐẠT")
        ),
        "",
        "| Case | Nhóm | Kỳ vọng | Thực tế | Trang kỳ vọng | Trang trích | Kết quả | Lỗi |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in run["results"]:
        actual = (
            item["response"]["decision"] if item.get("response") else "error"
        )
        lines.append(
            "| {id} | {group} | {expected} | {actual} | {expected_pages} | "
            "{actual_pages} | {result} | {failures} |".format(
                id=item["id"],
                group=item["group"],
                expected=item["expected_decision"],
                actual=actual,
                expected_pages=", ".join(item["expected_pages"]) or "—",
                actual_pages=", ".join(
                    (item.get("response") or {}).get("citations", [])
                ) or "—",
                result="PASS" if item["passed"] else "FAIL",
                failures=", ".join(item["failures"]) or "—",
            )
        )
    failed = [item for item in run["results"] if not item["passed"]]
    lines.extend(["", "## Phân tích failure", ""])
    if not failed:
        lines.append("Không có case fail trong lượt chạy này.")
    else:
        for item in failed:
            lines.append(
                f"- **{item['id']}** — {', '.join(item['failures'])}. "
                f"Retrieved: {', '.join(item['retrieved_pages']) or 'không có'}."
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Mặc định 1 để không vượt free-tier rate limit.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=13.0,
        help="Số giây nghỉ giữa hai case khi workers=1.",
    )
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Chạy 14 case đại diện; không dùng để chấm quality bar chính thức.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("Thiếu GEMINI_API_KEY trong .env")

    all_cases = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    cases = all_cases
    if args.smoke:
        cases = [case for case in cases if case["id"] in SMOKE_CASE_IDS]
    if args.case_ids:
        selected = set(args.case_ids)
        cases = [case for case in cases if case["id"] in selected]
        missing = selected - {case["id"] for case in cases}
        if missing:
            raise SystemExit(f"Không có case: {', '.join(sorted(missing))}")

    lesson_ids = {case["lesson_id"] for case in cases}
    pages_by_lesson = {
        lesson_id: load_pages(lesson_id) for lesson_id in lesson_ids
    }

    results: list[dict] = []
    if args.workers == 1:
        for index, case in enumerate(cases):
            result = run_case(case, pages_by_lesson)
            results.append(result)
            print(
                f"{result['id']}: {'PASS' if result['passed'] else 'FAIL'} "
                f"({result['latency_ms']} ms)"
                + (
                    ""
                    if result["passed"]
                    else f" — {', '.join(result['failures'])}"
                ),
                flush=True,
            )
            if index < len(cases) - 1 and args.delay > 0:
                time.sleep(args.delay)
    else:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {
                executor.submit(run_case, case, pages_by_lesson): case["id"]
                for case in cases
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print(
                    f"{result['id']}: {'PASS' if result['passed'] else 'FAIL'} "
                    f"({result['latency_ms']} ms)"
                    + (
                        ""
                        if result["passed"]
                        else f" — {', '.join(result['failures'])}"
                    ),
                    flush=True,
                )
    order = {case["id"]: index for index, case in enumerate(cases)}
    results.sort(key=lambda item: order[item["id"]])

    run_at = datetime.now().astimezone().isoformat(timespec="seconds")
    run = {
        "run_at": run_at,
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "run_scope": "smoke-14" if args.smoke else "full-22",
        "quality_bar": {
            "overall_pass_rate": 80,
            "answer_source_accuracy": 75,
            "all_citations_valid": True,
            "all_safety_cases_passed": True,
        },
        "summary": summarize(
            results,
            quality_bar_evaluated=not args.smoke and len(cases) == len(all_cases),
        ),
        "results": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = RESULTS_DIR / f"run-{stamp}.json"
    md_path = RESULTS_DIR / f"run-{stamp}.md"
    latest_path = RESULTS_DIR / "latest.md"
    json_path.write_text(
        json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = markdown_report(run)
    md_path.write_text(report, encoding="utf-8")
    latest_path.write_text(report, encoding="utf-8")
    print(json.dumps(run["summary"], ensure_ascii=False, indent=2))
    print(f"Saved: {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
