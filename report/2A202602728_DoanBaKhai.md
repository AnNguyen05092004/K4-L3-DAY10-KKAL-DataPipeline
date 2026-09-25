# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                        |
| ------------------ | --------------------------------------------------------------- |
| Họ và tên       | Đoàn Bá Khải                                                   |
| MSSV               | 2A202602728                                                     |
| Khóa/Lớp         | K4 / L3                                                         |
| Tên nhóm         | KKAL                                                            |
| Vai trò chính    | Trưởng nhóm / Pipeline Integrator                              |
| Repository         | https://github.com/AnNguyen05092004/K4-L3-DAY10-KKAL-DataPipeline |
| Ngày hoàn thành | 2026-09-25                                                      |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Cấu hình hệ thống | `src/core/config.py`, `src/core/utils.py` | Biến môi trường `.env` | Settings object, artifact paths | Hoàn thành |
| Baseline orchestration | `src/pipelines/phase1.py` | Raw records, settings | `baseline_metrics.json`, `phase1_report.md` | Hoàn thành |
| Corruption & repair flow | `src/pipelines/corruption_flow.py` | `papers_clean.csv`, raw records | `corruption_log.json`, `corrupted/repaired_metrics.json`, `corruption_report.md` | Hoàn thành |

Tôi chịu trách nhiệm kết nối tất cả module lại thành hai luồng chạy hoàn chỉnh. Module ingestion và cleaning (Lâm), RAG index (Khuyến), evaluation và observability (An) đều phụ thuộc vào artifact path config tôi thiết lập trong `core/`.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------------ | --------- |
| Debug lỗi import `ModuleNotFoundError: No module named 'core'` | Cả nhóm | Hướng dẫn chạy `pip install -e .` (editable install) — tất cả thành viên fix được |
| Kiểm tra tính nhất quán JSON artifact paths giữa phase1 và corruption flow | Đỗ Thanh Lâm, Nguyễn Văn An | Artifact paths đồng bộ, hai flow không bị conflict khi chạy song song |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ----------------------- | ----------------------- |
| Thiết lập config hệ thống | `src/core/config.py` | Settings object dùng chung toàn pipeline | Import và print settings |
| Điều phối baseline end-to-end | `src/pipelines/phase1.py` | `data/results/baseline_metrics.json` | `python script/run_phase1.py` → exit 0 |
| Điều phối corruption & repair | `src/pipelines/corruption_flow.py` | `data/reports/corruption_report.md` | `python script/run_corruption_flow.py` → exit 0 |
| Xác minh idempotency | `src/pipelines/corruption_flow.py` | `data/results/repair_verification.json` | SHA-256 repaired == baseline |

Output cụ thể quan trọng nhất: `data/reports/corruption_report.md` chứa bảng đối chiếu 3 trạng thái (baseline / corrupted / repaired) với số liệu thực tế — đây là bằng chứng chính nhóm dùng để chứng minh Silent Failure và khả năng phục hồi của pipeline.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần chạy đúng thứ tự và không bị lỗi khi một module thay đổi output format. Cụ thể, `phase1.py` phải điều phối 5 bước (ingestion → cleaning → quality check → embedding → evaluation) theo đúng dependency, và `corruption_flow.py` phải đảm bảo 3 collection ChromaDB (baseline / corrupted / repaired) độc lập, dùng chung test set.

### Cách triển khai

`phase1.py` gọi lần lượt các hàm từ module Lâm (ingest → clean), module Khuyến (build index), module An (quality check, freshness, generate test set, evaluate). Mỗi bước kiểm tra artifact output đầu ra trước khi chuyển sang bước tiếp theo — fail fast thay vì chạy tiếp rồi báo lỗi muộn.

`corruption_flow.py` thực hiện: (1) chạy phase1 để có baseline, (2) tiêm 6 lỗi vào `papers_clean.csv`, (3) re-index vào collection `papers-corrupted`, (4) re-evaluate để lấy `corrupted_metrics.json`, (5) repair từ raw records, (6) re-index vào `papers-repaired`, (7) re-evaluate để lấy `repaired_metrics.json`, (8) so sánh 3 bộ metrics và xuất `corruption_report.md`.

Repair được thiết kế idempotent: chỉ đọc từ `data/raw/crossref_records.json` (artifact không bao giờ bị sửa), chạy lại cleaning pipeline và verify SHA-256 của output khớp baseline.

### Input, output và contract

| Thành phần                   | Mô tả |
| ------------------------------ | ------- |
| Input                          | `data/raw/crossref_records.json` (từ Lâm), `src/core/config.py` (settings) |
| Output                         | `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |
| Module phụ thuộc             | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py` (Lâm); `src/retrieval/` (Khuyến); `src/observability/` (An) |
| Module sử dụng output        | Không có — pipeline orchestrator là điểm cuối |
| Điều kiện lỗi cần xử lý | `FileNotFoundError` khi artifact thiếu (fail fast với message rõ ràng), `KeyError` khi schema không khớp |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả hai lệnh exit code 0, in ra log từng bước.
- **Kết quả thực tế:** Exit code 0. `data/results/baseline_metrics.json` có `retrieval_hit_rate: 1.0`.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/repaired_metrics.json`, `data/results/repair_verification.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định liệu 3 trạng thái (baseline / corrupted / repaired) dùng chung hay tách riêng ChromaDB collection.
- **Các phương án đã cân nhắc:**
  1. Dùng chung một collection, xóa và nạp lại dữ liệu mỗi khi chuyển trạng thái.
  2. Tạo 3 collection riêng biệt (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
- **Phương án đã chọn:** 3 collection riêng biệt.
- **Lý do:** Nếu dùng chung và xóa đi nạp lại, không thể chạy evaluation song song và không thể so sánh "livequery" giữa các trạng thái. 3 collection riêng giúp debug từng trạng thái độc lập và đảm bảo reproducibility — baseline metrics không thay đổi dù corruption flow đã chạy.
- **Bằng chứng quyết định phù hợp:** `data/results/baseline_metrics.json` và `data/results/repaired_metrics.json` có cùng `retrieval_hit_rate: 1.0` dù được tạo ở các thời điểm khác nhau trong pipeline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'core'` khi chạy `python script/run_phase1.py`.
- **Lệnh tái hiện:** `python script/run_phase1.py` (chưa cài editable package).
- **Nguyên nhân gốc:** Python không nhận thư mục `src/` là package vì chưa chạy `pip install -e .`. Script import trực tiếp từ `core` nhưng Python chỉ tìm trong `sys.path` không chứa `src/`.
- **Cách xử lý:** Chạy `pip install -e .` để đăng ký project theo chế độ editable, đưa `src/` vào `sys.path` thông qua `pyproject.toml`.
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_phase1.py` → exit code 0.
- **Điều học được:** Bắt buộc đọc `pyproject.toml` và hướng dẫn cài đặt trước khi chạy bất kỳ script nào trong project Python có cấu trúc package.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu từ Crossref đến vector index:** Lâm fetch raw JSON từ API (hoặc offline snapshot), parse thành `PaperRecord`, cleaning module chuẩn hóa và tạo `text_for_embedding`. Khuyến đọc JSON, tạo embedding bằng MiniLM, nạp vào ChromaDB collection `papers-baseline`.

2. **Evaluation set và ground-truth:** An sinh 10 câu hỏi từ cleaned dataset, mỗi câu có `ground_truth_doc_ids` là `paper_id` của document liên quan. Khi evaluate, retrieval trả `top_k=5` documents, hit nếu ground truth nằm trong kết quả. Token F1 đo overlap giữa retrieved text và ground truth text.

3. **Quality checks vs freshness monitoring:** Quality checks (GX 1.x) kiểm tra schema và nội dung dữ liệu tại thời điểm cleaning (row count, non-null, unique ID, summary length). Freshness monitoring kiểm tra `age_days` — bao nhiêu % document đã cũ hơn ngưỡng — để phát hiện khi data source không được cập nhật.

4. **Cùng test set cho cả 3 trạng thái:** Nếu test set khác nhau, ta không thể kết luận metric thay đổi là do data quality hay do câu hỏi khó hơn/dễ hơn. Test set cố định là controlled variable trong thí nghiệm này.

5. **Repair thành công khi:** `data/results/repair_verification.json` xác nhận SHA-256 của repaired dataset khớp baseline, VÀ `repaired_metrics.json` có `retrieval_hit_rate` và `mean_token_f1` bằng hoặc xấp xỉ baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét |
| ---------------------- | -------: | --------: | -------: | --------- |
| `retrieval_hit_rate` | 1.0000 | 0.4000 | 1.0000 | Giảm 60% khi corrupted — nghiêm trọng |
| `mean_token_f1`      | 1.0000 | 0.3644 | 1.0000 | Token overlap gần như mất hoàn toàn |
| `judge_accuracy`     | 1.0000 | 0.4000 | 1.0000 | Phục hồi hoàn toàn sau repair |
| `mean_judge_score`   | 1.0000 | 0.3644 | 1.0000 | Phục hồi hoàn toàn sau repair |
| Quality checks         | PASS | FAIL | PASS | Gate phát hiện đúng khi corrupt |
| Freshness status       | FRESH | STALE | FRESH | Stale ratio 33.33% khi corrupted |

### Kết luận từ số liệu

1. **Drop abstract + inject noise** → Non-null check FAIL, summary length FAIL → `mean_token_f1` giảm từ 1.0 xuống 0.364 vì embedding mất ngữ nghĩa, retrieval trả sai document.
2. **Idempotent repair từ raw records** → Quality Gate PASS, Freshness FRESH → `retrieval_hit_rate` và `mean_token_f1` phục hồi về 1.0 — xác nhận chiến lược "raw preservation" là chìa khóa để repair đáng tin cậy.

Corruption ảnh hưởng rõ nhất: **drop abstract** (xóa summary) — vì `text_for_embedding` mất phần Summary quan trọng nhất, MiniLM không thể tạo embedding gần đúng, kết quả retrieval gần như random.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Idempotency không tự nhiên có — phải thiết kế từ đầu: không sửa raw artifact, mọi derived artifact đều có thể tái tạo, verify bằng hash.
2. **Data quality/observability:** GX 1.x phát hiện lỗi tại "trạm kiểm soát" trước khi data vào vector store — đây là tuyến phòng thủ quan trọng nhất chống Silent Failure.
3. **RAG + data quality:** Một RAG agent tốt đến đâu cũng vô dụng nếu vector store chứa dữ liệu corrupt — `retrieval_hit_rate` giảm 60% chỉ từ 6 loại lỗi thực tế rất phổ biến.

### Nếu có thêm thời gian

Tích hợp alerting tự động: khi Quality Gate FAIL hoặc Freshness STALE, gửi notification (email hoặc Slack) thay vì chỉ ghi log. Đo cải thiện bằng cách xác minh alert được nhận trong vòng 1 phút sau khi pipeline phát hiện lỗi.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đoàn Bá Khải
**Ngày xác nhận:** 2026-09-25
