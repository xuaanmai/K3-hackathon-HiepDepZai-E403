# Reflection — Lê Tuấn Hiệp

- **Mã học viên:** 2A202601667
- **Vai trò:** Người 5 — tích hợp pipeline, API và Evaluation

## Phần tôi thực hiện

Tôi phụ trách nối dữ liệu, Retrieval, Tutor, Citation Guard và Quiz vào
`streamlit_app.py`; quản lý cấu hình Gemini; xây golden set và runner trong
`eval/`; phối hợp các unit test trong `tests/`.

Prototype cho phép chọn buổi học, xem toàn bộ slide, hỏi đáp nhiều lượt trên đúng
PDF, bấm nguồn theo trang và tạo quiz 10/20/30 câu từ một hoặc nhiều buổi. Tôi
cũng lưu lịch sử chat theo từng buổi và xử lý lỗi API để UI không bị crash.

## AI đã hỗ trợ tôi thế nào

AI hỗ trợ tôi phân tích log, viết runner, tổng hợp báo cáo Markdown/JSON và đề
xuất các case regression. Tôi kiểm tra bằng unit test, health check và lời gọi
Gemini thật. Các lượt lỗi vẫn được giữ trong `eval/results/` thay vì chỉ giữ kết
quả đẹp.

## Bài học từ case fail

Lượt evaluation đầu gặp nhiều lỗi `429/503`; sau đó Streamlit gặp
`WinError 10013` vì tiến trình bị chặn socket. Có thời điểm test logic pass nhưng
app thật vẫn không gọi được Gemini. Khi đổi model và chạy lại full golden set,
nhóm mới xác nhận được 22/22 case.

Bài học của tôi là phải phân biệt failure sản phẩm với failure hạ tầng. Key đúng
không có nghĩa mạng, quota và model đều sẵn sàng. Cần health check, trace lỗi,
retry có giới hạn và một lượt end-to-end thật. Không nên sửa quality bar sau khi
thấy kết quả thấp; phải giữ trace và phân tích nguyên nhân.

## Tôi giải thích code của mình

Trong `streamlit_app.py`, luồng hỏi đáp là:

1. Nạp và làm sạch từng trang PDF.
2. Retrieval chọn các trang liên quan trong đúng buổi.
3. `answer_question()` gọi Gemini và trả `TutorResponse`.
4. UI render theo `answer/clarify/not_found`, gom citation thành liên kết trang.
5. Lịch sử được lưu theo buổi để hỗ trợ câu hỏi nối tiếp.

Luồng quiz gộp trang của các buổi được chọn thành `SourceChunk`, gọi
`generate_lesson_quiz()`, lưu bộ câu hỏi theo khóa phạm vi và chấm toàn bộ một
lần.

`eval/run_golden_set.py` chạy từng case, retrieval nguồn, gọi Tutor, so decision,
trang nguồn, citation và điều kiện safety. Runner ghi mọi kết quả ra JSON/Markdown
và chỉ tuyên bố đạt khi pass rate, source accuracy, citation và safety đồng thời
vượt quality bar. Lượt chính thức gần nhất đạt 22/22.

