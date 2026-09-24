# Hướng Dẫn Kỹ Thuật Chi Tiết (Technical Guide)

Tài liệu hướng dẫn từng bước hoàn thiện bài lab **Day 10 - Data Pipeline & Data Observability**.

---

## Bước 1: Khởi tạo Môi trường & Cấu hình

1. Mở terminal tại thư mục gốc của project.
2. Kiểm tra phiên bản Python:
   ```bash
   python --version
   ```
   *Yêu cầu:* Python 3.11, 3.12 hoặc 3.13.
3. Kích hoạt môi trường ảo:
   - Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
   - Linux/macOS: `source .venv/bin/activate`
4. Tạo file `.env` từ `.env.example` và điền API Key cần sử dụng.
5. Kiểm tra kết nối thư viện:
   ```bash
   python -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"
   ```
   > Tín hiệu hoàn thành: Console in `Môi trường sẵn sàng`.

---

## Bước 2: Ingestion & Raw Preservation (`src/ingestion/crossref.py`)

### Mục tiêu:
- Thu thập metadata từ Crossref REST API.
- Chuẩn hóa các trường: `paper_id` (DOI), `title`, `summary` (làm sạch thẻ JATS XML `<jats:p>`), `authors`, `categories`, `published` date.
- Lưu lại 2 artifacts raw để bảo đảm tính truy vết nguồn gốc (lineage):
  - `data/raw/crossref_response.json`: Toàn bộ raw JSON phản hồi từ API.
  - `data/raw/crossref_records.json`: Danh sách đối tượng `PaperRecord` đã parse.

### Chế độ Offline / Dev:
Nếu môi trường không có kết nối Internet hoặc API Crossref gặp lỗi `429 Too Many Requests`, pipeline tự động đọc từ file snapshot mẫu có sẵn tại `data/raw/crossref_response.json`.

Kiểm tra bước 2:
```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
```
> Tín hiệu hoàn thành: Console in ra `Tín hiệu hoàn thành: Đã tải 24 bài báo`.

---

## Bước 3: Data Cleaning & Pre-embed Modeling (`src/ingestion/cleaning.py`)

### Mục tiêu:
- Loại bỏ khoảng trắng thừa, chuẩn hóa định dạng văn bản.
- Tính toán tuổi của dữ liệu: `age_days = (run_date - published).days`.
- Tạo trường tổng hợp ngữ cảnh phục vụ sinh vector `text_for_embedding`:
  ```text
  Title: <Tiêu đề>
  Authors: <Tác giả>
  Published: <Ngày xuất bản>
  Categories: <Lĩnh vực>
  Summary: <Tóm tắt>
  ```
- Khử trùng lặp bản ghi theo `paper_id`.

Kiểm tra bước 3:
```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
```
> Tín hiệu hoàn thành: Console in ra `Tín hiệu hoàn thành: Clean thành công 24 dòng`.

---

## Bước 4: Data Observability với Great Expectations 1.x (`src/observability/quality.py`)

### Yêu cầu Chuẩn GX 1.x (Theo Slide Khóa 4 Trang 51-52):
Không sử dụng cú pháp cũ `context.sources.pandas_default` (bị lỗi `AttributeError` trên GX 1.x). Sử dụng chuẩn mới:
```python
context = gx.get_context(mode="ephemeral")
data_source = context.data_sources.add_pandas(name="papers_source")
data_asset = data_source.add_dataframe_asset(name="papers_asset")
batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
batch = batch_def.get_batch(batch_parameters={"dataframe": df})
```

### Các Expectation Bắt Buộc:
1. `ExpectTableRowCountToBeBetween`: Số lượng bản ghi nằm trong ngưỡng hợp lệ (5 đến 5000 dòng).
2. `ExpectColumnValuesToNotBeNull`: Trường `paper_id`, `title`, `text_for_embedding` không được phép null.
3. `ExpectColumnValuesToBeUnique`: `paper_id` là khóa duy nhất, không được trùng lặp.
4. `ExpectColumnValueLengthsToBeBetween`: Trường `summary` phải có độ dài tối thiểu 30 ký tự để đảm bảo chất lượng semantic search.

### Freshness SLA/SLO:
Đo lường tỉ lệ bài báo bị quá hạn (`age_days > 180 ngày`). Nếu tỉ lệ bài báo cũ vượt quá 25%, gắn cờ `is_fresh = False`.

Kiểm tra bước 4:
```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Tín hiệu hoàn thành: Quality check status = {res["success"]}')"
```
> Tín hiệu hoàn thành: Console in ra `Tín hiệu hoàn thành: Quality check status = True`.

---

## Bước 5: Tạo Benchmark Test Set (`src/evaluation/testset.py`)

Tạo 10 câu hỏi đa dạng phân bổ đều qua 4 dạng bài toán:
1. `summary`: Hỏi tóm tắt nội dung chính của bài báo cụ thể.
2. `authors`: Hỏi danh sách tác giả của công trình nghiên cứu.
3. `date`: Hỏi thời điểm xuất bản.
4. `categories`: Hỏi về chuyên ngành / lĩnh vực phân loại.

Mỗi mẫu có cấu trúc:
```json
{
  "id": "eval_001",
  "question_type": "summary",
  "question": "What is the summary of the paper '<Title>'?",
  "ground_truth": "<Nội dung câu đầu tóm tắt>",
  "ground_truth_doc_ids": ["<DOI>"]
}
```

Kiểm tra bước 5:
```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
```
> Tín hiệu hoàn thành: Console in ra `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`.

---

## Bước 6: Chạy Baseline Pipeline (`script/run_phase1.py`)

Thực thi toàn bộ chu trình dữ liệu sạch:
```bash
python script/run_phase1.py
```

> Tín hiệu hoàn thành:
> - File `data/clean/papers_clean.csv` xuất hiện.
> - File `data/results/baseline_metrics.json` ghi nhận Hit Rate và Token F1.
> - File `data/reports/phase1_report.md` được sinh ra với đầy đủ thông số.

---

## Bước 7: Mô phỏng Dữ liệu Lỗi (Data Corruption Suite)

Triển khai trong `src/ingestion/corruption.py` với 6 dạng lỗi thực tế:
1. **Drop latest records:** Xóa bỏ 20% bản ghi mới nhất.
2. **Blank summary:** Xóa rỗng tóm tắt ở một số dòng.
3. **Inject noise:** Chèn chuỗi ký tự vô nghĩa vào tóm tắt.
4. **Truncate title:** Cắt ngắn tiêu đề bài báo xuống dưới 8 ký tự.
5. **Stale date:** Lùi ngày xuất bản về 365 ngày trước.
6. **Duplicate rows:** Nhân đôi các dòng để tạo trùng lặp.

Kiểm tra bước 7:
```bash
python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupted {len(c)} dòng')"
```
> Tín hiệu hoàn thành: File `data/results/corruption_log.json` được ghi lại chi tiết.

---

## Bước 8: Chạy Corruption Flow, Repair & So sánh Đối chiếu

Thực thi toàn bộ luồng Phase 2:
```bash
python script/run_corruption_flow.py
```

> Tín hiệu hoàn thành:
> - Console in ra bảng so sánh hiệu năng 3 trạng thái.
> - File `data/reports/corruption_report.md` được tạo thành công, minh chứng rõ rệt sự suy giảm của Agent trên dữ liệu bẩn và sự phục hồi 100% sau khi sửa chữa.
