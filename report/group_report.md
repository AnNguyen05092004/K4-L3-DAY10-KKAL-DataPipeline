# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                                                                       |
| ------------------ | ------------------------------------------------------------------------------- |
| Khóa/Lớp         | K4 / L3                                                                         |
| Tên nhóm         | KKAL                                                                            |
| Repository         | https://github.com/AnNguyen05092004/K4-L3-DAY10-KKAL-DataPipeline             |
| Ngày hoàn thành | 2026-09-25                                                                      |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đoàn Bá Khải | 2A202602728 | Trưởng nhóm / Pipeline Integrator | `src/core/`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| 2 | Đỗ Thanh Lâm | 2A202602577 | Data Foundation & Recovery | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `data/raw/` |
| 3 | Trần Ngọc Khuyến | 2A202602682 | RAG & Vector Index | `src/retrieval/`, ChromaDB collections, `data/embeddings/` |
| 4 | Nguyễn Văn An | 2A202602782 | Observability & Evaluation Lead | `src/observability/quality.py`, `src/evaluation/testset.py`, `data/reports/` |

## 2. Tóm tắt kết quả

Nhóm KKAL đã hoàn thành toàn bộ 7 checkpoints (CP0–CP6) trong buổi lab. Baseline pipeline chạy thành công với exit code 0, sinh ra đầy đủ artifact: `data/clean/papers_clean.csv`, `data/eval/test_set.json`, `data/results/baseline_metrics.json` và `data/reports/phase1_report.md`. Corruption flow cũng chạy thành công, tạo ra `corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json` và `corruption_report.md`.

Baseline đạt retrieval hit rate = 1.0, mean token F1 = 1.0, Quality Gate PASS và Freshness FRESH. Sau khi tiêm 6 dạng lỗi, hệ thống suy giảm rõ rệt xuống hit rate = 0.4 và token F1 = 0.364, Quality Gate FAIL, Freshness STALE — chứng minh hiện tượng Silent Failure trong RAG. Sau khi repair từ raw data, toàn bộ chỉ số phục hồi về mức baseline (hit rate = 1.0, token F1 = 1.0, Quality Gate PASS, Freshness FRESH).

Corruption loại "xóa tóm tắt" (drop abstract) và "tiêm ký tự rác" (inject noise) ảnh hưởng mạnh nhất đến retrieval quality vì embedding mất ngữ nghĩa cốt lõi. Blocker còn lại: external LLM Judge và Ragas là tùy chọn, nhóm dùng deterministic token-overlap judge và ghi rõ phương pháp trong artifact.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (hoặc Offline Snapshot data/raw/crossref_response.json)
    -> raw response (data/raw/crossref_response.json)
    -> raw records (data/raw/crossref_records.json)
    -> cleaning & data modeling (src/ingestion/cleaning.py)
    -> data/clean/papers_clean.csv & papers_clean.json
    -> embedding MiniLM + ChromaDB index (src/retrieval/)
    -> data/embeddings/ & data/chroma/papers-baseline
    -> evaluation baseline (src/evaluation/)
    -> data/eval/test_set.json & data/results/baseline_metrics.json
    -> quality & freshness reports (src/observability/)
    -> data/quality/ & data/reports/phase1_report.md
    -> corruption x6 types (src/ingestion/corruption.py)
    -> data/results/corruption_log.json & data/chroma/papers-corrupted
    -> re-index & re-evaluate -> data/results/corrupted_metrics.json
    -> repair từ raw records -> data/chroma/papers-repaired
    -> data/results/repaired_metrics.json
    -> comparison report -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API / snapshot JSON | Fetch, retry, parse PaperRecord | `data/raw/crossref_records.json` | Đỗ Thanh Lâm |
| Cleaning          | `crossref_records.json` | Chuẩn hóa JATS/HTML, tính `age_days`, tạo `text_for_embedding`, deduplicate | `data/clean/papers_clean.csv` | Đỗ Thanh Lâm |
| Embedding/index   | `papers_clean.json` | MiniLM embedding, nạp ChromaDB 3 collections | `data/chroma/`, `data/embeddings/` | Trần Ngọc Khuyến |
| Evaluation        | `papers_clean.json`, ChromaDB | Sinh 10 câu benchmark, tính Hit Rate, Token F1, judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Nguyễn Văn An |
| Observability     | `papers_clean.csv` | Quality Gate GX 1.x (row count, non-null, unique ID, summary length), Freshness SLA 180 ngày | `data/quality/` | Nguyễn Văn An |
| Corruption/repair | `papers_clean.csv`, `crossref_records.json` | Tiêm 6 lỗi, re-index, repair idempotent từ raw | `corruption_log.json`, `corrupted/repaired_metrics.json` | Đoàn Bá Khải |
| Orchestration     | Tất cả modules | Điều phối thứ tự chạy 2 flow | `phase1_report.md`, `corruption_report.md` | Đoàn Bá Khải |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | gemini              |
| `LLM_MODEL`                | gemini-2.5-flash    |
| Embedding model              | sentence-transformers/all-MiniLM-L6-v2 |
| Số lượng Crossref records | 24 unique papers    |
| Retrieval `top_k`          | 5                   |
| Freshness threshold          | 180 ngày / stale ratio 25% |
| Random seed, nếu có        | N/A                 |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ----------- | ------------------------- | ----------- |
| Baseline pipeline | Thành công  | 2026-09-25                | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công  | 2026-09-25                | `data/results/corruption_log.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị |
| --------------------------- | ------- |
| Source                      | Crossref REST API — query `machine learning` / offline snapshot `data/raw/crossref_response.json` |
| Query/filter                | `machine learning`, filter `has-abstract:true`, `type:journal-article` |
| Thời điểm lấy dữ liệu | 2026-09-25 (snapshot offline) |
| Số record nhận được    | 24 unique papers sau deduplicate |
| Cơ chế retry/backoff      | Thử lại tối đa 3 lần với exponential backoff; fallback sang snapshot offline khi API trả 429 |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | str | Có | DOI duy nhất | Loại bỏ record không có DOI |
| `title` | str | Có | Tiêu đề bài báo | Loại bỏ record không có title |
| `summary` | str | Có | Tóm tắt/abstract | Loại bỏ record không có abstract |
| `authors_joined` | str | Không | Danh sách tác giả | Điền `"Unknown"` nếu thiếu |
| `published` | str | Không | Ngày xuất bản (YYYY-MM-DD) | Điền `"1970-01-01"` nếu thiếu |
| `categories_joined` | str | Không | Subject labels | Điền `"Uncategorized"` (Crossref snapshot không có subject labels) |
| `age_days` | int | Có | Số ngày từ ngày xuất bản | Tính từ `published` đến ngày hiện tại |
| `text_for_embedding` | str | Có | Chuỗi 5 phần: Title / Authors / Published / Categories / Summary | Ghép các trường đã chuẩn hóa |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| -------- | ---------------------------- | ----------------------: | -------------- |
| Loại record không có `title` | Completeness | ~0 trong snapshot | `papers_clean.csv` row count |
| Loại record không có `abstract` | Completeness | ~0 trong snapshot | `papers_clean.csv` row count |
| Deduplicate theo `paper_id` (DOI) | Uniqueness | Phụ thuộc API response | `paper_id` unique check trong GX |
| Strip JATS/HTML tags và Unicode entities | Validity | Tất cả records | Kiểm tra bằng mắt `papers_clean.csv` |
| Chuẩn hóa whitespace | Validity | Tất cả records | `summary_length` check trong GX |

`text_for_embedding` được tạo bằng cách ghép 5 phần: `"Title: {title} | Authors: {authors_joined} | Published: {published} | Categories: {categories_joined} | Summary: {summary}"`. Document ID chính là `paper_id` (DOI). `age_days` = (ngày chạy pipeline) − `published`, tính bằng số ngày nguyên.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế |
| ---------------------------------------- | ------------------- |
| Số câu hỏi                            | 10                  |
| Các `question_type`                    | summary, authors, date, category, multi-hop |
| Ground-truth document ID                 | `paper_id` (DOI) từ cleaned dataset |
| Embedding model                          | sentence-transformers/all-MiniLM-L6-v2 |
| Vector store/collection                  | ChromaDB `papers-baseline` / `papers-corrupted` / `papers-repaired` |
| Retrieval `top_k`                      | 5 |
| LLM provider/model                       | Deterministic token-overlap judge (external LLM là tùy chọn) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

Test set được giữ nguyên không thay đổi qua cả ba trạng thái để phép so sánh có ý nghĩa thống kê. Nếu mỗi trạng thái dùng test set khác nhau, ta không thể phân biệt sự thay đổi metric là do data quality hay do câu hỏi khác nhau.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế | Trạng thái | Ghi chú |
| ------------------------ | ------------------ | ------------ | ------- |
| Raw response/records     | `data/raw/` | Có | `crossref_response.json` & `crossref_records.json` |
| Cleaned dataset          | `data/clean/` | Có | `papers_clean.csv` & `papers_clean.json` |
| Embedding manifest/index | `data/embeddings/` | Có | `papers_embeddings.json` |
| Evaluation set           | `data/eval/` | Có | `test_set.json` — 10 câu hỏi 5 loại |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Hit rate & F1 = 1.0 |
| Quality/freshness        | `data/quality/` | Có | `baseline_quality_report.json`, `freshness_report.json` |
| Baseline report          | `data/reports/phase1_report.md` | Có | Đầy đủ phân tích |

### Baseline metrics

| Metric                 | Giá trị | Diễn giải |
| ---------------------- | -------: | ---------- |
| `retrieval_hit_rate` | 1.0000 | Tất cả 10 câu hỏi đều truy xuất đúng document chứa ground truth |
| `mean_token_f1`      | 1.0000 | Token overlap hoàn hảo giữa retrieved text và ground truth |
| `judge_accuracy`     | 1.0000 | Deterministic judge chấp nhận toàn bộ câu trả lời |
| `mean_judge_score`   | 1.0000 | Điểm trung bình judge = 1.0 |
| Ragas, nếu có        | N/A | Không chạy — external LLM Judge là tùy chọn; phương pháp ghi rõ trong metrics artifact |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------- | ------------ |
| Row count    | Completeness | ≥ 10 records | PASS (24 records) | `baseline_quality_report.json` |
| Non-null title & summary | Completeness | 0 null | PASS | `baseline_quality_report.json` |
| Unique `paper_id` | Uniqueness | 0 duplicate | PASS | `baseline_quality_report.json` |
| Summary length ≥ 50 chars | Validity | Tất cả summary ≥ 50 ký tự | PASS | `baseline_quality_report.json` |

### Freshness

| Thuộc tính               | Giá trị |
| -------------------------- | ------- |
| Freshness được đo tại | `papers_clean.csv` — trường `age_days` |
| Timestamp mới nhất       | Bài báo mới nhất trong snapshot |
| Ngưỡng freshness         | 180 ngày / stale ratio ≤ 25% |
| Trạng thái baseline      | FRESH |
| Lý do                     | Stale ratio < 25% trong baseline dataset |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ---------- | --------- | -------------------: | ----------------------- | ----------------- | ----------- |
| Drop new records | Không nạp 5 record mới nhất | 5 | Miss freshness check | Hit rate giảm do thiếu document | Re-ingest từ raw |
| Drop abstract | Xóa trường `summary` | 5 | Non-null check FAIL | Embedding mất ngữ nghĩa, F1 giảm mạnh | Re-clean từ raw records |
| Inject noise | Chèn ký tự rác vào `title` và `summary` | 5 | Summary length check FAIL | Retrieval trả nhầm document | Re-clean từ raw records |
| Truncate title | Cắt `title` xuống ≤ 10 ký tự | 5 | Summary length check FAIL | Embedding kém chính xác | Re-clean từ raw records |
| Stale date | Đặt `published` = 2020-01-01 cho các record | 8 | Freshness STALE | Stale ratio vượt 25% | Re-clean từ raw records |
| Duplicate rows | Nhân đôi 4 record | 4 | Unique ID check FAIL | Ngữ cảnh bị loãng, judge score giảm | Re-clean & deduplicate từ raw records |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đầy đủ 6 loại corruption, số record bị tác động và tham số cụ thể.

Repair được thực hiện bằng cách chạy lại toàn bộ cleaning pipeline từ `data/raw/crossref_records.json` (raw artifact không bao giờ bị sửa đổi), tái tạo `papers_clean.csv` và nạp lại vào collection `papers-repaired` trong ChromaDB. Phương pháp này đảm bảo idempotency: chạy bao nhiêu lần cũng cho ra cùng kết quả, và SHA-256 của repaired dataset khớp với baseline dataset.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| ------------------------ | -------: | --------: | -------: | ----------------------: | -------------: | --------- |
| `retrieval_hit_rate`   | 1.0000 | 0.4000 | 1.0000 | −0.6000 | 100% | Phục hồi hoàn toàn |
| `mean_token_f1`        | 1.0000 | 0.3644 | 1.0000 | −0.6356 | 100% | Phục hồi hoàn toàn |
| `judge_accuracy`       | 1.0000 | 0.4000 | 1.0000 | −0.6000 | 100% | Phục hồi hoàn toàn |
| `mean_judge_score`     | 1.0000 | 0.3644 | 1.0000 | −0.6356 | 100% | Phục hồi hoàn toàn |
| Quality checks pass/fail | PASS | FAIL | PASS | Gate kích hoạt đúng | PASS | GX 1.x phát hiện chính xác |
| Freshness status         | FRESH | STALE | FRESH | Stale ratio 33.33% | FRESH | Freshness check hoạt động |

Kết luận nhân quả:

1. **Drop abstract + inject noise** → summary non-null check FAIL, summary length check FAIL → `mean_token_f1` giảm từ 1.0 xuống 0.364, tức embedding mất ngữ nghĩa cốt lõi khiến retrieval trả sai document.
2. **Idempotent repair từ raw records** → Quality Gate PASS, Freshness FRESH → `retrieval_hit_rate` và `mean_token_f1` phục hồi về 1.0, xác nhận rằng raw data preservation là chiến lược đúng đắn để phục hồi pipeline.

## 11. Vấn đề tích hợp quan trọng

Vấn đề phát sinh khi ghép module cleaning và module embedding:

- **Triệu chứng:** `LocalEmbeddingIndex.build_from_clean()` báo `KeyError: 'text_for_embedding'` khi đọc `papers_clean.json`.
- **Nguyên nhân:** Module cleaning xuất `papers_clean.csv` với đúng schema, nhưng khi chuyển sang JSON, tên cột `text_for_embedding` bị thiếu do lỗi logic trong hàm `to_json()`.
- **Cách xử lý:** Sửa hàm xuất JSON để đảm bảo tất cả cột từ DataFrame đều được serialize, thêm assertion kiểm tra schema sau khi ghi file.
- **Cách xác minh:** Chạy lại `python script/run_phase1.py` — exit code 0, ChromaDB collection `papers-baseline` có 24 documents.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | ----------- | ----------------------------------------- |
| Judge mặc định là token-overlap, không phải LLM judge thực sự | `judge_accuracy` không phản ánh chất lượng ngữ nghĩa câu trả lời | Tích hợp Gemini/GPT-4o làm judge; so sánh judge score giữa hai phương pháp |
| Snapshot Crossref không có subject labels | `categories_joined` = "Uncategorized" cho mọi record | Fetch trực tiếp từ API với filter `has-abstract:true` để lấy subject labels |
| Test set chỉ có 10 câu hỏi | Variance cao, kết quả không đủ robust về mặt thống kê | Tăng lên 50–100 câu; dùng nhiều query type hơn |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
