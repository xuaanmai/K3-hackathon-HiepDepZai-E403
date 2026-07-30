# Lịch sử chạy golden set

| Lượt | Báo cáo | Pass | Trạng thái | Diễn giải |
|---|---|---:|---|---|
| 2026-07-30 17:44 | [run-20260730-174432.md](run-20260730-174432.md) | 6/22 (27,3%) | Chưa đạt | 15 runtime fail; 1 failure retrieval thật ở GS-005 |
| 2026-07-30 17:52 | [run-20260730-175231.md](run-20260730-175231.md) | 0/22 (0,0%) | Chưa đạt | 13 lỗi 503 high demand; 9 lỗi 429 quota |
| 2026-07-30 22:03 | [run-20260730-220340.md](run-20260730-220340.md) | 11/14 (78,6%) | Smoke — không chấm bar | 2 lỗi 503; GS-001 thiếu citation inline |
| 2026-07-30 22:42 | [run-20260730-224228.md](run-20260730-224228.md) | 19/22 (86,4%) | Chưa đạt safety bar | GS-010, GS-015 và GS-017 chưa đạt |
| 2026-07-30 22:49 | [run-20260730-224952.md](run-20260730-224952.md) | 3/3 (100%) | Regression subset | Ba failure GS-010, GS-015, GS-017 đã được sửa |
| 2026-07-30 23:00 | [run-20260730-230055.md](run-20260730-230055.md) | **22/22 (100%)** | **Đạt quality bar** | 100% đúng trang, citation hợp lệ và safety case pass |
| 2026-07-31 01:08 | [quiz-run-20260731-010844.md](quiz-run-20260731-010844.md) | **10/10 (100%)** | **Quiz đạt quality bar** | Hai output Gemini thật; phủ một/nhiều buổi, source, JSON và nộp trống |

## Kết luận hiện tại

- Lượt chính thức gần nhất đạt toàn bộ quality bar.
- `GS-001` đã tự bổ sung citation inline khi model khai báo nguồn hợp lệ.
- `GS-005` đã truy xuất đúng trang agenda `DAY1-P02`.
- Smoke 14 case chỉ dùng để lặp nhanh khi phát triển, không thay thế lượt chính
  thức 22 case.
- Các trace cũ được giữ nguyên để theo dõi quá trình cải tiến.
