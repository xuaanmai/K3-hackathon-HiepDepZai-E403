"""System prompt and input formatting for the Mini Quiz generator."""

from __future__ import annotations

from collections.abc import Sequence

from src.schemas import SourceChunk, TutorResponse


QUIZ_SYSTEM_PROMPT = """
Bạn là trợ lý tạo câu hỏi trắc nghiệm dựa trên NỘI DUNG ĐÃ XÁC THỰC.

NHIỆM VỤ
Tạo đúng MỘT câu hỏi trắc nghiệm kiểm tra mức độ hiểu bài của học viên.

QUY TẮC
1. Câu hỏi phải dựa hoàn toàn trên ANSWER và VERIFIED SOURCES bên dưới.
2. Tạo đúng 3 hoặc 4 lựa chọn (label A, B, C, và D nếu 4).
3. Chỉ có đúng MỘT đáp án đúng.
4. Các đáp án nhiễu phải hợp lý nhưng sai so với nội dung nguồn.
5. Giải thích ngắn gọn tại sao đáp án đúng là đúng, có trích dẫn source_id.
6. source_ids trong output chứa các SOURCE_ID được sử dụng để tạo quiz.
7. Không dùng kiến thức ngoài, không bịa thông tin.

PHONG CÁCH
- Câu hỏi rõ ràng, không mơ hồ.
- Đáp án nhiễu nên là sai lầm phổ biến hoặc hiểu nhầm thường gặp.
- Giải thích giúp học viên hiểu sâu hơn, không chỉ nói "đáp án B đúng".

ĐỊNH DẠNG OUTPUT
Trả về JSON theo schema Quiz đã cung cấp.
""".strip()


LESSON_QUIZ_SYSTEM_PROMPT = """
Bạn là trợ lý tạo bộ câu hỏi trắc nghiệm tổng hợp cho MỘT HOẶC NHIỀU BUỔI HỌC.

NHIỆM VỤ
Tạo đúng số câu hỏi được yêu cầu từ toàn bộ VERIFIED LESSON SOURCES.

QUY TẮC
1. Chỉ dùng thông tin trong nguồn được cung cấp, tuyệt đối không dùng kiến thức ngoài.
2. Phân bố câu hỏi trên nhiều phần/trang; nếu có nhiều buổi, phải phủ kiến thức
   của tất cả các buổi được cung cấp, không tập trung vào riêng một buổi.
3. Không tạo hai câu hỏi trùng ý hoặc chỉ thay cách diễn đạt.
4. Mỗi câu có đúng 4 lựa chọn A, B, C, D và chỉ một đáp án đúng.
5. Đáp án nhiễu phải hợp lý nhưng sai theo tài liệu.
6. explanation giải thích ngắn gọn, giúp người học hiểu lại kiến thức.
7. source_ids chỉ chứa SOURCE_ID thực sự hỗ trợ đáp án.
8. Không hỏi về số trang, tên file, bố cục slide hoặc chi tiết trang trí.
9. Ưu tiên câu hỏi về khái niệm, so sánh, quy trình, ứng dụng và lỗi hiểu thường gặp.

ĐỊNH DẠNG OUTPUT
Trả về JSON theo schema QuizSet đã cung cấp.
""".strip()


def format_quiz_input(
    response: TutorResponse,
    verified_sources: Sequence[SourceChunk],
) -> str:
    """Build the user-content string for the quiz generation prompt.

    Parameters
    ----------
    response:
        The validated TutorResponse (must have decision="answer").
    verified_sources:
        Only the SourceChunks whose IDs passed citation validation.
    """
    source_blocks = []
    for source in verified_sources:
        metadata = " · ".join(
            part for part in (source.lesson, source.section) if part
        )
        heading = f"[{source.source_id}]"
        if metadata:
            heading += f" {metadata}"
        source_blocks.append(f"{heading}\n{source.content}")

    joined_sources = (
        "\n\n".join(source_blocks) if source_blocks else "(không có nguồn)"
    )

    return (
        "<TUTOR_ANSWER>\n"
        f"{(response.answer or '').strip()}\n"
        "</TUTOR_ANSWER>\n\n"
        "<VERIFIED_SOURCES>\n"
        f"{joined_sources}\n"
        "</VERIFIED_SOURCES>"
    )


def format_lesson_quiz_input(
    sources: Sequence[SourceChunk],
    question_count: int,
) -> str:
    """Build the grounded input for a lesson-level quiz set."""
    source_blocks = []
    for source in sources:
        metadata = " · ".join(part for part in (source.lesson, source.section) if part)
        heading = f"[{source.source_id}]"
        if metadata:
            heading += f" {metadata}"
        source_blocks.append(f"{heading}\n{source.content}")

    return (
        f"<QUESTION_COUNT>{question_count}</QUESTION_COUNT>\n\n"
        "<VERIFIED_LESSON_SOURCES>\n"
        + "\n\n".join(source_blocks)
        + "\n</VERIFIED_LESSON_SOURCES>"
    )
