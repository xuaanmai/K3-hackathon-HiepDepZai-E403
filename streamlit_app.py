import time
import streamlit as st

st.set_page_config(page_title="VLearn Smart Tutor", page_icon="🎓", layout="wide")

st.markdown("""
<style>
.stApp{background:#fbfcf8;color:#172126}[data-testid="stSidebar"]{background:#f1f5ef}
.brand{font-size:1.5rem;font-weight:800;color:#164d3b;margin-bottom:1.5rem}
.mark{display:inline-grid;place-items:center;width:2.3rem;height:2.3rem;background:#c9f55a;border-radius:.7rem .7rem .7rem .2rem;margin-right:.6rem}
.chapter{color:#2b735c;font-size:.75rem;font-weight:800;letter-spacing:.12em}
.title{font-family:Georgia,serif;font-size:2.8rem;line-height:1.05;margin:.4rem 0 1rem}
.lead{font-family:Georgia,serif;font-size:1.15rem;color:#59645f;line-height:1.65;margin-bottom:2rem}
.card{background:white;border:1px solid #dfe5e2;border-radius:14px;padding:1rem 1.1rem;margin:.75rem 0}
.card strong{color:#164d3b}.callout{background:#eef6dc;border-left:4px solid #88b326;padding:1rem 1.1rem;margin-top:1.2rem}
.verified,.warning{padding:.55rem .75rem;border-radius:8px;font-size:.78rem;font-weight:800;margin-bottom:.8rem}
.verified{background:#e2f3ea;color:#216a50}.warning{background:#fff0c9;color:#835f0c}
.answer{background:white;border:1px solid #dfe5e2;border-radius:14px;padding:1.1rem;margin-top:.8rem}
.source{background:#f0f6f3;color:#164d3b;padding:.8rem;border-radius:9px;margin-top:.9rem}
.quiz{background:#f7f3e9;border:1px solid #eadfc8;border-radius:14px;padding:1.1rem;margin-top:1rem}
.quiz-label{display:inline-block;background:#fb8b71;padding:.25rem .45rem;border-radius:5px;font-size:.72rem;font-weight:900}
.note{color:#758079;font-size:.78rem;text-align:center;margin-top:1rem}
</style>
""", unsafe_allow_html=True)

SUGGESTIONS = {
    "Có căn cứ": "RAG giúp mô hình trả lời chính xác hơn như thế nào?",
    "Câu hỏi mơ hồ": "Giải thích đoạn này đi",
    "Ngoài tài liệu": "Làm sao chữa bệnh mất ngủ bằng AI?",
}

def classify(question: str) -> str:
    text = question.lower()
    if any(x in text for x in ("mất ngủ", "chữa bệnh", "bitcoin", "thời tiết")):
        return "unsupported"
    if len(question.strip()) < 14 or any(x in text for x in ("cái này", "đoạn này", "nó là gì")):
        return "ambiguous"
    return "grounded"

with st.sidebar:
    st.markdown('<div class="brand"><span class="mark">V</span>VLearn</div>', unsafe_allow_html=True)
    st.caption("NỘI DUNG BÀI HỌC")
    st.subheader("Xây dựng hệ thống RAG")
    st.markdown("✅ 01 · Tổng quan")
    st.markdown("🟢 **02 · Retrieval-Augmented Generation**")
    st.markdown("⬜ 03 · Chunking tài liệu")
    st.markdown("⬜ 04 · Đánh giá hệ thống")
    st.divider()
    st.caption("Tiến độ bài học · 3/4 phần")
    st.progress(0.75)
    st.divider()
    st.caption("KỊCH BẢN TEST NHANH")
    for label, prompt in SUGGESTIONS.items():
        if st.button(label, use_container_width=True):
            st.session_state.question = prompt
            st.session_state.submitted = prompt
            st.session_state.quiz_answer = None
            st.rerun()

lesson_col, tutor_col = st.columns([1.15, .85], gap="large")

with lesson_col:
    st.markdown('<div class="chapter">02 · KHÁI NIỆM CỐT LÕI</div>', unsafe_allow_html=True)
    st.markdown('<div class="title">Retrieval-Augmented<br>Generation</div>', unsafe_allow_html=True)
    st.markdown('<div class="lead">RAG kết hợp khả năng sinh ngôn ngữ của mô hình với một bước truy xuất thông tin từ nguồn dữ liệu bên ngoài.</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><strong>1 · Retrieve — Tìm thông tin liên quan</strong><br>Hệ thống tìm những đoạn tài liệu liên quan nhất trong kho kiến thức.</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><strong>2 · Augment — Bổ sung ngữ cảnh</strong><br>Những đoạn tìm được được đưa vào prompt làm ngữ cảnh. Mô hình không “học lại”.</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><strong>3 · Generate — Tạo câu trả lời</strong><br>Mô hình tổng hợp câu trả lời dựa trên câu hỏi và ngữ cảnh được truy xuất.</div>', unsafe_allow_html=True)
    st.markdown('<div class="callout"><strong>Điểm cần nhớ</strong><br>RAG không đảm bảo câu trả lời luôn đúng. Hệ thống cần từ chối khi không đủ căn cứ.</div>', unsafe_allow_html=True)

with tutor_col:
    st.subheader("✦ Smart Tutor")
    st.caption("🟢 Chỉ dùng tài liệu chính thức của khóa học")
    st.session_state.setdefault("question", SUGGESTIONS["Có căn cứ"])
    st.session_state.setdefault("submitted", SUGGESTIONS["Có căn cứ"])
    st.session_state.setdefault("quiz_answer", None)

    with st.form("question_form"):
        question = st.text_area("Hỏi về nội dung đang học", value=st.session_state.question, height=90)
        send = st.form_submit_button("Gửi câu hỏi", type="primary", use_container_width=True)
    if send and question.strip():
        with st.spinner("Đang kiểm tra tài liệu chính thức..."):
            time.sleep(.5)
        st.session_state.question = question.strip()
        st.session_state.submitted = question.strip()
        st.session_state.quiz_answer = None

    current = st.session_state.submitted
    st.markdown(f"**Bạn:** {current}")
    scenario = classify(current)

    if scenario == "unsupported":
        st.markdown('<div class="answer"><div class="warning">⚠ KHÔNG CÓ ĐỦ CĂN CỨ</div><h3>Tài liệu không đề cập.</h3><p>Mình không tìm thấy nội dung đủ tin cậy trong bài học. Mình sẽ không sử dụng kiến thức ngoài hoặc tự suy đoán.</p></div>', unsafe_allow_html=True)
        st.button("Sao chép câu hỏi để hỏi TA", use_container_width=True)
    elif scenario == "ambiguous":
        st.markdown('<div class="answer"><div class="warning">? CẦN THÊM NGỮ CẢNH</div><h3>Bạn muốn mình giải thích phần nào?</h3><p>“Đoạn này” có thể là Retrieve, Augment hoặc Generate.</p></div>', unsafe_allow_html=True)
        part = st.radio("Chọn phần", ["Retrieve", "Augment", "Generate"], horizontal=True)
        if st.button("Dùng lựa chọn này"):
            new_question = f"Giải thích bước {part} trong RAG"
            st.session_state.question = new_question
            st.session_state.submitted = new_question
            st.rerun()
    else:
        st.markdown('<div class="answer"><div class="verified">✓ CÓ CĂN CỨ TRONG BÀI HỌC</div><p>RAG giúp câu trả lời bám sát tài liệu bằng cách <strong>tìm các đoạn liên quan trước</strong>, đưa chúng vào ngữ cảnh, rồi mới yêu cầu mô hình tạo câu trả lời.</p><p>Nếu nguồn không có thông tin, hệ thống nên nói rõ chưa đủ căn cứ thay vì suy diễn.</p><div class="source"><strong>§ Bài 04 · RAG là gì?</strong><br>Đoạn 02.1–02.3</div></div>', unsafe_allow_html=True)
        with st.expander("Xem nguyên văn đoạn nguồn"):
            st.info("“Khi nhận câu hỏi, hệ thống tìm những đoạn tài liệu có liên quan nhất… Những đoạn tìm được được đưa vào prompt làm ngữ cảnh.”")

        st.markdown('<div class="quiz"><span class="quiz-label">MINI QUIZ</span>', unsafe_allow_html=True)
        st.markdown("#### Điều nào mô tả đúng nhất vai trò của RAG?")
        answers = ["Huấn luyện lại mô hình sau mỗi câu hỏi", "Cung cấp ngữ cảnh liên quan trước khi tạo câu trả lời", "Đảm bảo mọi câu trả lời đều chính xác"]
        choice = st.radio("Chọn đáp án", answers, index=None, key="quiz_choice", label_visibility="collapsed")
        if st.button("Kiểm tra đáp án", use_container_width=True):
            st.session_state.quiz_answer = choice
        if st.session_state.quiz_answer:
            if st.session_state.quiz_answer == answers[1]:
                st.success("Chính xác! RAG bổ sung ngữ cảnh; mô hình không được huấn luyện lại.")
            else:
                st.error("Chưa đúng. Hãy xem lại bước Augment ở đoạn 02.2.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="note">Prototype dùng mock data — chưa gọi OpenAI API.</div>', unsafe_allow_html=True)
