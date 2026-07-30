# Reflection — Trần Doãn Hưng

- **Mã học viên:** 2A202601143
- **Vai trò:** Người 3 — Gemini AI Tutor và quyết định ba nhánh

## Phần tôi thực hiện

Tôi phụ trách phản hồi trung tâm của Smart Tutor trong `src/tutor.py`,
`src/prompts/tutor_prompt.py` và `src/schemas.py`.

Tutor nhận câu hỏi, lịch sử hội thoại và các nguồn Retrieval đã chọn, sau đó
quyết định:

- `answer`: tài liệu có đủ căn cứ.
- `clarify`: câu hỏi chưa rõ và cần hỏi lại một câu cụ thể.
- `not_found`: tài liệu không đề cập hoặc yêu cầu nằm ngoài phạm vi.

Tôi thiết kế prompt chống yêu cầu bỏ qua tài liệu, xử lý tiền đề sai, yêu cầu
trích nguồn inline và parse output Gemini bằng Pydantic.

## AI đã hỗ trợ tôi thế nào

AI hỗ trợ tôi xây prompt ban đầu, liệt kê prompt injection và sinh unit test cho
ba decision. Tôi dùng trace thật để sửa prompt và validation, không đánh giá
chất lượng chỉ dựa trên một vài câu trả lời nhìn có vẻ hợp lý.

## Bài học từ case fail

Ở `GS-001`, Gemini khai báo citation hợp lệ trong trường `citations` nhưng quên
đưa citation inline vào câu trả lời, làm output bị guard từ chối. Ở `GS-017`,
model sửa đúng tiền đề trong nội dung nhưng bỏ trống `corrected_premise`.

Bài học của tôi là structured output vẫn có thể đúng về nghĩa nhưng lệch hợp
đồng dữ liệu. Với lỗi có thể sửa an toàn, hệ thống nên repair có kiểm soát: chỉ
bổ sung citation inline từ source ID đã được xác minh và chỉ suy ra
`corrected_premise` khi câu trả lời thực sự bắt đầu bằng một câu phủ định/sửa
sai. Không được tự sửa citation lạ hoặc tạo thêm kiến thức.

## Tôi giải thích code của mình

`answer_question()` thực hiện:

1. Chuẩn hóa và loại source ID trùng.
2. Nếu không có nguồn, trả `not_found` an toàn mà không gọi Gemini.
3. Gửi prompt, câu hỏi, lịch sử và nguồn tới Gemini.
4. Yêu cầu JSON theo schema `TutorResponse`.
5. Parse bằng Pydantic.
6. `_validate_grounding()` kiểm tra citation chỉ thuộc tập nguồn đã cung cấp.

`TutorResponse` áp hợp đồng khác nhau cho từng decision. `answer` bắt buộc có
câu trả lời và citation; `clarify` chỉ có câu hỏi làm rõ; `not_found` không được
chứa câu trả lời hoặc nguồn. Cách này giúp UI không phải đoán ý model từ văn bản
tự do.

