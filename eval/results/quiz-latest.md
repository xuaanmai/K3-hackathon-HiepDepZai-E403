# Quiz evaluation report

- Run: `2026-07-31T01:08:44+07:00`
- Model: `gemini-3.1-flash-lite-preview`
- Scope: 2 live Gemini generations + 2 deterministic regressions
- Result: **10/10 (100.0%)**
- Quality bar: **PASS**

| ID | Kết quả | Chi tiết |
|---|:---:|---|
| QZ-001 | PASS | 10/10 câu |
| QZ-002 | PASS | 10/10 câu |
| QZ-003 | PASS | DAY1-P03, DAY1-P14, DAY1-P15, DAY1-P16, DAY1-P18, DAY1-P19, DAY1-P20, DAY1-P22, DAY1-P23, DAY1-P24, DAY1-P27, DAY1-P28, DAY1-P29 |
| QZ-004 | PASS | Buổi được cite: DAY1, DAY2 |
| QZ-005 | PASS | 20/20 câu duy nhất |
| QZ-006 | PASS | Mỗi câu có 4 option và 1 correct_label |
| QZ-007 | PASS | Không có source ID lạ |
| QZ-008 | PASS | Lexical support proxy |
| QZ-009 | PASS | Chuẩn hóa list/object, option map và answer |
| QZ-010 | PASS | score=1/3; unanswered=[2] |

## Diễn giải

- QZ-001 đến QZ-008 chấm trên hai output Gemini thật.
- QZ-009 tái hiện JSON biến thể mà Gemini từng trả.
- QZ-010 kiểm tra câu bỏ trống được ghi nhận và tính sai khi vẫn nộp.
- QZ-008 là grounding proxy lexical; đánh giá ngữ nghĩa sâu hơn vẫn cần human review.
