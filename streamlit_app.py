from __future__ import annotations

import json
import os
import re
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
import streamlit as st
from dotenv import load_dotenv

from src.quiz import QuizGenerationError, generate_lesson_quiz, grade_quiz
from src.schemas import Quiz, QuizOption, QuizSet, SourceChunk, TutorResponse
from src.tutor import TutorError, answer_question


load_dotenv()
ROOT = Path(__file__).resolve().parent
CHAT_HISTORY_PATH = ROOT / ".vlearn_chat_history.json"


@dataclass(frozen=True)
class Lesson:
    lesson_id: str
    label: str
    title: str
    subtitle: str
    path: Path


LESSONS = {
    "day-1": Lesson(
        lesson_id="day-1",
        label="Buổi 01",
        title="AI & LLM Foundation",
        subtitle="Từ nền tảng AI đến cách LLM vận hành",
        path=ROOT / "tài liệu" / "d1-slide-hackathon.pdf",
    ),
    "day-2": Lesson(
        lesson_id="day-2",
        label="Buổi 02",
        title="Xác định bài toán cho AI",
        subtitle="Từ yêu cầu mơ hồ đến Problem Statement rõ ràng",
        path=ROOT / "tài liệu" / "d2-slide-hackathon.pdf",
    ),
}


def load_chat_history() -> dict[str, list[dict]]:
    """Restore complete chats so they survive browser/app restarts."""
    chats = {lesson_id: [] for lesson_id in LESSONS}
    if not CHAT_HISTORY_PATH.exists():
        return chats
    try:
        raw = json.loads(CHAT_HISTORY_PATH.read_text(encoding="utf-8"))
        for lesson_id in LESSONS:
            for item in raw.get(lesson_id, []):
                response_data = item.get("response")
                chats[lesson_id].append(
                    {
                        "role": item.get("role", "user"),
                        "content": item.get("content", ""),
                        "response": (
                            TutorResponse.model_validate(response_data)
                            if response_data
                            else None
                        ),
                        "sources": [
                            SourceChunk.model_validate(source)
                            for source in item.get("sources", [])
                        ],
                    }
                )
    except (OSError, ValueError, TypeError):
        return {lesson_id: [] for lesson_id in LESSONS}
    return chats


def save_chat_history(chats: dict[str, list[dict]]) -> None:
    """Persist every user and assistant turn, grouped by lesson."""
    serializable: dict[str, list[dict]] = {}
    for lesson_id, messages in chats.items():
        serializable[lesson_id] = []
        for item in messages:
            response = item.get("response")
            sources = item.get("sources", [])
            serializable[lesson_id].append(
                {
                    "role": item.get("role", "user"),
                    "content": item.get("content", ""),
                    "response": (
                        response.model_dump(mode="json")
                        if isinstance(response, TutorResponse)
                        else response
                    ),
                    "sources": [
                        source.model_dump(mode="json")
                        if isinstance(source, SourceChunk)
                        else source
                        for source in sources
                    ],
                }
            )
    CHAT_HISTORY_PATH.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


st.set_page_config(
    page_title="VLearn Smart Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root{--forest:#124c38;--lime:#c7f34f;--coral:#ff5a5f;--paper:#fbfcf8;--ink:#172126;--muted:#77817c}
    html,body,[class*="css"],.stApp{
      font-family:"Segoe UI",Arial,sans-serif;
      font-kerning:normal;
      text-rendering:optimizeLegibility
    }
    .stApp{background:var(--paper);color:var(--ink)}
    [data-testid="stSidebar"]{background:#f0f4ee;border-right:1px solid #d7ddd9}
    [data-testid="stSidebar"] .stButton button{border-radius:10px;border:1px solid #d2d9d5;background:#fff;color:#26332d}
    [data-testid="stSidebar"] .stButton button:hover{border-color:var(--forest);color:var(--forest)}
    .brand{display:flex;align-items:center;gap:.7rem;font-size:1.55rem;font-weight:850;color:var(--forest);margin:.1rem 0 1.4rem}
    .mark{display:grid;place-items:center;width:2.45rem;height:2.45rem;background:var(--lime);border-radius:.75rem .75rem .75rem .2rem;color:#163d2f}
    .lesson-kicker{color:#257359;font-size:.76rem;font-weight:850;letter-spacing:.12em;text-transform:uppercase;margin-top:.2rem}
    .lesson-title{font-family:"Segoe UI",Arial,sans-serif;font-size:clamp(2.35rem,4vw,4.2rem);font-weight:800;line-height:1.08;letter-spacing:-.025em;margin:.45rem 0 1rem}
    .lead{font-family:"Segoe UI",Arial,sans-serif;font-size:1.18rem;color:#59645f;line-height:1.6;margin-bottom:1.4rem}
    .section-card{background:#fff;border:1px solid #dce3df;border-radius:16px;padding:1.25rem 1.4rem;margin:.85rem 0;box-shadow:0 8px 30px rgba(18,76,56,.035)}
    .section-card h3{color:var(--forest);margin:0 0 .6rem;font-size:1.08rem}
    .section-card p{color:#45524c;line-height:1.7;margin:0;white-space:pre-line}
    .section-meta{display:flex;gap:.55rem;align-items:center;color:#7b8680;font-size:.8rem;margin:.7rem 0 1.2rem}
    .pill{display:inline-block;padding:.28rem .6rem;border-radius:999px;background:#edf4f0;color:#276a53;font-weight:700}
    .tutor-head{font-family:"Segoe UI",Arial,sans-serif;font-size:1.42rem;font-weight:800;margin:0 0 .15rem}
    .grounded{color:#6d7872;font-size:.86rem;margin-bottom:1rem}
    .dot{display:inline-block;width:.7rem;height:.7rem;border-radius:50%;background:#71dda8;margin-right:.35rem;box-shadow:0 0 0 3px #e2f6eb}
    .answer{background:#fff;border:1px solid #dce3df;border-radius:15px;padding:1.1rem;margin-top:1rem}
    .verified,.warning{padding:.55rem .72rem;border-radius:8px;font-size:.77rem;font-weight:850;margin-bottom:.8rem}
    .verified{background:#def2e8;color:#176447}.warning{background:#fff0c9;color:#835f0c}
    .source{background:#eef5f1;color:#15513c;padding:.75rem;border-radius:9px;margin-top:.8rem;font-size:.84rem}
    .progress-label{display:flex;justify-content:space-between;color:#7b8580;font-size:.78rem;margin-top:.3rem}
    .empty-chat{padding:1.1rem;border:1px dashed #cfd8d3;border-radius:12px;color:#78837d;font-size:.9rem}
    .quiz-source{font-size:.78rem;color:#69756f;background:#eff5f1;padding:.55rem .7rem;border-radius:8px}
    .quiz-hero{background:linear-gradient(135deg,#f0f8f3,#fbfdea);border:1px solid #d7e5dc;border-radius:16px;padding:1.1rem 1.25rem;margin:.6rem 0 1rem}
    .quiz-hero h3{margin:0 0 .3rem;color:var(--forest)}
    .quiz-hero p{margin:0;color:#627069;line-height:1.5}
    .small-note{text-align:center;color:#929b96;font-size:.72rem;margin-top:.7rem}
    .slide-card{border:1px solid #dce3df;border-radius:16px;padding:1rem;margin:0 0 1.25rem;background:#fff;box-shadow:0 8px 28px rgba(18,76,56,.04)}
    .slide-card-head{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:.75rem}
    .slide-card-title{font-weight:800;color:var(--forest);font-size:1rem}
    .slide-card-meta{color:#7b8680;font-size:.75rem;white-space:nowrap}
    .st-key-tutor_panel{
      position:fixed!important;
      top:1rem;
      right:1.25rem;
      width:min(360px,27vw);
      height:calc(100vh - 2rem);
      z-index:50;
      padding:.9rem;
      border:1px solid #dce3df;
      border-radius:16px;
      background:#fff;
      box-shadow:0 12px 35px rgba(18,76,56,.10);
      overflow:hidden
    }
    .st-key-tutor_panel [data-testid="stVerticalBlockBorderWrapper"]{border-color:#e2e7e4}
    @media(max-width:900px){
      .lesson-title{font-size:2.2rem}
      .st-key-tutor_panel{position:static!important;width:auto;height:auto;max-height:none;margin-top:1rem}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _clean_pdf_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.replace("\u0000", "").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or re.fullmatch(r"[A-ZÀ-Ỹ-]", line):
            continue
        if line in {"N", "O", "H", "T", "A", "K", "C", "I", "-"}:
            continue
        # Watermark letters from the slide template are sometimes appended to
        # an otherwise valid line by PDF text extraction.
        line = re.sub(r"\s+[NOHTAKCI]$", "", line).strip()
        line = line.replace("n-ó", "nó")
        lines.append(line)
    return "\n".join(lines).strip()


def _page_title(text: str, page_number: int) -> str:
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 4]
    for line in lines[:6]:
        candidate = re.sub(r"^AI IN ACTION[^|]*\|?", "", line, flags=re.IGNORECASE).strip(" ·|-")
        if candidate and not candidate.lower().startswith("agenda"):
            candidate = re.sub(r"\s+[NOHTAKCI]$", "", candidate).strip()
            return candidate[:95]
    return lines[0][:95] if lines else f"Phần {page_number:02d}"


@st.cache_data(show_spinner=False)
def load_lesson_pages(path_string: str, lesson_id: str, lesson_label: str) -> list[dict[str, str | int]]:
    path = Path(path_string)
    if not path.exists():
        return []
    pages: list[dict[str, str | int]] = []
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            text = _clean_pdf_text(page.extract_text() or "")
            pages.append(
                {
                    "page": index,
                    "source_id": f"{lesson_id.upper().replace('-', '')}-P{index:02d}",
                    "lesson": lesson_label,
                    "title": _page_title(text, index),
                    "content": text or "Trang này chủ yếu chứa hình minh họa.",
                }
            )
    return pages


@st.cache_data(show_spinner=False)
def render_slide(path_string: str, page_number: int, scale: float = 1.8) -> bytes:
    """Render one PDF page as a sharp PNG for the lesson viewer."""
    document = pdfium.PdfDocument(path_string)
    page = document[page_number - 1]
    bitmap = page.render(scale=scale, rotation=0)
    image = bitmap.to_pil()
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    page.close()
    document.close()
    return buffer.getvalue()


def tokenize(text: str) -> set[str]:
    tokens = set()
    for token in re.findall(r"[a-zA-ZÀ-ỹ0-9]+", text.lower()):
        if len(token) <= 2:
            continue
        # Normalize simple English plurals used in slide headings, e.g.
        # "workflow pattern" in a question vs "workflow patterns" in PDF.
        tokens.add(token[:-1] if token.isascii() and len(token) > 4 and token.endswith("s") else token)
    return tokens


def is_blocked_out_of_scope(question: str) -> bool:
    """Deterministic safety gate before retrieval/LLM generation."""
    normalized = question.casefold()
    high_stakes_terms = (
        "chẩn đoán", "chữa bệnh", "đơn thuốc", "liều thuốc",
        "tư vấn pháp lý", "kiện tụng", "lời khuyên đầu tư",
    )
    return any(term in normalized for term in high_stakes_terms)


def retrieve_from_lesson(
    question: str,
    pages: list[dict[str, str | int]],
    *,
    context: str = "",
    top_k: int = 3,
) -> list[SourceChunk]:
    """Rank the current question first; use chat history only for follow-ups."""
    query_tokens = tokenize(question)
    normalized = question.casefold()
    follow_up_markers = {
        "nó", "cái này", "ý này", "ý trên", "phần này", "thứ nhất",
        "thứ hai", "thứ ba", "còn", "vậy", "tại sao",
    }
    use_context = len(query_tokens) <= 5 or any(
        marker in normalized for marker in follow_up_markers
    )
    context_tokens = tokenize(context) if use_context else set()
    overview_intent = any(
        phrase in normalized
        for phrase in (
            "nội dung chính",
            "học những gì",
            "học gì",
            "gồm những gì",
            "agenda",
            "tổng quan buổi",
        )
    )
    ranked = []
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
            if overview_intent and "agenda" in str(page["content"]).casefold():
                score += 25
            ranked.append((score, page))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        SourceChunk(
            source_id=str(page["source_id"]),
            lesson=str(page["lesson"]),
            section=str(page["title"]),
            content=str(page["content"]),
            score=round(score, 4),
        )
        for score, page in ranked[:top_k]
    ]


def lesson_sources(pages: list[dict[str, str | int]]) -> list[SourceChunk]:
    """Expose every PDF page as a grounded source for the lesson quiz."""
    return [
        SourceChunk(
            source_id=str(page["source_id"]),
            lesson=str(page["lesson"]),
            section=str(page["title"]),
            content=str(page["content"]),
        )
        for page in pages
    ]


def fallback_lesson_quiz(
    pages: list[dict[str, str | int]],
    question_count: int,
) -> QuizSet:
    """Deterministic local quiz used only when Gemini is unavailable."""
    informative = [
        page
        for page in pages
        if len(str(page["content"]).split()) >= 8
    ] or pages
    questions: list[Quiz] = []
    for index in range(question_count):
        page = informative[index % len(informative)]
        distractors = [
            str(item["title"])
            for item in informative
            if item["source_id"] != page["source_id"]
            and str(item["title"]) != str(page["title"])
        ]
        if len(distractors) < 3:
            distractors.extend(
                ["Một nội dung ngoài buổi học", "Thông tin không được đề cập", "Cả ba đáp án"]
            )
        options = [str(page["title"]), *distractors[:3]]
        questions.append(
            Quiz(
                question=(
                    f"Câu {index + 1}: Nội dung nào phù hợp nhất với phần "
                    f"“{str(page['title'])[:65]}”?"
                ),
                options=[
                    QuizOption(label=label, text=text)
                    for label, text in zip(("A", "B", "C", "D"), options)
                ],
                correct_label="A",
                explanation=f"Đáp án được tổng hợp từ Trang {int(page['page'])}.",
                source_ids=[str(page["source_id"])],
            )
        )
    return QuizSet(title="Quiz tổng hợp buổi học", questions=questions)


def create_lesson_quiz(
    pages: list[dict[str, str | int]],
    question_count: int,
) -> QuizSet:
    if not os.getenv("GEMINI_API_KEY"):
        return fallback_lesson_quiz(pages, question_count)
    return generate_lesson_quiz(lesson_sources(pages), question_count)


def _citation_link(source_id: str) -> str:
    """Convert an internal source id into a learner-friendly page link."""
    match = re.search(r"-P(\d+)$", source_id)
    page_number = int(match.group(1)) if match else source_id
    lesson_match = re.match(r"DAY(\d+)-P", source_id)
    lesson_prefix = (
        f"Buổi {int(lesson_match.group(1)):02d} · " if lesson_match else ""
    )
    anchor = f"slide-{source_id.lower()}"
    return f"[{lesson_prefix}Trang {page_number}](#{anchor})"


def _link_answer_citations(answer: str, sources: list[SourceChunk]) -> str:
    """Show every cited page once in a compact source footer."""
    body = answer
    source_links: list[str] = []
    for source in sources:
        token = f"[{source.source_id}]"
        if token in body:
            body = body.replace(token, "")
            source_links.append(_citation_link(source.source_id))
    body = re.sub(r"[ \t]+([.,;:])", r"\1", body)
    body = re.sub(r"[ \t]+\n", "\n", body).strip()
    if not source_links:
        return body
    return f"{body}\n\n**Nguồn:** {' · '.join(source_links)}"


def render_answer(response: TutorResponse, sources: list[SourceChunk]) -> None:
    if response.decision == "answer":
        st.markdown(
            '<div class="verified">✓ CÓ CĂN CỨ TRONG BUỔI HỌC</div>',
            unsafe_allow_html=True,
        )
        st.markdown(_link_answer_citations(response.answer or "", sources))
    elif response.decision == "clarify":
        st.markdown(
            '<div class="warning">? CẦN THÊM NGỮ CẢNH</div>',
            unsafe_allow_html=True,
        )
        st.markdown(response.clarification or "")
    else:
        st.markdown(
            '<div class="warning">⚠ KHÔNG CÓ ĐỦ CĂN CỨ</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            "**Tài liệu buổi học không đề cập.**\n\n"
            "Smart Tutor sẽ không sử dụng kiến thức ngoài hoặc tự suy đoán."
        )


def render_lesson_quiz(quiz_set: QuizSet, lesson_id: str) -> None:
    """Render the whole assessment inline and grade it as one submission."""
    st.markdown(
        '<div class="quiz-hero"><h3>Quiz tổng hợp buổi học</h3>'
        '<p>Trả lời toàn bộ câu hỏi rồi bấm nộp bài. '
        'Mỗi đáp án đều được đối chiếu với slide của buổi học.</p></div>',
        unsafe_allow_html=True,
    )
    answers: dict[int, str | None] = {}
    with st.form(key=f"lesson-quiz-form-{lesson_id}"):
        for index, quiz in enumerate(quiz_set.questions, 1):
            st.markdown(f"#### Câu {index}. {quiz.question}")
            answer_map = {option.label: option.text for option in quiz.options}
            answers[index - 1] = st.radio(
                "Chọn một đáp án",
                list(answer_map),
                format_func=lambda label, mapping=answer_map: f"{label}. {mapping[label]}",
                index=None,
                key=f"lesson-quiz-{lesson_id}-{index}",
                label_visibility="collapsed",
            )
            st.divider()
        submitted = st.form_submit_button(
            "Nộp bài và xem kết quả",
            type="primary",
            use_container_width=True,
        )

    ordered_answers = [answers[index] for index in range(len(quiz_set.questions))]
    score, unanswered = grade_quiz(quiz_set, ordered_answers)
    confirm_key = f"confirm-incomplete-quiz-{lesson_id}"
    st.session_state.setdefault(confirm_key, False)
    if submitted and unanswered:
        st.session_state[confirm_key] = True

    if st.session_state[confirm_key] and unanswered:
        force_incomplete_submit = False
        st.warning(
            f"Bạn còn {len(unanswered)} câu chưa trả lời: "
            + ", ".join(map(str, unanswered[:10]))
            + ("…" if len(unanswered) > 10 else "")
            + ". Bạn vẫn muốn nộp bài?"
        )
        continue_col, submit_col = st.columns(2)
        with continue_col:
            if st.button(
                "Tiếp tục trả lời",
                key=f"continue-incomplete-{lesson_id}",
                use_container_width=True,
            ):
                st.session_state[confirm_key] = False
                st.rerun()
        with submit_col:
            if st.button(
                "Vẫn nộp bài",
                key=f"submit-incomplete-{lesson_id}",
                type="primary",
                use_container_width=True,
            ):
                st.session_state[confirm_key] = False
                force_incomplete_submit = True
        if not force_incomplete_submit:
            return
        submitted = True
    elif not unanswered:
        st.session_state[confirm_key] = False

    if submitted:
        percentage = round(score / len(quiz_set.questions) * 100)
        if percentage >= 80:
            st.success(f"Bạn đạt {score}/{len(quiz_set.questions)} câu ({percentage}%).")
        elif percentage >= 50:
            st.warning(f"Bạn đạt {score}/{len(quiz_set.questions)} câu ({percentage}%).")
        else:
            st.error(f"Bạn đạt {score}/{len(quiz_set.questions)} câu ({percentage}%).")

        st.markdown("### Đáp án và giải thích")
        for index, quiz in enumerate(quiz_set.questions, 1):
            selected = answers[index - 1]
            icon = "✅" if selected == quiz.correct_label else "❌"
            source_links = " · ".join(_citation_link(item) for item in quiz.source_ids)
            with st.expander(
                f"{icon} Câu {index} · Đáp án đúng: {quiz.correct_label}",
                expanded=selected != quiz.correct_label,
            ):
                st.markdown(quiz.explanation)
                st.markdown(f"**Nguồn:** {source_links}")


st.session_state.setdefault("lesson_id", "day-1")
st.session_state.setdefault("lesson_chats", load_chat_history())
st.session_state.setdefault("lesson_view", "Slide bài học")
st.session_state.setdefault("lesson_quizzes", {})
st.session_state.setdefault("quiz_scope_picker", ["day-1"])

with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="mark">V</span>VLearn</div>',
        unsafe_allow_html=True,
    )
    st.caption("CHỌN BUỔI HỌC")
    lesson_id = st.selectbox(
        "Buổi học",
        list(LESSONS),
        index=list(LESSONS).index(st.session_state.lesson_id),
        format_func=lambda key: f"{LESSONS[key].label} · {LESSONS[key].title}",
        label_visibility="collapsed",
    )
    if lesson_id != st.session_state.lesson_id:
        st.session_state.lesson_id = lesson_id
        st.session_state.lesson_view = "Slide bài học"
        st.session_state.quiz_scope_picker = [lesson_id]
        st.rerun()

lesson = LESSONS[st.session_state.lesson_id]
pages = load_lesson_pages(str(lesson.path), lesson.lesson_id, lesson.label)
st.session_state.section_count = len(pages)
if not pages:
    st.error(f"Không tìm thấy tài liệu: {lesson.path.name}")
    st.stop()
with st.sidebar:
    st.caption("NỘI DUNG BUỔI HỌC")
    lesson_view = st.radio(
        "Chế độ học",
        ["Slide bài học", "Quiz tổng hợp"],
        index=0 if st.session_state.lesson_view == "Slide bài học" else 1,
        horizontal=True,
    )
    if lesson_view != st.session_state.lesson_view:
        st.session_state.lesson_view = lesson_view
        st.rerun()
    st.caption(f"Slide bài học gồm {len(pages)} trang.")
    if st.session_state.lesson_view == "Quiz tổng hợp":
        st.divider()
        st.caption("TẠO QUIZ TỔNG HỢP")
        quiz_scope_ids = st.multiselect(
            "Phạm vi kiến thức",
            list(LESSONS),
            format_func=lambda key: f"{LESSONS[key].label} · {LESSONS[key].title}",
            key="quiz_scope_picker",
            placeholder="Chọn một hoặc nhiều buổi",
        )
        question_count = st.radio(
            "Số lượng câu hỏi",
            [10, 20, 30],
            horizontal=True,
            key="quiz-question-count",
        )
        if st.button(
            "Tạo bộ câu hỏi",
            type="primary",
            use_container_width=True,
        ):
            generated = False
            if not quiz_scope_ids:
                st.error("Hãy chọn ít nhất một buổi học.")
            else:
                selected_labels = [LESSONS[item].label for item in quiz_scope_ids]
                combined_pages: list[dict[str, str | int]] = []
                for selected_id in quiz_scope_ids:
                    selected_lesson = LESSONS[selected_id]
                    combined_pages.extend(
                        load_lesson_pages(
                            str(selected_lesson.path),
                            selected_lesson.lesson_id,
                            selected_lesson.label,
                        )
                    )
                scope_key = "+".join(sorted(quiz_scope_ids))
                spinner_scope = " + ".join(selected_labels)
                with st.spinner(
                    f"Gemini đang tạo {question_count} câu từ {spinner_scope}..."
                ):
                    try:
                        st.session_state.lesson_quizzes[scope_key] = (
                            create_lesson_quiz(combined_pages, question_count)
                        )
                        generated = True
                    except QuizGenerationError as exc:
                        st.error(f"Không thể tạo quiz: {exc}")
            if generated:
                st.rerun()
    st.divider()
    st.caption("TÀI LIỆU ĐANG DÙNG")
    st.write(f"📄 `{lesson.path.name}`")
    st.caption("Smart Tutor chỉ tìm trong PDF của buổi đang chọn.")
    if st.button("＋ Cuộc trò chuyện mới", use_container_width=True):
        st.session_state.lesson_chats[lesson.lesson_id] = []
        save_chat_history(st.session_state.lesson_chats)
        st.rerun()

lesson_col, tutor_col = st.columns([1.55, 0.65], gap="medium")

with lesson_col:
    if st.session_state.lesson_view == "Quiz tổng hợp":
        quiz_scope_ids = st.session_state.quiz_scope_picker
        scope_key = "+".join(sorted(quiz_scope_ids))
        scope_labels = " + ".join(LESSONS[item].label for item in quiz_scope_ids)
        st.markdown(
            f'<div class="lesson-kicker">{scope_labels or "CHƯA CHỌN BUỔI HỌC"}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="lesson-title">Quiz tổng hợp</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="lead">Kiểm tra kiến thức</div>',
            unsafe_allow_html=True,
        )
        quiz_set = st.session_state.lesson_quizzes.get(scope_key)
        if quiz_set:
            render_lesson_quiz(quiz_set, scope_key)
        else:
            st.markdown(
                '<div class="quiz-hero"><h3>Quiz tổng hợp buổi học</h3>'
                '<p>Chọn một hoặc nhiều buổi, chọn 10/20/30 câu rồi bấm '
                '“Tạo bộ câu hỏi”. Quiz sẽ bao quát phạm vi đã chọn.</p></div>',
                unsafe_allow_html=True,
            )
            st.info("Chưa có bộ câu hỏi cho phạm vi này.")
    else:
        st.markdown(
            f'<div class="lesson-kicker">{lesson.label} · {len(pages)} TRANG SLIDE</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="lesson-title">{lesson.title}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="lead">{lesson.subtitle}</div>', unsafe_allow_html=True)
        with lesson.path.open("rb") as pdf_file:
            st.download_button(
                "Tải toàn bộ slide PDF",
                data=pdf_file.read(),
                file_name=lesson.path.name,
                mime="application/pdf",
                use_container_width=True,
            )
        for page in pages:
            st.markdown(
                f'<div id="slide-{str(page["source_id"]).lower()}" '
                'style="scroll-margin-top:1rem"></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="slide-card-head">'
                f'<span class="slide-card-title">{int(page["page"]):02d} · {page["title"]}</span>'
                f'<span class="slide-card-meta">Trang {int(page["page"])}/{len(pages)}</span>'
                "</div>",
                unsafe_allow_html=True,
            )
            st.image(
                render_slide(str(lesson.path), int(page["page"]), scale=1.25),
                caption=f"{lesson.label} · Trang {page['page']}/{len(pages)}",
                use_container_width=True,
            )
            st.divider()

with tutor_col:
    with st.container(key="tutor_panel"):
        st.markdown('<div class="tutor-head">✦ Smart Tutor</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="grounded"><span class="dot"></span>{lesson.label} · Có nhớ ngữ cảnh</div>',
            unsafe_allow_html=True,
        )
        messages = st.session_state.lesson_chats.setdefault(lesson.lesson_id, [])
        chat_area = st.container(height=430, border=True)
        with chat_area:
            if not messages:
                with st.chat_message("assistant", avatar="🎓"):
                    st.markdown(
                        f"Chào bạn! Hãy hỏi mình về **{lesson.label}**. "
                    )
            for message in messages:
                avatar = "👤" if message["role"] == "user" else "🎓"
                with st.chat_message(message["role"], avatar=avatar):
                    if message["role"] == "user":
                        st.markdown(message["content"])
                    elif message.get("response"):
                        render_answer(message["response"], message.get("sources", []))
                    else:
                        st.error(message["content"])

        question = st.chat_input(
            f"Hỏi về {lesson.label}...",
            key=f"chat-input-{lesson.lesson_id}",
        )
        mode = "Gemini API" if os.getenv("GEMINI_API_KEY") else "Local fallback"
        st.markdown(f'<div class="small-note">Chế độ: {mode}</div>', unsafe_allow_html=True)
    if question:
        history = [
            {"role": item["role"], "content": item["content"]}
            for item in messages[-8:]
        ]
        messages.append({"role": "user", "content": question})
        save_chat_history(st.session_state.lesson_chats)
        prior_user_context = " ".join(
            [item["content"] for item in history if item["role"] == "user"]
        )
        with st.spinner(f"Smart Tutor đang đọc {lesson.label}..."):
            if is_blocked_out_of_scope(question):
                sources = []
                result = TutorResponse(
                    decision="not_found",
                    answer=None,
                    citations=[],
                    clarification=None,
                    reason="Câu hỏi thuộc miền rủi ro cao ngoài phạm vi Tutor.",
                )
            else:
                sources = retrieve_from_lesson(
                    question,
                    pages,
                    context=prior_user_context,
                )
            if not is_blocked_out_of_scope(question) and not sources:
                result = TutorResponse(
                    decision="not_found",
                    answer=None,
                    citations=[],
                    clarification=None,
                    reason="Không tìm thấy trang có nội dung liên quan.",
                )
            elif not is_blocked_out_of_scope(question) and os.getenv("GEMINI_API_KEY"):
                try:
                    result = answer_question(question, sources, history=history)
                except TutorError as exc:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"Gemini đang lỗi: {exc}",
                            "response": None,
                            "sources": [],
                        }
                    )
                    save_chat_history(st.session_state.lesson_chats)
                    st.rerun()
            elif not is_blocked_out_of_scope(question):
                top = sources[0]
                preview = re.split(r"(?<=[.!?])\s+", top.content)[:3]
                result = TutorResponse(
                    decision="answer",
                    answer=f"{' '.join(preview)} [{top.source_id}]",
                    citations=[top.source_id],
                    clarification=None,
                    reason="Chế độ local fallback khi chưa có GEMINI_API_KEY.",
                )
        messages.append(
            {
                "role": "assistant",
                "content": result.answer or result.clarification or "Không tìm thấy trong tài liệu.",
                "response": result,
                "sources": sources,
            }
        )
        save_chat_history(st.session_state.lesson_chats)
        st.rerun()
