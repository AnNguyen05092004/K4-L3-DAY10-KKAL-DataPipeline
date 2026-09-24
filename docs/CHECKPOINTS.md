# CHECKPOINTS: DAY 10 - DATA PIPELINE & DATA OBSERVABILITY

> **Tổng thời lượng thực chiến:** 240 phút (4 giờ)  
> **Hình thức:** Làm việc theo nhóm (Teamwork)  
> **Bộ dữ liệu chuẩn:** Crossref Metadata API (hoặc Local Snapshot `data/raw/crossref_response.json`)  
> **Mục tiêu cốt lõi:** Xây dựng Data Pipeline hoàn chỉnh cho hệ thống RAG Agent, tích hợp Data Observability (Great Expectations 1.x + Freshness SLA), đo lường mức độ suy giảm khi dữ liệu bị lỗi (Data Corruption) và chứng minh năng lực tự phục hồi (Self-healing / Repair).

---

## Bảng Phân Bổ Thời Gian & Mục Tiêu Từng Checkpoint

| Checkpoint | Nội dung trọng tâm | Thời lượng gợi ý | Deliverables (Sản phẩm bàn giao) | Tín hiệu hoàn thành (Self-Verification) |
| :--- | :--- | :--- | :--- | :--- |
| **CP0** | Khởi tạo môi trường, cấu hình `.env`, kiểm tra thư viện | 0 - 30m (30') | Môi trường venv kích hoạt, file `.env` hợp lệ | Console in `Môi trường sẵn sàng` khi test import |
| **CP1** | Ingestion & Bảo toàn dữ liệu gốc (Raw Preservation) | 30m - 60m (30') | `src/ingestion/crossref.py`, 2 raw JSON artifacts | 24 bản ghi raw được lưu, console in hoàn tất tải |
| **CP2** | Data Cleaning & Chuẩn hóa ngữ cảnh `text_for_embedding` | 60m - 95m (35') | `src/ingestion/cleaning.py`, cleaned dataframe | Cleaned dataframe 24 dòng với cột `text_for_embedding` |
| **CP3** | Data Observability với Great Expectations 1.x & Freshness | 95m - 140m (45') | `src/observability/quality.py`, GX suite & SLA checks | `run_data_quality_checks` trả về `success=True` |
| **CP4** | Benchmark Test Set & ChromaDB Vector Store Indexing | 140m - 170m (30') | `src/evaluation/testset.py`, ChromaDB collection | Sinh 10 câu hỏi benchmark, ChromaDB index 24 docs |
| **CP5** | Multi-Provider RAG Agent & Thực thi Baseline (Phase 1) | 170m - 205m (35') | `script/run_phase1.py`, `baseline_metrics.json`, report | Phase 1 sinh báo cáo markdown và baseline Hit Rate |
| **CP6** | Data Corruption Suite, Repair & Báo cáo đối chiếu 3 trạng thái | 205m - 240m (35') | `src/ingestion/corruption.py`, `run_corruption_flow.py`, `corruption_report.md` | Bảng so sánh 3 trạng thái: Baseline vs Corrupted vs Repaired |

---

## Chi Tiết Yêu Cầu Từng Checkpoint

### Checkpoint 0: Khởi tạo Môi trường & Cấu hình (30 phút)
- **Mục tiêu:** Thiết lập workspace Python chuẩn hóa (Python 3.11 - 3.13), cài đặt đầy đủ dependencies qua `uv` hoặc `pip`.
- **Nhiệm vụ:**
  1. Tạo và kích hoạt virtual environment (`.venv`).
  2. Cài đặt các gói phụ thuộc từ `requirements.txt` hoặc `pyproject.toml`.
  3. Tạo file `.env` từ `.env.example`, điền API Key cần thiết (`GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, v.v.).
- **Tín hiệu nghiệm thu:**
  ```bash
  python -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"
  ```
  Console in ra đúng chuỗi `Môi trường sẵn sàng`.

---

### Checkpoint 1: Ingestion & Raw Data Preservation (30 phút)
- **Mục tiêu:** Thu thập dữ liệu metadata bài báo học thuật qua Crossref API và lưu trữ raw artifacts phục vụ data lineage.
- **Nhiệm vụ:**
  1. Xây dựng logic gọi API trong `src/ingestion/crossref.py`, hỗ trợ cơ chế fallback đọc từ snapshot local `data/raw/crossref_response.json` khi mất mạng hoặc dính `429 Too Many Requests`.
  2. Parse các trường: `paper_id` (DOI), `title`, `summary` (làm sạch thẻ JATS XML `<jats:p>`), `authors`, `categories`, `published`.
  3. Lưu 2 file raw artifacts:
     - `data/raw/crossref_response.json`: Toàn bộ raw response từ API.
     - `data/raw/crossref_records.json`: Danh sách đối tượng `PaperRecord` đã parse.
- **Tín hiệu nghiệm thu:**
  ```bash
  python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
  ```
  Console in ra `Tín hiệu hoàn thành: Đã tải 24 bài báo`.

---

### Checkpoint 2: Data Cleaning & Pre-embed Modeling (35 phút)
- **Mục tiêu:** Tiền xử lý, tính toán metadata bổ sung và tạo trường văn bản giàu ngữ cảnh phục vụ sinh vector.
- **Nhiệm vụ:**
  1. Hoàn thiện hàm `build_clean_dataframe` trong `src/ingestion/cleaning.py`.
  2. Loại bỏ khoảng trắng thừa, chuẩn hóa Unicode.
  3. Tính toán tuổi dữ liệu: `age_days = (run_date - published).days`.
  4. Khử trùng lặp bản ghi theo `paper_id`.
  5. Xây dựng trường tổng hợp `text_for_embedding` theo mẫu:
     ```text
     Title: <Tiêu đề>
     Authors: <Tác giả>
     Published: <Ngày xuất bản>
     Categories: <Lĩnh vực>
     Summary: <Tóm tắt>
     ```
- **Tín hiệu nghiệm thu:**
  ```bash
  python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
  ```
  Console in ra `Tín hiệu hoàn thành: Clean thành công 24 dòng`.

---

### Checkpoint 3: Data Observability với Great Expectations 1.x & Freshness SLA (45 phút)
- **Mục tiêu:** Áp dụng công nghệ Data Observability hiện đại, thiết lập bộ kiểm định chất lượng tự động theo chuẩn Great Expectations 1.x và đo lường Freshness SLA.
- **Nhiệm vụ:**
  1. Cấu hình ephemeral context của Great Expectations 1.x trong `src/observability/quality.py`:
     ```python
     context = gx.get_context(mode="ephemeral")
     data_source = context.data_sources.add_pandas(name="papers_source")
     data_asset = data_source.add_dataframe_asset(name="papers_asset")
     batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
     batch = batch_def.get_batch(batch_parameters={"dataframe": df})
     ```
  2. Định nghĩa các Expectation thiết yếu:
     - `ExpectTableRowCountToBeBetween`: Số dòng từ 5 đến 5000.
     - `ExpectColumnValuesToNotBeNull`: Các cột `paper_id`, `title`, `text_for_embedding` không được null.
     - `ExpectColumnValuesToBeUnique`: `paper_id` là định danh duy nhất.
     - `ExpectColumnValueLengthsToBeBetween`: Trường `summary` có độ dài tối thiểu 30 ký tự.
  3. Tính toán Freshness SLA: Cảnh báo `is_fresh = False` nếu tỷ lệ bài báo có `age_days > 180` vượt quá 25%.
- **Tín hiệu nghiệm thu:**
  ```bash
  python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Tín hiệu hoàn thành: Quality check status = {res["success"]}')"
  ```
  Console in ra `Tín hiệu hoàn thành: Quality check status = True`.

---

### Checkpoint 4: Benchmark Test Set & Vector Store Indexing (30 phút)
- **Mục tiêu:** Xây dựng bộ test đánh giá chuẩn hóa gồm 10 câu hỏi qua 4 nhóm nghiệp vụ và đánh chỉ mục vector trên ChromaDB.
- **Nhiệm vụ:**
  1. Viết logic sinh câu hỏi đánh giá trong `src/evaluation/testset.py` phủ đủ 4 nhóm: `summary`, `authors`, `date`, `categories`.
  2. Lưu kết quả ra file `data/eval/eval_testset.json`.
  3. Khởi tạo ChromaDB collection, nạp vector embedding sinh từ `all-MiniLM-L6-v2` cho toàn bộ các tài liệu sạch.
- **Tín hiệu nghiệm thu:**
  ```bash
  python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
  ```
  Console in ra `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`.

---

### Checkpoint 5: Multi-Provider RAG Agent & Thực thi Baseline Phase 1 (35 phút)
- **Mục tiêu:** Chạy end-to-end chu trình dữ liệu sạch, kiểm thử RAG Agent đa nhà cung cấp và đo lường chỉ số nền (Baseline).
- **Nhiệm vụ:**
  1. Hoàn thiện Router Agent hỗ trợ fallback đa provider (`mock`, `google`, `openai`, `anthropic`).
  2. Chạy kịch bản `python script/run_phase1.py`.
  3. Kiểm tra các artifact sinh ra:
     - `data/clean/papers_clean.csv` & `data/clean/papers_clean.json`
     - `data/results/baseline_metrics.json`
     - `data/reports/phase1_report.md`
- **Tín hiệu nghiệm thu:**
  File `data/results/baseline_metrics.json` xuất hiện với các chỉ số `hit_rate > 0.8` và `token_f1 > 0.6`.

---

### Checkpoint 6: Data Corruption Suite, Repair Flow & Báo Cáo Đối Chiếu (35 phút)
- **Mục tiêu:** Giả lập sự cố dữ liệu bẩn trong sản xuất, đo lường sự sụp đổ của RAG Agent, thực thi cơ chế sửa chữa (repair) và lập báo cáo so sánh 3 trạng thái.
- **Nhiệm vụ:**
  1. Triển khai 6 kịch bản làm bẩn dữ liệu trong `src/ingestion/corruption.py`:
     - Drop latest records (mất 20% bản ghi mới).
     - Blank summary (xóa rỗng tóm tắt).
     - Inject noise (chèn ký tự rác vào tóm tắt).
     - Truncate title (cắt ngắn tiêu đề < 8 ký tự).
     - Stale date (lùi ngày xuất bản về quá khứ).
     - Duplicate rows (nhân bản dữ liệu).
  2. Chạy toàn bộ pipeline kiểm chứng qua lệnh:
     ```bash
     python script/run_corruption_flow.py
     ```
  3. Xuất báo cáo đối chiếu chi tiết tại `data/reports/corruption_report.md` với bảng so sánh rõ ràng: Baseline vs Corrupted vs Repaired.
- **Tín hiệu nghiệm thu:**
  Console in ra bảng so sánh hiệu năng 3 trạng thái và file `data/reports/corruption_report.md` chứa đầy đủ phân tích nguyên nhân - giải pháp.
