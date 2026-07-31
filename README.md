# VLearn Smart Tutor

VLearn Smart Tutor là prototype trợ lý học tập đọc đúng tài liệu PDF của khóa
học, trả lời câu hỏi có dẫn nguồn theo trang và tạo quiz tổng hợp để người học
tự kiểm tra kiến thức.

Prototype thuộc **Hướng A — VLearn**, mức **Working**. Hai quyết định AI chính
là:

1. Tutor chọn `answer`, `clarify` hoặc `not_found` dựa trên nguồn truy xuất.
2. Quiz tạo 10/20/30 câu từ một hoặc nhiều buổi học đã chọn.

## Thành viên và phân công

| Thành viên | Mã học viên | Phần phụ trách | File chính |
|---|---|---|---|
| Nguyễn Thị Xuân Mai | 2A202601691 | Xử lý transcript/PDF, làm sạch dữ liệu và chuẩn hóa source ID | `src/data_loader.py`, `scripts/prepare_data.py` |
| Cao Hữu Phúc | 2A202601283 | Embedding, Retrieval, xếp hạng nguồn và câu hỏi nối tiếp | `src/embeddings.py`, `src/retriever.py`, `scripts/build_index.py` |
| Trần Doãn Hưng | 2A202601143 | Gemini Tutor, prompt và ba decision | `src/tutor.py`, `src/prompts/tutor_prompt.py`, `src/schemas.py` |
| Ngô Khánh Trượng | 2A202601477 | Citation Guard và Quiz tổng hợp | `src/citation_guard.py`, `src/quiz.py`, `src/prompts/quiz_prompt.py` |
| Lê Tuấn Hiệp | 2A202601667 | Tích hợp Streamlit, quản lý API, test và evaluation | `streamlit_app.py`, `eval/`, `tests/` |

Chi tiết công việc nằm trong `phan-cong-cong-viec.docx`; reflection cá nhân nằm
trong `reflection/`.

## Tính năng

- Chọn Buổi 01 hoặc Buổi 02 và xem toàn bộ slide.
- Hỏi đáp nhiều lượt trên đúng PDF của buổi đang chọn.
- Citation chỉ hiển thị tên buổi và số trang, không lặp cùng một nguồn.
- Xử lý câu hỏi mơ hồ, ngoài tài liệu, tiền đề sai và prompt injection.
- Tạo quiz 10/20/30 câu từ một buổi hoặc kết hợp nhiều buổi.
- Chấm điểm, giải thích đáp án và dẫn nguồn.
- Xác nhận trước khi nộp nếu còn câu chưa trả lời.
- Lưu lịch sử chat riêng theo từng buổi trên máy đang chạy app.

## Yêu cầu môi trường

- Python 3.11 trở lên.
- Kết nối Internet để gọi Gemini.
- Gemini API key.

## Cài đặt

Mở PowerShell tại thư mục repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Hai file PDF dùng cho demo cần nằm đúng vị trí:

```text
tài liệu/
├── d1-slide-hackathon.pdf
└── d2-slide-hackathon.pdf
```

## Cấu hình `.env`

Sao chép file mẫu:

```powershell
Copy-Item .env.example .env
```

Điền cấu hình:

```dotenv
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
```

- `GEMINI_API_KEY` là bắt buộc để chạy Tutor và Quiz bằng AI thật.
- `GEMINI_MODEL` có thể đổi sang model Gemini mà tài khoản được cấp quyền.
- Không commit `.env` hoặc đưa API key vào source code.

Nếu thiếu key, giao diện chuyển sang **Local fallback** để kiểm tra flow. Kết quả
fallback không được dùng thay cho evaluation bằng Gemini thật.

## Chạy Streamlit

```powershell
python -m streamlit run streamlit_app.py
```

Mở:

```text
http://localhost:8501
```

Flow test nhanh:

1. Chọn một buổi học.
2. Chọn **Slide bài học**, đặt câu hỏi trong Smart Tutor và bấm nguồn.
3. Chọn **Quiz tổng hợp**.
4. Chọn một hoặc nhiều buổi và chọn 10/20/30 câu.
5. Tạo quiz, trả lời và nộp bài.

## Chạy unit test

Toàn bộ unit test dùng fake client, không tiêu thụ quota Gemini:

```powershell
python -m pytest -q
```

Kết quả gần nhất:

```text
39 passed
```

## Chạy golden set

Golden set Tutor gồm 22 case và cần Gemini API key:

```powershell
python eval/run_golden_set.py
```

Để giảm nguy cơ rate limit, chạy tuần tự:

```powershell
python eval/run_golden_set.py --workers 1 --delay 13
```

Chạy smoke set 14 case trong lúc phát triển:

```powershell
python eval/run_golden_set.py --smoke
```

Chạy một case:

```powershell
python eval/run_golden_set.py --case GS-001
```

Kết quả được ghi vào `eval/results/` dưới dạng JSON và Markdown. Lượt chính thức
gần nhất đạt:

- 22/22 case pass.
- 100% đúng trang nguồn.
- 100% citation hợp lệ.
- 100% safety case pass.

Smoke set chỉ dùng để phát hiện lỗi nhanh, không thay thế lượt full 22 case khi
đối chiếu quality bar.

### Quiz evaluation

Chạy 10 kiểm tra cho Quiz tổng hợp:

```powershell
python eval/run_quiz_eval.py
```

Runner dùng hai output Gemini thật — Buổi 01 và Buổi 01 + Buổi 02 — cùng hai
regression deterministic cho JSON biến thể và câu bỏ trống. Kết quả gần nhất:

```text
10/10 checks pass
Quality bar: PASS
```

## Phần chạy thật và phần fallback/mock

### Chạy thật

- Đọc và render PDF Buổi 01/Buổi 02.
- Làm sạch text và retrieval theo trang trong buổi đang chọn.
- Gemini Tutor với structured output `answer/clarify/not_found`.
- Kiểm tra source ID và citation inline.
- Chat nhiều lượt có nhớ ngữ cảnh gần.
- Gemini tạo quiz từ một hoặc nhiều buổi.
- Pydantic kiểm tra số câu, lựa chọn, đáp án và nguồn.
- Golden-set evaluation bằng Gemini thật.

### Fallback/mock hoặc chưa tích hợp

- Khi thiếu Gemini key, Tutor trả đoạn trích cục bộ và Quiz dùng câu hỏi
  deterministic để demo flow.
- `src/embeddings.py` và FAISS trong `src/retriever.py` là pipeline backend thử
  nghiệm; app Streamlit hiện dùng lexical retrieval theo trang PDF.
- Chưa có dashboard giảng viên, lưu điểm dài hạn hoặc cá nhân hóa độ khó.
- Chưa có tài khoản người dùng và đồng bộ lịch sử lên server.
- App chạy local; đề bài không yêu cầu deploy.

## Cấu trúc chính

```text
.
├── streamlit_app.py
├── src/
│   ├── tutor.py
│   ├── citation_guard.py
│   ├── quiz.py
│   ├── schemas.py
│   └── prompts/
├── tests/
├── eval/
│   ├── golden_set.json
│   └── results/
├── reflection/
├── spec.md
└── phan-cong-cong-viec.docx
```

## Tài liệu dự án

- `spec.md`: AI Spec và kết quả evaluation.
- `eval/README.md`: cách chấm golden set.
- `reflection/README.md`: reflection của năm thành viên.
- `01-de-bai.md`, `02-guide.md`, `04-rubric.md`: đề bài, hướng dẫn và rubric.

## Bảo mật

- Không commit `.env`, API key, lịch sử chat hoặc log runtime.
- Không đưa data pack riêng của khóa học vào repository công khai.
- Chỉ dùng dữ liệu được phép trong phạm vi hackathon.
