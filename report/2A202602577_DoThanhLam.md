# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                        |
| ------------------ | --------------------------------------------------------------- |
| Họ và tên       | Đỗ Thanh Lâm                                                   |
| MSSV               | 2A202602577                                                     |
| Khóa/Lớp         | K4 / L3                                                         |
| Tên nhóm         | KKAL                                                            |
| Vai trò chính    | Data Foundation & Recovery                                      |
| Repository         | https://github.com/AnNguyen05092004/K4-L3-DAY10-KKAL-DataPipeline |
| Ngày hoàn thành | 2026-09-25                                                      |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Raw ingestion | `src/ingestion/crossref.py` — `fetch_papers()`, `save_raw()` | Crossref API endpoint / offline snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Cleaning & data modeling | `src/ingestion/cleaning.py` — `clean_papers()`, `build_text_for_embedding()` | `crossref_records.json` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Idempotent repair | `src/ingestion/cleaning.py` — `repair_from_raw()` | `crossref_records.json` (raw, không sửa) | Repaired `papers_clean.csv` để nạp lại vào ChromaDB | Hoàn thành |

Module embedding (Khuyến) và evaluation (An) phụ thuộc trực tiếp vào `papers_clean.json` và schema `text_for_embedding` tôi định nghĩa. Nếu schema thay đổi, tôi phải thông báo để họ cập nhật code tương ứng.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------------ | --------- |
| Giải thích schema PaperRecord và ý nghĩa từng trường | Trần Ngọc Khuyến (embedding), Nguyễn Văn An (evaluation) | Hai thành viên hiểu đúng contract, không xảy ra KeyError ở downstream |
| Kiểm tra dữ liệu repair khớp baseline | Đoàn Bá Khải (pipeline orchestrator) | Confirm SHA-256 khớp, repair idempotent |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ----------------------- | ----------------------- |
| Fetch raw data từ Crossref | `src/ingestion/crossref.py` | `data/raw/crossref_response.json` (raw API response), `crossref_records.json` (24 parsed records) | File tồn tại, JSON hợp lệ |
| Cleaning & chuẩn hóa | `src/ingestion/cleaning.py` | `data/clean/papers_clean.csv` — 24 rows, 8 cột | `pandas read_csv` không báo lỗi; GX row count PASS |
| Tạo `text_for_embedding` | `build_text_for_embedding()` | Cột `text_for_embedding` trong CSV và JSON | Không có giá trị null trong cột này |
| Repair idempotent | `repair_from_raw()` | Repaired dataset SHA-256 khớp baseline | `data/results/repair_verification.json` |

Output cụ thể: `data/clean/papers_clean.csv` có 24 rows, không null ở `title`, `summary`, `paper_id`, `text_for_embedding`. SHA-256 của repaired dataset bằng SHA-256 của baseline dataset — xác nhận trong `data/results/repair_verification.json`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref API trả về JSON thô với cấu trúc lồng nhau, nhiều trường tùy chọn có thể thiếu (abstract, author list, publication date). Cần parse an toàn, chuẩn hóa và tạo chuỗi `text_for_embedding` phù hợp cho MiniLM.

Ngoài ra, repair pipeline phải idempotent: chạy lại từ raw data bao nhiêu lần cũng cho ra cùng kết quả, không phụ thuộc vào trạng thái trung gian của file bị corrupt.

### Cách triển khai

`fetch_papers()` gọi Crossref API với retry 3 lần, exponential backoff 1s/2s/4s. Nếu gặp `429 Too Many Requests` hoặc mạng lỗi, tự động fallback sang đọc file `data/raw/crossref_response.json`.

`clean_papers()` thực hiện: (1) strip JATS/HTML tags bằng regex, (2) decode Unicode entities, (3) collapse whitespace, (4) loại bỏ record không có `title` hoặc `abstract`, (5) deduplicate theo `paper_id` (DOI), (6) tính `age_days` = ngày hôm nay − `published`, (7) điền fallback cho trường thiếu.

`build_text_for_embedding()` ghép: `"Title: {title} | Authors: {authors_joined} | Published: {published} | Categories: {categories_joined} | Summary: {summary}"`. Cấu trúc 5 phần này giúp MiniLM encode đủ context metadata và nội dung semantic.

`repair_from_raw()` chỉ đọc từ `data/raw/crossref_records.json`, không chạm vào bất kỳ file derived nào. Gọi lại toàn bộ cleaning pipeline, ghi `papers_clean.csv` và `papers_clean.json` đè lên version bị corrupt.

### Input, output và contract

| Thành phần                   | Mô tả |
| ------------------------------ | ------- |
| Input                          | `data/raw/crossref_response.json` (raw API response JSON) hoặc live Crossref API |
| Output                         | `data/raw/crossref_records.json` (list of PaperRecord dicts), `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` |
| Module phụ thuộc             | Crossref REST API / offline snapshot; `src/core/config.py` cho paths |
| Module sử dụng output        | `src/retrieval/` (Khuyến đọc `papers_clean.json`); `src/observability/quality.py` (An đọc `papers_clean.csv`) |
| Điều kiện lỗi cần xử lý | API rate limit 429 (→ fallback), missing `abstract` field (→ loại record), encoding error (→ strip và normalize) |

### Cách xác minh

```bash
python script/run_phase1.py
```

- **Kết quả mong đợi:** `data/clean/papers_clean.csv` tồn tại với 24 rows, không null ở cột bắt buộc.
- **Kết quả thực tế:** File tồn tại, `pandas.read_csv().shape == (24, 8)`, GX quality check PASS.
- **Artifact/log:** `data/clean/papers_clean.csv`, `data/quality/baseline_quality_report.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Crossref snapshot không có subject labels (field `subject` trống). Cần quyết định điền `categories_joined` như thế nào để không mislead embedding.
- **Các phương án đã cân nhắc:**
  1. Loại bỏ hoàn toàn field `categories_joined` khỏi `text_for_embedding`.
  2. Điền `"Uncategorized"` làm giá trị fallback minh bạch.
- **Phương án đã chọn:** Điền `"Uncategorized"`.
- **Lý do:** Loại bỏ hoàn toàn sẽ phá vỡ contract với module embedding (Khuyến) đã expect đủ 5 phần trong `text_for_embedding`. Hơn nữa, `"Uncategorized"` là giá trị có ngữ nghĩa rõ ràng, dễ phát hiện và thay thế khi có dữ liệu thật. Token này cũng không mislead MiniLM vì nó quá phổ biến nên ảnh hưởng embedding rất nhỏ.
- **Bằng chứng:** Baseline `retrieval_hit_rate` = 1.0 dù categories đều là "Uncategorized" — chứng tỏ 4 phần còn lại (title, authors, published, summary) đủ để retrieval chính xác.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe2 in position 142` khi đọc Crossref response.
- **Lệnh tái hiện:** `python script/run_phase1.py` với raw response có ký tự Unicode đặc biệt trong abstract.
- **Nguyên nhân gốc:** Crossref API trả về một số abstract có ký tự Unicode nằm ngoài ASCII range (ví dụ: dấu `−` (U+2212) thay vì `-`, ký tự subscript trong công thức). File được đọc không chỉ định encoding.
- **Cách xử lý:** Thêm `encoding='utf-8'` khi đọc/ghi file, thêm bước `unicodedata.normalize('NFKC', text)` trước khi strip HTML để chuẩn hóa các ký tự Unicode tương đương.
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_phase1.py` — exit code 0, `papers_clean.csv` đọc được bằng `pandas.read_csv()`.
- **Điều học được:** Luôn chỉ định encoding khi đọc/ghi file text trong Python, và normalize Unicode trước khi xử lý text từ API nước ngoài.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu từ Crossref đến vector index:** Tôi fetch raw JSON từ API (hoặc offline snapshot), parse thành list of `PaperRecord` dict, cleaning module strip HTML và tạo `text_for_embedding`. Khuyến đọc `papers_clean.json`, tạo embedding vector bằng MiniLM và nạp vào ChromaDB với `paper_id` làm document ID.

2. **Evaluation set và ground-truth:** An sinh 10 câu từ cleaned dataset, mỗi câu kèm `ground_truth_doc_ids`. Retrieval trả `top_k=5` documents; hit nếu `paper_id` của ground truth nằm trong kết quả. Token F1 đo overlap từ vựng giữa câu trả lời retrieved và ground truth text.

3. **Quality checks vs freshness:** Quality checks (GX 1.x) kiểm tra tính đúng đắn của schema tại thời điểm hiện tại (row count, null, unique, length). Freshness check kiểm tra `age_days` — bao nhiêu % records đã quá cũ so với ngưỡng 180 ngày — để phát hiện khi data source lâu không được cập nhật.

4. **Cùng test set:** Nếu mỗi trạng thái dùng test set khác nhau, ta không phân biệt được sự thay đổi metric đến từ data quality hay từ sự khó dễ của câu hỏi. Test set cố định là controlled variable.

5. **Repair thành công khi:** `repair_verification.json` xác nhận SHA-256 repaired dataset == SHA-256 baseline dataset, VÀ `repaired_metrics.json` có `retrieval_hit_rate` ≥ baseline `retrieval_hit_rate`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét |
| ---------------------- | -------: | --------: | -------: | --------- |
| `retrieval_hit_rate` | 1.0000 | 0.4000 | 1.0000 | Drop abstract trực tiếp gây miss retrieval |
| `mean_token_f1`      | 1.0000 | 0.3644 | 1.0000 | Noise trong text làm F1 giảm mạnh |
| `judge_accuracy`     | 1.0000 | 0.4000 | 1.0000 | Phục hồi hoàn toàn sau clean từ raw |
| `mean_judge_score`   | 1.0000 | 0.3644 | 1.0000 | Phục hồi hoàn toàn |
| Quality checks         | PASS | FAIL | PASS | GX phát hiện null summary và duplicate ID |
| Freshness status       | FRESH | STALE | FRESH | Stale date injection đẩy ratio lên 33.33% |

### Kết luận từ số liệu

1. **Drop abstract** → `summary` null → Non-null check FAIL → `mean_token_f1` giảm từ 1.0 xuống 0.364 vì `text_for_embedding` mất phần Summary — embedding kém, retrieval trả sai document.
2. **Repair từ `crossref_records.json`** → Cleaning pipeline chạy lại → `papers_clean.csv` sạch → Quality Gate PASS, Freshness FRESH → `retrieval_hit_rate` và `mean_token_f1` phục hồi về 1.0.

Corruption ảnh hưởng rõ nhất: drop abstract — vì Summary chiếm phần lớn ngữ nghĩa trong `text_for_embedding`. Kết quả này đúng với kỳ vọng và khớp với lý thuyết "garbage in → garbage out".

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Raw artifact là "nguồn sự thật" (source of truth) — không bao giờ sửa, mọi derived artifact đều có thể tái tạo từ raw. Đây là nền tảng của idempotent repair.
2. **Data quality:** Thiếu abstract không gây lỗi ngay — system vẫn chạy "thành công" nhưng retrieval quality sụp đổ. GX Quality Gate là lớp phòng thủ chủ động bắt lỗi trước khi vào production.
3. **RAG:** `text_for_embedding` cần đủ 5 phần metadata + content để embedding vector chứa đủ tín hiệu ngữ nghĩa. Thiếu bất kỳ phần nào đều ảnh hưởng retrieval đáng kể.

### Nếu có thêm thời gian

Bổ sung validation schema cho `crossref_records.json` ngay sau bước parse (trước cleaning) bằng Pydantic model. Nếu parse ra record thiếu trường bắt buộc, log warning ngay thay vì propagate lỗi xuống cleaning. Đo cải thiện bằng cách đếm số lỗi được phát hiện sớm so với phiên bản hiện tại.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đỗ Thanh Lâm
**Ngày xác nhận:** 2026-09-25
