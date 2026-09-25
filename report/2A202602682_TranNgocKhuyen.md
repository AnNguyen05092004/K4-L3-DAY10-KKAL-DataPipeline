# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                        |
| ------------------ | --------------------------------------------------------------- |
| Họ và tên       | Trần Ngọc Khuyến                                               |
| MSSV               | 2A202602682                                                     |
| Khóa/Lớp         | K4 / L3                                                         |
| Tên nhóm         | KKAL                                                            |
| Vai trò chính    | RAG & Vector Index Specialist                                   |
| Repository         | https://github.com/AnNguyen05092004/K4-L3-DAY10-KKAL-DataPipeline |
| Ngày hoàn thành | 2026-09-25                                                      |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Embedding & index | `src/retrieval/index.py` — `LocalEmbeddingIndex.build_from_clean()`, `semantic_search()` | `data/clean/papers_clean.json` | ChromaDB collection, `data/embeddings/papers_embeddings.json` | Hoàn thành |
| QA Agent | `src/retrieval/agent.py` — `answer_question()` | Query string, ChromaDB collection | Retrieved context + answer | Hoàn thành |
| Test set generation | `src/evaluation/testset.py` — `generate_test_set()` | `data/clean/papers_clean.json` | `data/eval/test_set.json` (10 câu, 5 loại) | Hoàn thành |

Module observability (An) và pipeline orchestrator (Khải) phụ thuộc vào ChromaDB collection tôi build và interface `semantic_search()` tôi định nghĩa.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------------ | --------- |
| Debug lỗi ChromaDB collection tồn tại khi chạy lại pipeline | Đoàn Bá Khải (orchestrator) | Thêm logic `delete_collection_if_exists()` trước khi build, pipeline idempotent |
| Giải thích cách `ground_truth_doc_ids` được dùng trong hit rate | Nguyễn Văn An (evaluation) | An hiểu đúng contract, hit rate tính chính xác |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ----------------------- | ----------------------- |
| Build ChromaDB 3 collections | `src/retrieval/index.py` | `data/chroma/papers-baseline`, `papers-corrupted`, `papers-repaired` — mỗi collection 24 documents | `collection.count() == 24` |
| Tạo embedding manifest | `build_from_clean()` | `data/embeddings/papers_embeddings.json` | File tồn tại, JSON hợp lệ |
| Sinh test set | `src/evaluation/testset.py` | `data/eval/test_set.json` — 10 câu, 5 loại | File tồn tại, 10 entries, có `ground_truth_doc_ids` |
| Smoke test retrieval | `semantic_search()` | Retrieval hit rate baseline = 1.0 | Chạy evaluate trên 10 câu |

Output quan trọng nhất: `data/eval/test_set.json` — đây là "bộ đề thi" cố định được dùng cho cả 3 trạng thái. Nếu file này sai hoặc thiếu `ground_truth_doc_ids`, toàn bộ evaluation pipeline cho kết quả sai.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Cần xây dựng vector index để RAG agent có thể tìm kiếm ngữ nghĩa (semantic search) trên 24 bài báo khoa học. Index phải hỗ trợ 3 collection độc lập (baseline / corrupted / repaired) để so sánh được retrieval quality ở từng trạng thái mà không can thiệp lẫn nhau.

Ngoài ra, cần sinh test set đủ đa dạng (5 loại câu hỏi) và có `ground_truth_doc_ids` chính xác để evaluation có ý nghĩa.

### Cách triển khai

`build_from_clean()` đọc `papers_clean.json`, dùng `SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')` để encode `text_for_embedding` thành vector 384 chiều, nạp vào ChromaDB với `paper_id` làm document ID và các field metadata (`title`, `published`, `authors_joined`). Trước khi build, kiểm tra và xóa collection cũ nếu tồn tại để đảm bảo idempotency.

`semantic_search(query, top_k=5)` encode query bằng cùng model, gọi `collection.query()` với `n_results=top_k`, trả về list of `(paper_id, distance, metadata)`.

`generate_test_set()` lấy ngẫu nhiên papers từ cleaned dataset, sinh câu hỏi theo 5 loại: `summary` (hỏi về nội dung abstract), `authors` (hỏi tên tác giả), `date` (hỏi năm xuất bản), `category` (hỏi lĩnh vực), `multi-hop` (hỏi so sánh 2 papers). Mỗi câu có `ground_truth` text và `ground_truth_doc_ids` list để tính hit rate.

### Input, output và contract

| Thành phần                   | Mô tả |
| ------------------------------ | ------- |
| Input                          | `data/clean/papers_clean.json` — list of dicts với các field: `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `text_for_embedding` |
| Output                         | ChromaDB collection (tên được đọc từ settings), `data/embeddings/papers_embeddings.json`, `data/eval/test_set.json` |
| Module phụ thuộc             | `src/ingestion/cleaning.py` (Lâm — cung cấp `papers_clean.json`), `src/core/config.py` (Khải — collection names và paths) |
| Module sử dụng output        | `src/observability/quality.py` (An — evaluate metrics); `src/pipelines/phase1.py`, `corruption_flow.py` (Khải — gọi `build_from_clean()` và `semantic_search()`) |
| Điều kiện lỗi cần xử lý | `KeyError: 'text_for_embedding'` nếu cleaning schema sai, ChromaDB collection conflict nếu không xóa trước khi build lại |

### Cách xác minh

```bash
python script/run_phase1.py
```

- **Kết quả mong đợi:** ChromaDB collection `papers-baseline` có 24 documents; `data/eval/test_set.json` có 10 entries.
- **Kết quả thực tế:** `collection.count() == 24`; baseline retrieval hit rate = 1.0.
- **Artifact/log:** `data/embeddings/papers_embeddings.json`, `data/eval/test_set.json`, `data/chroma/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi corruption flow chạy, cần build collection `papers-corrupted` mà không làm mất collection `papers-baseline` đã build ở phase 1.
- **Các phương án đã cân nhắc:**
  1. Xóa toàn bộ ChromaDB và build lại từ đầu mỗi lần chạy.
  2. Tạo 3 collection riêng biệt với tên khác nhau, không xóa collection cũ khi build mới.
- **Phương án đã chọn:** 3 collection riêng biệt — `papers-baseline`, `papers-corrupted`, `papers-repaired`.
- **Lý do:** Phương án 1 phá vỡ khả năng chạy lại evaluation trên baseline sau khi corruption flow đã xong. Nếu muốn so sánh 3 trạng thái "trực tiếp" (query cùng lúc vào 3 collection), phương án 2 là bắt buộc. Hơn nữa, 3 collection riêng giúp debug từng trạng thái độc lập.
- **Bằng chứng:** Sau khi chạy xong `run_corruption_flow.py`, có thể vẫn query `papers-baseline` và nhận hit rate = 1.0 — chứng minh baseline không bị ảnh hưởng bởi corruption flow.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `chromadb.errors.InvalidCollectionException: Collection papers-baseline already exists` khi chạy phase1 lần thứ hai.
- **Lệnh tái hiện:** Chạy `python script/run_phase1.py` hai lần liên tiếp mà không xóa ChromaDB.
- **Nguyên nhân gốc:** `build_from_clean()` gọi `client.create_collection()` mà không kiểm tra collection đã tồn tại hay chưa. ChromaDB không tự overwrite collection có tên trùng.
- **Cách xử lý:** Thêm logic:
  ```python
  try:
      client.delete_collection(collection_name)
  except Exception:
      pass
  collection = client.create_collection(collection_name)
  ```
  Trước mỗi lần `create_collection()`, đảm bảo collection cũ được xóa.
- **Cách xác minh:** Chạy `python script/run_phase1.py` hai lần liên tiếp — lần hai exit code 0, không raise exception.
- **Điều học được:** API `create_collection()` của ChromaDB không phải upsert — cần tự handle idempotency. Luôn kiểm tra và dọn dẹp state cũ trước khi tạo mới trong pipeline production.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu từ Crossref đến vector index:** Lâm parse raw JSON thành records, cleaning tạo `text_for_embedding`. Tôi encode chuỗi này bằng MiniLM (384-dim), nạp vector + metadata vào ChromaDB với `paper_id` làm ID. Index sẵn sàng cho semantic search.

2. **Evaluation set và ground-truth:** Tôi sinh 10 câu hỏi từ cleaned dataset, mỗi câu gắn `ground_truth_doc_ids` là `paper_id` của document liên quan. Khi evaluate, An dùng `semantic_search()` của tôi để lấy `top_k=5` documents, tính hit nếu ground truth `paper_id` nằm trong kết quả.

3. **Quality checks vs freshness:** Quality checks (GX) kiểm tra tính đúng của schema cleaned data trước khi index. Freshness kiểm tra `age_days` — dữ liệu trong index có còn "tươi" không. Hai loại check bổ sung cho nhau: GX bắt lỗi format/content, freshness bắt lỗi temporal.

4. **Cùng test set:** Test set cố định là biến kiểm soát. Thay đổi test set giữa các trạng thái sẽ invalidate so sánh — ta không biết metric thay đổi do data hay do câu hỏi.

5. **Repair thành công khi:** Collection `papers-repaired` có đúng 24 documents (không thiếu, không duplicate), VÀ `repaired_metrics.json` có `retrieval_hit_rate` = 1.0 khi chạy cùng test set.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét |
| ---------------------- | -------: | --------: | -------: | --------- |
| `retrieval_hit_rate` | 1.0000 | 0.4000 | 1.0000 | 6/10 câu miss retrieval khi corrupt — nghiêm trọng |
| `mean_token_f1`      | 1.0000 | 0.3644 | 1.0000 | Noise trong text phá vỡ token overlap |
| `judge_accuracy`     | 1.0000 | 0.4000 | 1.0000 | Phục hồi hoàn toàn |
| `mean_judge_score`   | 1.0000 | 0.3644 | 1.0000 | Phục hồi hoàn toàn |
| Quality checks         | PASS | FAIL | PASS | GX kích hoạt đúng |
| Freshness status       | FRESH | STALE | FRESH | Stale date injection hiệu quả |

### Kết luận từ số liệu

1. **Inject noise vào `text_for_embedding`** → Embedding vector lệch khỏi vector của câu hỏi → `retrieval_hit_rate` giảm từ 1.0 xuống 0.4 — 6/10 câu hỏi không tìm được document đúng.
2. **Repair tái tạo `papers_clean.json` sạch → Re-index vào `papers-repaired`** → Embedding vector khôi phục → `retrieval_hit_rate` = 1.0, xác nhận embedding index sạch là điều kiện đủ để retrieval phục hồi.

Corruption ảnh hưởng rõ nhất: **inject noise + drop abstract** — vì `text_for_embedding` là input trực tiếp vào MiniLM; bất kỳ noise nào trong chuỗi này đều làm lệch vector embedding và dẫn đến retrieval sai.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** ChromaDB collection không phải magic — quality của vector index phụ thuộc 100% vào quality của `text_for_embedding`. "Garbage in → garbage embedding → garbage retrieval."
2. **Data quality:** GX checks ở tầng cleaning cần chạy trước khi build index. Nếu skip quality check, index bị corrupt mà không có cảnh báo — đây là root cause của Silent Failure.
3. **RAG:** `top_k=5` trên 24 documents là tỉ lệ 21% — cao hơn nhiều so với production thực tế. Với corpus lớn hơn, impact của noise sẽ còn nghiêm trọng hơn vì signal-to-noise ratio thấp hơn.

### Nếu có thêm thời gian

Thử nghiệm các embedding model lớn hơn (ví dụ `all-mpnet-base-v2` hoặc `bge-m3`) để xem liệu model tốt hơn có robust hơn với noise không. Đo cải thiện bằng cách so sánh `retrieval_hit_rate` sau corruption giữa các model.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Ngọc Khuyến
**Ngày xác nhận:** 2026-09-25
