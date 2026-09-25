# Báo cáo thành viên 3 — RAG & Vector Index

**Họ tên/MSSV:** Cần thay bằng thông tin thật trước khi nộp  
**Vai trò:** RAG, MiniLM embedding, ChromaDB và kiểm tra truy xuất.

## Phần việc đã thực hiện

- Bổ sung `LocalEmbeddingIndex.build_from_clean()` để đọc `data/clean/papers_clean.json`, tạo lại collection ChromaDB và lưu manifest tại `data/embeddings/papers_embeddings.json`.
- Bổ sung `semantic_search(query, top_k)` và cho phép khởi tạo index bằng `LocalEmbeddingIndex(settings, collection_name=...)`.
- Giữ mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`; collection baseline, corrupted và repaired có tên riêng trong cấu hình.
- Hỗ trợ checkpoint 2: tạo benchmark 10 câu thuộc 5 loại, có ground truth và document ID từ dữ liệu sạch.

## Input và output

| Input | Output |
| --- | --- |
| `data/clean/papers_clean.json` với `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `text_for_embedding` | ChromaDB `papers-baseline`, manifest embedding, kết quả `semantic_search` |
| Clean dataframe | `data/eval/test_set.json` gồm 10 mẫu; mỗi mẫu có `id`, `type`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` |

## Cách xác minh

Đã chạy `python script/run_phase1.py` và `python script/run_corruption_flow.py`. Collection baseline, corrupted và repaired đều có 24 documents. Benchmark có 10 câu; baseline retrieval hit rate là 1.0, corrupted là 0.4 và repaired là 1.0.

## Trạng thái và giới hạn hiện tại

Phần RAG/vector index đã được xác minh end to end. Snapshot Crossref không có subject labels nên category metadata dùng giá trị fallback `Uncategorized`. LLM judge và Ragas là tùy chọn; kết quả mặc định dùng deterministic token-overlap judge và ghi rõ trong metrics/report.
