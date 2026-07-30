> Cấu trúc phủ đúng "SPEC 8 phần" của chương trình: Bằng chứng (§1-§2) · Lát cắt (§4) · Canvas (đính kèm CP1) · Augment/Automate (§4) · 4 đường đi của trải nghiệm (§6) · Kiểu lỗi (§5) · Kiểm thử (§7) · Phân công (§8). Hướng dẫn viết từng mục: `02-guide.md`.

```markdown
# AI SPEC — VLearn Smart Tutor · Nhóm XX · Zone X
Hướng: A — VLearn
Loại: Tối ưu tính năng có sẵn + Tính năng mới

## §1. User & Job
- Job executor + workflow (đính kèm worksheet JTBD / ảnh sơ đồ):
  + User chính: Học viên học trên nền tảng VLearn
  + Workflow hiện tại:
    Học viên xem bài học -> Có nội dung chưa hiểu hoặc muốn ôn tập -> Mở chatbot để hỏi -> Chatbot trả lời -> Học viên tự kiểm chứng xem câu trả lời có đúng với bài học hay không
- Core JTBD (không tên sản phẩm/AI trong câu): Khi học một bài học trên VLearn, tôi muốn nhận được lời giải thích chính xác dựa trên nội dung của khóa học và được kiểm tra mức độ hiểu bài ngay sau đó để học hiệu quả hơn
- Problem statement (KHÔNG chữ AI):
  Chatbot hiện tại có thể trả lời các câu hỏi của học viên nhưng chưa đảm bảo luôn dựa trên tài liệu chính thức của khóa học, khiến người học khó đánh giá độ tin cậy của câu trả lời. Đồng thời, sau khi nhận câu trả lời, học viên chưa có công cụ để tự kiểm tra mức độ hiểu bài trước khi chuyển sang nội dung tiếp theo.
- Evidence (chuẩn A và/hoặc B — log đầy đủ trong repo):
  - Số liệu mining / kết quả khảo sát (n = 21):
    + 90.5% học viên muốn chatbot trích dẫn đúng nguồn.
    + 81% học viên muốn đánh giá lại mức độ hiểu bài của bản thân sau mỗi lần học.
    + 76.2% học viên không hài lòng về chất lượng chatbot hiện tại của VLearn.
  - ≥5 quote/ví dụ nguyên văn + nguồn:
    + Không biết chatbot lấy thông tin ở đâu.
    + Mình phải mở slide để kiểm tra lại.
    + Đọc xong vẫn không biết mình hiểu chưa.
    + Nếu chatbot trích đúng bài học thì sẽ yên tâm hơn.
    + Muốn có vài câu hỏi để ôn luôn sau mỗi phần.

## §2. Impact & quyết định chọn
- Bảng impact ≥3 ứng viên (bao nhiêu người · tần suất · tốn gì mỗi lần · khả thi):
- Ứng viên ĐÃ LOẠI + vì sao:
- Ứng viên CHỌN + vì sao (bằng số):

## §3. Giải pháp tương tự đã nghiên cứu
- [Sản phẩm 1]: flow / đáng học / đáng né / mình khác gì
- [Sản phẩm 2]: ...

## §4. Thiết kế
- Lát cắt MỘT CÂU (1 user · 1 việc · 1 quyết định AI · 1 kết quả):
- Non-goals (≥3 thứ KHÔNG build):
- Mức prototype nhắm tới: [ ] Sketch [ ] Mock [ ] Working — phần nào mock, phần nào thật:
- Automation: [ ] augment [ ] conditional [ ] automate — lý do theo cost-of-error:
- §4b. Nguyên tắc đã áp dụng (≥4 — HAX/PAIR, xem guide):
  | Nguyên tắc | Áp cụ thể vào đâu trong prototype |
  |---|---|

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8) [bảng theo guide §2.5]

## §6. Bốn đường đi của trải nghiệm
- Happy path: · Low-confidence (②): · Failure/không căn cứ (①): · Correction (user sửa):
- Khi bị đòi ngoài phạm vi (③): · Case đặc thù domain (④):

## §7. Kiểm thử
- Chiều chất lượng + định nghĩa kiểm chứng được:
- Golden set (≥20 case theo cơ cấu trong guide §2.6, file trong eval/):
- Quality bar (chốt từ 23:59, giữ nguyên sau đó): "Đạt khi ≥ ___% qua bộ, và ___"
- Kết quả các lượt chạy (bảng % — cập nhật đến trước CP6):

## §8. Phân công & kế hoạch
- Phân công có tên: spec / evidence / prompt / code / demo
- Willing users (≥3 tên) + kế hoạch vòng validation CP5 (3 câu hỏi, ai log):
- Multi-prototype (nếu làm): trục khác biệt của ≥2 phương án + lý do chọn:

## §9. Changelog
| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
```
