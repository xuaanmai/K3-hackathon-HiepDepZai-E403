# Lịch sử chạy golden set

| Lượt | Báo cáo | Pass | Trạng thái | Diễn giải |
|---|---|---:|---|---|
| 2026-07-30 17:44 | [run-20260730-174432.md](run-20260730-174432.md) | 6/22 (27,3%) | Chưa đạt | 15 runtime fail; 1 failure retrieval thật ở GS-005 |
| 2026-07-30 17:52 | [run-20260730-175231.md](run-20260730-175231.md) | 0/22 (0,0%) | Chưa đạt | 13 lỗi 503 high demand; 9 lỗi 429 quota |
| 2026-07-30 22:03 | [run-20260730-220340.md](run-20260730-220340.md) | 11/14 (78,6%) | Smoke — không chấm bar | Model mới: 2 lỗi 503; 1 lỗi định dạng citation |

## Kết luận hiện tại

- Citation guard không chấp nhận source ID lạ trong cả hai lượt.
- Lượt đầu có 7 case nhận được output hợp lệ từ model; 6 case pass. Đây chỉ là
  số chẩn đoán trên tập con, **không thay thế tỷ lệ chính thức 27,3%**.
- Failure sản phẩm quan sát được: `GS-005` lấy trang 3/4/21 thay vì trang agenda
  `DAY1-P02`.
- Failure hạ tầng chiếm đa số, vì vậy cần chạy lại toàn bộ khi quota ổn định.
- Giữ nguyên golden set, quality bar và mọi trace cũ khi chạy lượt tiếp theo.
- Smoke 14 case dùng để lặp nhanh trong lúc phát triển, không thay lượt chính
  thức 22 case mà rubric yêu cầu.
