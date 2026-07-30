
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

<!-- ## §2. Impact & quyết định chọn
- Bảng impact ≥3 ứng viên (bao nhiêu người · tần suất · tốn gì mỗi lần · khả thi):
- Ứng viên ĐÃ LOẠI + vì sao:
- Ứng viên CHỌN + vì sao (bằng số): -->
## §2. Impact & Quyết định chọn

### Bảng Impact

| Ứng viên | Người bị ảnh hưởng | Tần suất | Chi phí mỗi lần | Khả thi (6 tuần) |
|----------|-------------------:|---------:|----------------:|:----------------:|
| **Tối ưu chatbot với trích dẫn đúng nguồn** | ~100% học viên sử dụng chatbot | Mỗi lần đặt câu hỏi | 3–10 phút để mở lại tài liệu kiểm chứng, có nguy cơ hiểu sai nếu tin vào câu trả lời | ⭐⭐⭐⭐⭐ |
| **Tạo Mini Quiz sau mỗi phần học** | ~100% học viên | Sau mỗi lần hoàn thành một phần bài học | 5–15 phút tự ôn tập hoặc không biết mình đã nắm được kiến thức đến đâu | ⭐⭐⭐⭐⭐ |
| **Cá nhân hóa lộ trình học** | Học viên học trong thời gian dài | 1–2 lần/tuần | Mất thời gian lựa chọn nội dung học tiếp theo, hiệu quả phụ thuộc dữ liệu lịch sử | ⭐⭐⭐☆☆ |

---

### Ứng viên ĐÃ LOẠI + vì sao

#### Cá nhân hóa lộ trình học

**Lý do loại:**

- Cần thu thập và phân tích dữ liệu học tập trong thời gian dài để đưa ra gợi ý chính xác.
- Khó đánh giá hiệu quả trong phạm vi prototype 6 tuần.
- Không giải quyết trực tiếp hai vấn đề được học viên phản ánh nhiều nhất là **độ tin cậy của chatbot** và **khả năng tự đánh giá sau khi học**.

---

### Ứng viên CHỌN + vì sao (bằng số)

#### Chọn: Tối ưu chatbot với trích dẫn đúng nguồn và tạo Mini Quiz sau mỗi phần học.

**Lý do lựa chọn:**

- **90,5%** học viên mong muốn chatbot **trích dẫn đúng nguồn** để tăng độ tin cậy của câu trả lời.
- **81,0%** học viên muốn có **Mini Quiz** để tự đánh giá mức độ hiểu bài sau mỗi lần học.
- **76,2%** học viên **không hài lòng** với chất lượng chatbot hiện tại của VLearn.
- Hai tính năng này trực tiếp giải quyết hai pain point có tỷ lệ đồng thuận cao nhất trong khảo sát.
- Có thể triển khai trong **6 tuần** bằng cách sử dụng RAG trên tài liệu chính thức kết hợp LLM để sinh Mini Quiz từ nội dung vừa học.
- Giá trị mang lại rõ ràng cho cả học viên và giảng viên:
  - Học viên nhận được câu trả lời có căn cứ và biết ngay mức độ tiếp thu.
  - Giảng viên giảm số câu hỏi lặp lại và tăng mức độ tin cậy của chatbot.

## §3. Giải pháp tương tự đã nghiên cứu
- [Sản phẩm 1]: flow / đáng học / đáng né / mình khác gì
- [Sản phẩm 2]: ...

<!-- ## §4. Thiết kế
- Lát cắt MỘT CÂU (1 user · 1 việc · 1 quyết định AI · 1 kết quả): Một học viên đang đọc tài liệu trên VLearn · hỏi chatbot về nội dung vừa đọc · AI quyết định câu trả lời có đủ căn cứ từ tài liệu chính thức hay không · trả về câu trả lời kèm trích dẫn đúng nguồn và tạo mini quiz để kiểm tra mức độ hiểu bài, hoặc thông báo "tài liệu không đề cập
- Non-goals (≥3 thứ KHÔNG build):
  + Không trả lời các câu hỏi nằm ngoài phạm vi tài liệu chính thức của khóa học.
  + Không tự suy diễn hoặc bổ sung kiến thức không có trong nguồn tài liệu.
  + Không thay thế giảng viên hoặc TA trong việc giải đáp các câu hỏi chuyên sâu.
  + Không cá nhân hóa lộ trình học hoặc gợi ý khóa học tiếp theo.
  + Không chấm điểm hay lưu trữ kết quả học tập của học viên.
- Mức prototype nhắm tới: [ ] Sketch [ ] Mock [ ] Working — phần nào mock, phần nào thật:
- Automation: [ ] augment [ ] conditional [ ] automate — lý do theo cost-of-error:
- §4b. Nguyên tắc đã áp dụng (≥4 — HAX/PAIR, xem guide):
  | Nguyên tắc | Áp cụ thể vào đâu trong prototype |
  |---|---| -->

## §4. Thiết kế

### Lát cắt MỘT CÂU

> Một học viên đang đọc tài liệu trên VLearn · hỏi chatbot về nội dung vừa đọc · AI quyết định câu trả lời có đủ căn cứ từ tài liệu chính thức hay không · trả về câu trả lời kèm trích dẫn đúng nguồn và tạo Mini Quiz để kiểm tra mức độ hiểu bài, hoặc thông báo **"Tài liệu không đề cập."**

---

### Non-goals (KHÔNG build)

- Không trả lời các câu hỏi nằm ngoài phạm vi tài liệu chính thức của khóa học.
- Không tự suy diễn hoặc bổ sung kiến thức không có trong nguồn tài liệu.
- Không thay thế giảng viên hoặc TA trong việc giải đáp các câu hỏi chuyên sâu.
- Không cá nhân hóa lộ trình học hoặc gợi ý khóa học tiếp theo.
- Không chấm điểm hay lưu trữ kết quả học tập của học viên.

---

### Mức prototype nhắm tới

- [ ] Sketch
- [ ] Mock
- [x] Working

**Phần hoạt động thật**
- Chatbot truy xuất nội dung từ tài liệu chính thức (RAG).
- Trả lời câu hỏi kèm trích dẫn đúng nguồn (tên tài liệu, chương/trang hoặc mục).
- Thông báo "Tài liệu không đề cập" khi không tìm thấy căn cứ.
- Sinh Mini Quiz từ đúng nội dung vừa được sử dụng để trả lời.

**Phần mock**
- Dashboard thống kê kết quả làm Mini Quiz.
- Theo dõi tiến độ học tập dài hạn.
- Cá nhân hóa độ khó của Mini Quiz theo năng lực từng học viên.

---

### Automation

- [ ] Augment
- [x] Conditional
- [ ] Automate

**Lý do theo cost-of-error**

Việc trả lời sai kiến thức hoặc trích dẫn sai nguồn có thể khiến học viên hiểu sai nội dung bài học. Vì vậy, AI chỉ được phép tự động trả lời khi tìm thấy thông tin trong tài liệu chính thức. Nếu không có đủ căn cứ, hệ thống sẽ từ chối trả lời và thông báo **"Tài liệu không đề cập"** thay vì tự suy diễn. Mini Quiz cũng chỉ được sinh từ nội dung đã được xác thực.

---

## §4b. Nguyên tắc đã áp dụng

| Nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|
| **Appropriate Trust & Reliance (HAX)** | Chatbot luôn hiển thị trích dẫn nguồn (tài liệu, chương, trang/mục) để học viên có thể kiểm chứng câu trả lời. |
| **Uncertainty Disclosure (PAIR)** | Khi không tìm thấy thông tin trong tài liệu chính thức, chatbot trả lời rõ **"Tài liệu không đề cập"** thay vì suy đoán. |
| **Explainability (PAIR)** | Mỗi câu trả lời đều nêu rõ căn cứ được sử dụng và liên kết đến đúng phần của tài liệu. |
| **Human-in-the-loop (PAIR)** | Với câu hỏi ngoài phạm vi tài liệu hoặc có độ tin cậy thấp, chatbot đề nghị học viên liên hệ giảng viên/TA thay vì tự trả lời. |
| **Progressive Disclosure (HAX)** | Sau khi trả lời, chatbot chỉ sinh Mini Quiz liên quan đến đúng phần kiến thức vừa hỏi, tránh đưa quá nhiều thông tin cùng lúc. |
| **Error Prevention (HAX)** | Chỉ sử dụng tài liệu chính thức làm nguồn tri thức, không kết hợp kiến thức bên ngoài để hạn chế hallucination. |

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
