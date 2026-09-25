# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo cá nhân của Đoàn Bá Khải - Trưởng nhóm & Pipeline Integrator

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đoàn Bá Khải             |
| MSSV               | 2A202602728                     |
| Khóa/Lớp         | K4-L3-DAY10              |
| Tên nhóm         | KKAL     |
| Vai trò chính    | Trưởng nhóm / Pipeline Integrator                 |
| Repository         | https://github.com/VinUni-AI20k/K4-L3-DAY10-KKAL-DataPipeline |
| Ngày hoàn thành | 2026-09-25               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Thiết lập cấu hình hệ thống      | `src/core/config.py`, `src/core/utils.py`           | `.env` config          | Settings object, Setup folders | Hoàn thành |
| Điều phối Baseline Pipeline      | `src/pipelines/phase1.py`           | Raw Data          | Các metric baseline | Hoàn thành |
| Điều phối Corruption & Repair    | `src/pipelines/corruption_flow.py`           | Baseline artifacts          | Corrupted & Repaired Metrics, Báo cáo 3 trạng thái | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Quản lý nhóm và Review code | Toàn bộ các thành viên | Tất cả module được chạy nối tiếp trơn tru, không có lỗi tích hợp, hoàn thành 7 checkpoints trước hạn |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Chạy Pipeline Phase 1 | `script/run_phase1.py` | `data/results/baseline_metrics.json` | Lệnh `python script/run_phase1.py` trả về exit code 0 |
| Chạy Corruption & Repair Flow | `script/run_corruption_flow.py` | `data/reports/corruption_report.md` | Lệnh `python script/run_corruption_flow.py` trả về exit code 0 |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

File tổng hợp báo cáo 3 trạng thái `data/reports/corruption_report.md` thể hiện rõ số liệu Baseline, Corrupted, và Repaired do hàm orchestration mà tôi phụ trách tạo ra.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Bài lab yêu cầu xây dựng một pipeline xuyên suốt từ đầu đến cuối, gồm nhiều công đoạn: Ingestion -> Cleaning -> Quality Gate -> Vector Indexing -> Evaluation. Vấn đề là nếu không có một orchestration chuẩn (Phase 1, Corruption flow), các module sẽ chạy rời rạc, không đảm bảo tính Idempotent (chạy lại bao nhiêu lần vẫn ra 1 kết quả) và không so sánh được 3 trạng thái.

### Cách triển khai

Tôi đã viết các file orchestration (`phase1.py` và `corruption_flow.py`) đóng vai trò như bộ điều khiển trung tâm. Nó nhận vào các object cấu hình từ `core/config.py`, sau đó gọi lần lượt các hàm từ module `ingestion`, `observability`, `retrieval`, `evaluation`. Ở pha 2, tôi thực hiện logic: tải lại test set, khởi tạo 2 collection riêng biệt (corrupted và repaired), tiêm lỗi, ghi log, index vào collection tương ứng và sinh ra báo cáo so sánh cuối cùng.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Snapshot JSON, Cấu hình trong file `.env`           |
| Output                         | Pipeline metrics, bảng markdown `corruption_report.md` |
| Module phụ thuộc             | `crossref.py`, `cleaning.py`, `quality.py`, `index.py`, `testset.py`, `metrics.py` |
| Module sử dụng output        | Báo cáo đánh giá tổng kết nhóm                    |
| Điều kiện lỗi cần xử lý | Xử lý collection ChromaDB bị duplicate bằng cách cô lập vector store |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** In ra terminal quá trình tiêm lỗi, kiểm tra GX bị Failed, và quá trình phục hồi thành công.
- **Kết quả thực tế:** Code chạy mượt mà, metrics xuất ra chuẩn xác ở cả 3 trạng thái.
- **Artifact/log:** `data/reports/corruption_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi chạy 3 trạng thái (Baseline, Corrupted, Repaired), cần lưu trữ Vector Index như thế nào để không bị lẫn lộn dữ liệu.
- **Các phương án đã cân nhắc:** (1) Dùng chung 1 collection và xoá đi add lại sau mỗi trạng thái. (2) Tạo 3 collection độc lập cho 3 trạng thái.
- **Phương án đã chọn:** Tạo 3 collection riêng biệt (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
- **Lý do:** Giúp tránh hiện tượng Silent Failure do delete không sạch, đồng thời dễ dàng debug và query song song khi đối chiếu kết quả. Đảm bảo tính Idempotent cho pipeline.
- **Bằng chứng quyết định phù hợp:** Hit rate và F1 của Baseline và Repaired giống nhau hoàn toàn (1.000), chứng tỏ dữ liệu được cô lập rất tốt.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'core'`
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_phase1.py` ngay sau khi clone mà chưa cài package `src`.
- **Nguyên nhân gốc:** Python không nhận diện thư mục `src/` dưới dạng module nội bộ của project nếu không cài đặt ở chế độ editable package.
- **Cách xử lý:** Cài đặt lại chuẩn môi trường bằng lệnh `uv sync` (hoặc `python -m pip install -e .`) và đảm bảo mọi thành viên trong nhóm cũng làm tương tự.
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_phase1.py` không còn lỗi import.
- **Điều học được:** Tầm quan trọng của setup môi trường và file cấu hình dependencies `pyproject.toml`.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
   - Raw data từ Crossref -> Lưu local snapshot -> Clean & chuẩn hoá thành dataframe -> Chạy kiểm tra Quality Gate bằng GX -> Nếu pass, text_for_embedding sẽ được encode bằng MiniLM và index vào ChromaDB.
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
   - Test set chứa câu hỏi và `document_id` nguồn. Khi truy vấn Vector DB, ta lấy top k ID trả về so sánh với `ground_truth_id` để tính Hit Rate. Dựa vào answer text trả lời từ Agent so với text mẫu để tính Token F1 hoặc đưa cho LLM làm giám khảo đánh giá.
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
   - Quality checks kiểm tra tính toàn vẹn và hợp lệ (schema chuẩn, không null, title đủ ký tự), còn freshness giám sát độ cũ/mới (age_days <= max_days), tránh việc dữ liệu bị lỗi thời (Stale Data).
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
   - Để đảm bảo tính công bằng. Nếu câu hỏi thay đổi, sự sụt giảm điểm số có thể do đề bài khó lên chứ không phải do Data Pipeline bị hỏng.
5. Repair được xem là thành công dựa trên artifact và metric nào?
   - Dựa vào việc metric (Hit Rate, F1) của Repaired khôi phục lại chính xác mức điểm 1.0 của Baseline, và Quality Gate vượt qua tất cả kiểm tra (PASS).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |       0.4 |      1.0 | Điểm giảm rất mạnh chứng tỏ khi dữ liệu rác vào, Retriever mất định hướng. |
| `mean_token_f1`      |      1.0 |       0.3644 |      1.0 | LLM không lấy được context chuẩn nên trả lời thiếu sót thông tin. |
| `judge_accuracy`     |      1.0 |       0.3 |      1.0 | Độ chính xác của Agent giảm sút rất lớn theo góc nhìn LLM Judge. |
| `mean_judge_score`   |      5 |       2.2 |      5 | Điểm judge rớt xuống mức kém, báo động hiện tượng Hallucination. |
| Quality checks         |      PASS |       FAIL |      PASS | GX 1.x chặn đứng và báo lỗi thành công đối với dữ liệu rác. |
| Freshness status       |      FRESH |       STALE |      FRESH | Giám sát độ tươi phát hiện ra bài báo đã quá cũ. |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. **[Data corruption]** (Tiêm lỗi rác, xóa summary, làm cũ ngày) → **[quality/freshness signal thay đổi]** (Từ Pass -> Fail/Stale) → **[agent metric thay đổi]** (Hit Rate sập từ 1.0 xuống 0.4).
2. **[Repair action]** (Khôi phục tự động từ Raw snapshot và clean lại) → **[quality/freshness signal phục hồi]** (Từ Fail -> Pass) → **[agent metric phục hồi]** (Hit Rate quay lại đúng 1.0).

Corruption nào ảnh hưởng rõ nhất và vì sao?
- Các lỗi như `drop_latest_records` và `blank_summary` ảnh hưởng trực tiếp đến nội dung được query. Retriever dựa vào ngữ nghĩa (Embedding) để search, khi bản tóm tắt trống rỗng hoặc bản ghi bị vứt bỏ, hệ thống không thể tìm thấy context trả cho LLM.

Kết quả nào khác với kỳ vọng ban đầu?
- Ở trạng thái Corrupted, tôi cứ tưởng Hit Rate sẽ bằng 0%, nhưng kết quả vẫn đạt 0.4. Điều này cho thấy hệ thống Vector Search vẫn có sự bù đắp từ các trường dữ liệu còn lại (như title hoặc author), tuy nhiên với F1 rất thấp (0.36) thì câu trả lời từ hệ thống RAG không có giá trị sử dụng.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Sự nguy hiểm của "Silent Failure" trong AI/RAG: LLM không bao giờ báo lỗi đỏ khi Data Pipeline bị hỏng, nó vẫn sẽ trả lời nhưng sai bét, đó là lý do Data Observability cực kỳ quan trọng.
2. Tầm quan trọng của Orchestration trong Data Pipeline để dễ dàng cô lập và tự động hóa các thử nghiệm end-to-end.
3. Tính Idempotent (Idempotency): Khả năng sửa sai tự động từ Root Data, đảm bảo chạy đi chạy lại vẫn sinh ra cùng một Output sạch và khôi phục được trạng thái chuẩn.

### Nếu có thêm thời gian

Tôi sẽ nghiên cứu cấu hình Great Expectations lưu trữ Data Docs dưới dạng giao diện web (HTML) để báo cáo lỗi trông trực quan hơn thay vì chỉ nhìn console hay JSON logs.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đoàn Bá Khải
**Ngày xác nhận:** 2026-09-25
