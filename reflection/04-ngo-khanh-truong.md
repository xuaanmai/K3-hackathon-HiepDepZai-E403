# Reflection — Ngô Khánh Trượng

- **Mã học viên:** 2A202601477
- **Vai trò:** Người 4 — Citation Guard và Quiz tổng hợp

## Phần tôi thực hiện

Tôi phụ trách kiểm tra nguồn của câu trả lời và sinh quiz trong
`src/citation_guard.py`, `src/quiz.py`, `src/prompts/quiz_prompt.py` cùng các
schema `Quiz`/`QuizSet`.

Citation Guard kiểm tra citation có tồn tại, có nằm trong nguồn Retrieval và có
được dùng inline. Quiz cho phép chọn 10/20/30 câu, lấy kiến thức từ một hoặc
nhiều buổi, có bốn lựa chọn, đúng một đáp án và giải thích kèm nguồn.

## AI đã hỗ trợ tôi thế nào

AI hỗ trợ tôi đề xuất schema, prompt tạo đáp án nhiễu và các test cho citation
giả, thiếu nguồn, sai số lựa chọn và JSON lỗi. Tôi dùng Pydantic và kiểm tra
source ID phía ứng dụng để không phụ thuộc hoàn toàn vào việc model tuân thủ
prompt.

## Bài học từ case fail

Khi tạo bộ quiz, Gemini từng trả `400 INVALID_ARGUMENT` vì schema lồng sâu.
Sau khi bỏ schema khỏi request và vẫn yêu cầu JSON, model lại trả nhiều biến thể:
mảng câu hỏi thay vì object, `options` dạng `{A: ...}`, trường `answer` thay cho
`correct_label`, thậm chí metadata bị đặt nhầm trong `options`.

Bài học của tôi là output của AI cần một lớp tương thích và một lớp validation
tách biệt. Lớp tương thích chỉ chuẩn hóa các biến thể tương đương; Pydantic và
post-validation vẫn phải từ chối câu thiếu, nguồn giả, đáp án không thuộc A–D
hoặc số lượng không đúng yêu cầu.

## Tôi giải thích code của mình

`validate_citations()` xây tập source ID hợp lệ, trích citation inline và tạo
`ValidationResult`. Quiz đơn chỉ được sinh sau khi Citation Guard pass.

`generate_lesson_quiz()`:

1. Chỉ chấp nhận số lượng 10, 20 hoặc 30.
2. Nhận toàn bộ `SourceChunk` của các buổi đã chọn.
3. Gọi Gemini ở chế độ JSON.
4. `_normalize_lesson_quiz_payload()` chuẩn hóa object/mảng, option map và tên
   trường đáp án.
5. `QuizSet` kiểm tra cấu trúc và câu hỏi trùng.
6. `_post_validate_quiz_set()` kiểm tra đúng số câu và mọi `source_id` đều thuộc
   tài liệu đã cung cấp.

Khi người học nộp bài còn câu trống, UI yêu cầu xác nhận; nếu vẫn nộp, câu trống
được tính sai nhưng các đáp án đã chọn được giữ nguyên.

