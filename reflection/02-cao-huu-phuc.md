# Reflection — Cao Hữu Phúc

- **Mã học viên:** 2A202601283
- **Vai trò:** Người 2 — Embedding và Retrieval

## Phần tôi thực hiện

Tôi phụ trách tìm đúng đoạn/trang tài liệu cho câu hỏi của người học. Các file
chính là `src/embeddings.py`, `src/retriever.py`, `scripts/build_index.py` và
phần retrieval theo trang trong `streamlit_app.py`.

Công việc gồm:

- Sinh embedding và cache theo model + nội dung để không gọi API lại.
- Chuẩn hóa vector và tìm kiếm cosine similarity bằng FAISS.
- Trả top nguồn kèm `source_id`, nội dung và điểm liên quan.
- Hỗ trợ ngưỡng điểm để loại nguồn quá yếu.
- Kết hợp câu hỏi hiện tại với lịch sử gần cho câu hỏi nối tiếp.
- Bổ sung trọng số cho intent đặc biệt như agenda/tổng quan.

## AI đã hỗ trợ tôi thế nào

AI hỗ trợ tôi phân tích các trace retrieval sai, đề xuất cách so sánh token và
viết test cho top-k, ngưỡng điểm, cache và câu hỏi nối tiếp. Tôi kiểm tra lại đề
xuất bằng golden case và chỉ giữ thay đổi làm tăng độ đúng trang mà không phá
các case đã pass.

## Bài học từ case fail

`GS-005` hỏi nội dung/agenda của buổi học nhưng Retrieval không lấy trang agenda,
mà lấy các trang có vài từ trùng rời rạc. Một failure khác là `GS-010`, khi từ
`patterns` trong câu hỏi không khớp `pattern` trên slide.

Bài học của tôi là retrieval không chỉ là đếm từ trùng. Cần chuẩn hóa token,
xử lý biến thể số nhiều và nhận diện một số intent có cấu trúc. Tuy nhiên boost
chỉ nên áp dụng cho tín hiệu rõ ràng; nếu boost quá rộng, hệ thống sẽ luôn ưu
tiên agenda dù câu hỏi hỏi chi tiết.

## Tôi giải thích code của mình

Trong `src/embeddings.py`, `_key()` băm model và nội dung để tạo khóa cache.
`embed_texts()` chỉ gọi API cho cache miss rồi trả vector theo đúng thứ tự input.

Trong `src/retriever.py`, `Retriever._load()` nạp FAISS index và metadata một
lần. `retrieve()`:

1. Từ chối câu hỏi rỗng.
2. Embed câu hỏi và chuẩn hóa L2.
3. Tìm top-k bằng FAISS.
4. Loại kết quả dưới ngưỡng.
5. Trả nguồn và điểm cosine.

Prototype Streamlit dùng thêm lexical retrieval theo trang PDF. `tokenize()`
chuẩn hóa token, còn `retrieve_from_lesson()` đặt trọng số lớn hơn cho câu hỏi
hiện tại; lịch sử chỉ hỗ trợ giải đại từ, không thay thế nội dung nguồn.

