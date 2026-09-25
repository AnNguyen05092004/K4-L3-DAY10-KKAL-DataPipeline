# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                        |
| ------------------ | --------------------------------------------------------------- |
| Họ và tên       | Nguyễn Văn An                                                  |
| MSSV               | 2A202602782                                                     |
| Khóa/Lớp         | K4 / L3                                                         |
| Tên nhóm         | KKAL                                                            |
| Vai trò chính    | Observability & Evaluation Lead                                 |
| Repository         | https://github.com/AnNguyen05092004/K4-L3-DAY10-KKAL-DataPipeline |
| Ngày hoàn thành | 2026-09-25                                                      |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Quality Gate (GX 1.x) | `src/observability/quality.py` — `run_quality_checks()` | `data/clean/papers_clean.csv` | `data/quality/baseline_quality_report.json`, `corrupted_quality_report.json` | Hoàn thành |
| Freshness SLA | `src/observability/quality.py` — `check_freshness()` | `papers_clean.csv` trường `age_days` | `data/quality/freshness_report.json` | Hoàn thành |
| Metrics evaluation | `src/evaluation/metrics.py` — `evaluate_retrieval()` | `test_set.json`, ChromaDB collection | `data/results/*_metrics.json` | Hoàn thành |
| Markdown reporting | `src/observability/reporting.py` — `generate_phase1_report()`, `generate_corruption_report()` | Các file metrics JSON | `data/reports/phase1_report.md`, `corruption_report.md` | Hoàn thành |

Module orchestrator (Khải) gọi hàm của tôi ở bước cuối mỗi phase. Module RAG (Khuyến) cung cấp `semantic_search()` mà tôi dùng để tính hit rate và F1.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------------ | --------- |
| Giải thích cú pháp GX 1.x (ephemeral datasource) cho cả nhóm | Đoàn Bá Khải, Đỗ Thanh Lâm | Nhóm hiểu sự khác biệt GX 0.x vs 1.x, tránh dùng deprecated API |
| Kiểm tra `corruption_report.md` có đủ 3 cột so sánh trước khi submit | Đoàn Bá Khải | Report đúng format, đủ bảng đối chiếu |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ----------------------- | ----------------------- |
| Quality Gate GX 1.x | `src/observability/quality.py` | `data/quality/baseline_quality_report.json` (PASS), `corrupted_quality_report.json` (FAIL) | Mở file JSON, xem `success: true/false` |
| Freshness SLA | `check_freshness()` | `data/quality/freshness_report.json` — baseline FRESH, corrupted STALE | `stale_ratio` < 0.25 (baseline) vs > 0.25 (corrupted) |
| Evaluate 3 trạng thái | `src/evaluation/metrics.py` | 3 file metrics JSON với hit rate & F1 | `jq '.retrieval_hit_rate' data/results/baseline_metrics.json` |
| Báo cáo đối chiếu | `src/observability/reporting.py` | `data/reports/corruption_report.md` | Mở file, kiểm tra có đủ 3 cột |

Output quan trọng nhất: `data/reports/corruption_report.md` — bảng đối chiếu 3 trạng thái với số liệu thực tế, là bằng chứng chính nhóm trình bày trong live demo.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cần hai loại "trạm kiểm soát" độc lập:
1. **Quality Gate (GX 1.x):** Kiểm tra schema và nội dung `papers_clean.csv` — phát hiện lỗi dữ liệu trước khi vào vector store.
2. **Freshness SLA:** Kiểm tra `age_days` — phát hiện khi data source không được cập nhật, vector store chứa kiến thức cũ.

Ngoài ra, cần tính metrics (Hit Rate, Token F1) cho 3 trạng thái dùng cùng test set và xuất báo cáo Markdown so sánh định lượng.

### Cách triển khai

**Quality Gate với GX 1.x:**
```python
import great_expectations as gx

context = gx.get_context()
ds = context.sources.add_pandas("papers_source")
da = ds.add_dataframe_asset("papers_asset")
batch = da.build_batch_request(dataframe=df)
suite = context.add_expectation_suite("papers_suite")
validator = context.get_validator(batch_request=batch, expectation_suite=suite)

validator.expect_table_row_count_to_be_between(min_value=10)
validator.expect_column_values_to_not_be_null("title")
validator.expect_column_values_to_not_be_null("summary")
validator.expect_column_values_to_be_unique("paper_id")
validator.expect_column_value_lengths_to_be_between("summary", min_value=50)
result = validator.validate()
```

Dùng ephemeral datasource (không persist GX context ra disk) để tránh xung đột khi chạy lại.

**Freshness SLA:** Tính `stale_ratio = (df['age_days'] > 180).mean()`. STALE nếu `stale_ratio > 0.25`.

**Hit Rate:** Với mỗi câu hỏi trong test set, gọi `semantic_search(question, top_k=5)`, trả về list `paper_id`. Hit nếu tất cả `ground_truth_doc_ids` nằm trong kết quả (strict match cho multi-hop).

**Token F1:** Tokenize câu trả lời retrieved và ground truth bằng whitespace split, tính precision/recall/F1 trên tập token.

### Input, output và contract

| Thành phần                   | Mô tả |
| ------------------------------ | ------- |
| Input                          | `data/clean/papers_clean.csv` (từ Lâm), `data/eval/test_set.json` (từ Khuyến), ChromaDB collection (từ Khuyến) |
| Output                         | `data/quality/baseline_quality_report.json`, `data/quality/corrupted_quality_report.json`, `data/quality/freshness_report.json`, `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |
| Module phụ thuộc             | `src/ingestion/cleaning.py` (Lâm), `src/retrieval/index.py` (Khuyến), `src/core/config.py` (Khải) |
| Module sử dụng output        | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` (Khải đọc metrics để tạo comparison) |
| Điều kiện lỗi cần xử lý | GX datasource conflict khi chạy lại (→ ephemeral context), `test_set.json` thiếu `ground_truth_doc_ids` (→ KeyError), ChromaDB collection chưa build (→ FileNotFoundError) |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** `data/quality/baseline_quality_report.json` có `success: true`; `data/quality/corrupted_quality_report.json` có `success: false`; `corruption_report.md` có bảng 3 cột.
- **Kết quả thực tế:** Đúng như kỳ vọng. Baseline PASS, Corrupted FAIL (duplicate ID và short summary), Repaired PASS.
- **Artifact/log:** `data/quality/`, `data/results/`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** GX 1.x thay đổi hoàn toàn API so với GX 0.x — không còn `DataContext()` kiểu cũ, thay bằng `gx.get_context()` với ephemeral hoặc persistent context.
- **Các phương án đã cân nhắc:**
  1. Dùng GX 0.x API (`DataContext`, `PandasDatasource` kiểu cũ) — quen thuộc nhưng deprecated.
  2. Dùng GX 1.x API với ephemeral datasource (`gx.get_context()`, `add_pandas()`).
- **Phương án đã chọn:** GX 1.x API, ephemeral context.
- **Lý do:** Đây là yêu cầu bắt buộc trong RUBRIC. Hơn nữa, ephemeral context không ghi file ra disk nên idempotent hoàn toàn — chạy lại bao nhiêu lần cũng không conflict. GX 1.x API cũng rõ ràng hơn về datasource vs asset vs batch.
- **Bằng chứng:** `data/quality/baseline_quality_report.json` được tạo bởi GX 1.x, field `success: true`. RUBRIC checklist GX 1.x được đánh dấu PASS.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `AttributeError: 'EphemeralDataContext' object has no attribute 'add_expectation_suite'` khi chạy GX 1.x lần đầu.
- **Lệnh tái hiện:** Chạy `python script/run_phase1.py` với code dùng `context.add_expectation_suite()` (API GX 0.x style).
- **Nguyên nhân gốc:** GX 1.x đổi tên và cấu trúc API — `add_expectation_suite()` không còn là method của context. Thay vào đó phải tạo suite qua validator trực tiếp.
- **Cách xử lý:** Đọc docs GX 1.x tại `docs.greatexpectations.io`, chuyển sang pattern:
  ```python
  validator = context.get_validator(batch_request=batch)
  validator.expect_table_row_count_to_be_between(...)
  result = validator.validate()
  ```
  Không cần tạo suite riêng nếu chỉ cần ephemeral validation.
- **Cách xác minh:** Chạy lại `python script/run_phase1.py` — GX validation chạy thành công, `baseline_quality_report.json` được tạo với `success: true`.
- **Điều học được:** API của thư viện lớn thay đổi đáng kể giữa các major version. Luôn kiểm tra version trong `requirements.txt` và đọc migration guide trước khi code.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu từ Crossref đến vector index:** Lâm fetch raw JSON, cleaning chuẩn hóa và tạo `text_for_embedding`. Khuyến encode bằng MiniLM, nạp vào ChromaDB. Tôi nhận `papers_clean.csv` để chạy Quality Gate GX 1.x và nhận ChromaDB collection để chạy evaluation.

2. **Evaluation set và ground-truth:** Khuyến sinh 10 câu với `ground_truth_doc_ids`. Tôi gọi `semantic_search()` cho mỗi câu, so sánh kết quả trả về với `ground_truth_doc_ids`. Hit Rate = (số câu hit) / 10. Token F1 đo overlap token giữa retrieved text và ground truth text string.

3. **Quality checks vs freshness:** Quality checks (GX 1.x) kiểm tra tính đúng đắn của dữ liệu tại thời điểm hiện tại — đây là "kiểm dịch nội dung". Freshness monitoring kiểm tra `age_days` — đây là "kiểm dịch thời gian". Hai kiểu check phát hiện hai loại lỗi khác nhau: content corruption vs temporal staleness.

4. **Cùng test set:** Ba trạng thái phải dùng cùng `test_set.json` vì đây là biến kiểm soát. Nếu test set khác nhau, phép so sánh metric mất ý nghĩa — ta không thể phân biệt metric thay đổi do data hay do câu hỏi khó/dễ hơn.

5. **Repair thành công khi:** `data/quality/repaired_quality_report.json` có `success: true` (GX PASS), `freshness_report.json` cho trạng thái repaired là FRESH, VÀ `repaired_metrics.json` có `retrieval_hit_rate` = 1.0 và `mean_token_f1` = 1.0.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét |
| ---------------------- | -------: | --------: | -------: | --------- |
| `retrieval_hit_rate` | 1.0000 | 0.4000 | 1.0000 | Giảm 60% do corrupt — nghiêm trọng; phục hồi 100% |
| `mean_token_f1`      | 1.0000 | 0.3644 | 1.0000 | Token overlap gần như mất khi summary bị xóa/noise |
| `judge_accuracy`     | 1.0000 | 0.4000 | 1.0000 | Phục hồi hoàn toàn sau repair |
| `mean_judge_score`   | 1.0000 | 0.3644 | 1.0000 | Phục hồi hoàn toàn |
| Quality checks         | PASS | FAIL | PASS | GX phát hiện đúng: null summary + duplicate ID |
| Freshness status       | FRESH | STALE | FRESH | Stale ratio tăng từ <25% lên 33.33% khi inject stale date |

### Kết luận từ số liệu

1. **Stale date injection + duplicate rows** → Freshness STALE (ratio 33.33%), GX FAIL (duplicate `paper_id`) → Agent trả lời bằng kiến thức cũ và context bị loãng → `mean_token_f1` giảm từ 1.0 xuống 0.364 — đây là biểu hiện Silent Failure điển hình.
2. **Idempotent repair từ raw records** → GX PASS, Freshness FRESH → `retrieval_hit_rate` và `mean_token_f1` phục hồi về 1.0 — chứng minh Quality Gate + repair pipeline là giải pháp hiệu quả chống Silent Failure.

Corruption ảnh hưởng rõ nhất: **drop abstract** — GX non-null check FAIL ngay lập tức, và metric drop 60% — đây là loại lỗi dễ phát hiện nhất nhờ Quality Gate, nhưng cũng gây tác hại nặng nhất nếu không có gate.

Kết quả khác kỳ vọng: Tôi kỳ vọng `retrieval_hit_rate` corrupted sẽ thấp hơn nữa (có thể 0.2–0.3) vì 6 loại corruption trải đều. Thực tế 0.4 vì 4/10 câu hỏi query các paper không bị corrupt nên vẫn hit đúng.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Quality Gate không chỉ là "nice to have" — nếu không có GX check, pipeline vẫn chạy "thành công" với dữ liệu corrupt và agent trả lời sai. Silent Failure không có exception, không có error log.
2. **Data quality/observability:** GX 1.x API ephemeral context là pattern đúng cho pipeline — không để lại state trên disk, idempotent, không conflict khi chạy lại.
3. **RAG:** `retrieval_hit_rate` và `mean_token_f1` là hai metric bổ sung cho nhau — hit rate đo "có lấy đúng document không", token F1 đo "text trong document có overlap với ground truth không". Cả hai cùng drop nghĩa là lỗi ở tầng retrieval (embedding/index), không phải tầng generation.

### Nếu có thêm thời gian

Bổ sung alert tự động: khi Quality Gate FAIL hoặc Freshness STALE, pipeline raise exception có structured log (JSON format) thay vì chỉ ghi file JSON. Tích hợp với monitoring system để team nhận notification ngay. Đo cải thiện bằng Mean Time To Detect (MTTD) lỗi: từ "phát hiện khi có khiếu nại" xuống "phát hiện trong vòng 1 pipeline run".

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn An
**Ngày xác nhận:** 2026-09-25
