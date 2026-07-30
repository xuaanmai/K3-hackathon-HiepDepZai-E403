# Reflection — Nguyễn Thị Xuân Mai

- **Mã học viên:** 2A202601691
- **Vai trò:** Người 1 — xử lý dữ liệu transcript và chuẩn hóa nguồn

## Phần tôi thực hiện

Tôi phụ trách biến transcript/PDF đầu vào thành dữ liệu có cấu trúc để Retrieval
và Tutor sử dụng. Phần chính nằm ở `src/data_loader.py` và
`scripts/prepare_data.py`:

- Đọc các transcript theo đúng thứ tự.
- Tách nội dung dựa trên mã nguồn như `T01-003`.
- Làm sạch Markdown và khoảng trắng nhưng giữ nguyên ý nghĩa.
- Gắn `source_id`, `lesson`, `section` và `content`.
- Phát hiện chunk rỗng, trùng nội dung hoặc quá dài.
- Xuất dữ liệu chuẩn hóa thành JSON cho các module sau.

Tôi cũng phối hợp kiểm tra việc đọc PDF trong `streamlit_app.py`, vì nguồn của
prototype cuối là các trang slide `DAY1-Pxx` và `DAY2-Pxx`.

## AI đã hỗ trợ tôi thế nào

AI hỗ trợ tôi đề xuất biểu thức chính quy để nhận diện source ID, gợi ý các case
biên khi làm sạch Markdown và tạo khung kiểm tra chunk rỗng/trùng/quá dài. Tôi
không dùng kết quả một cách tự động: tôi đối chiếu output với transcript gốc,
kiểm tra source ID và bảo đảm bước làm sạch không xóa mất nội dung có ý nghĩa.

## Bài học từ case fail

Khi đọc PDF, thư viện liên tục cảnh báo `Could not get FontBBox...` và một số
dòng bị dính ký tự watermark hoặc sai thứ tự. Nếu coi text extraction là nguồn
hoàn hảo, Retrieval có thể lấy sai nội dung dù PDF nhìn bằng mắt vẫn đúng.

Bài học của tôi là dữ liệu đầu vào cần được kiểm tra cả về cấu trúc lẫn nghĩa.
Warning về font không nhất thiết làm chương trình dừng, nhưng phải có bước làm
sạch, source ID ổn định và cho người học mở lại đúng trang slide để kiểm chứng.

## Tôi giải thích code của mình

Luồng trong `src/data_loader.py` là:

1. `load_chunks()` tìm tất cả transcript.
2. `parse_transcript_file()` tìm mã đoạn và cắt nội dung giữa hai mã liên tiếp.
3. `infer_section()` lấy tiêu đề gần nhất làm metadata.
4. `clean_text()` bỏ ký hiệu Markdown và chuẩn hóa khoảng trắng.
5. `validate_chunks()` loại chunk rỗng/trùng và báo chunk dài.
6. `save_chunks()` ghi JSON UTF-8 để không mất tiếng Việt.

Điều quan trọng nhất là `source_id` không được thay đổi tùy tiện, vì Retrieval,
Tutor, Citation Guard và evaluation đều dùng nó làm khóa để kiểm chứng nguồn.

