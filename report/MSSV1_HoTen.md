# Báo cáo thành viên 1 — Pipeline Integrator

**Họ tên/MSSV:** Cần thay bằng thông tin thật trước khi nộp  
**Vai trò:** Cấu hình, orchestration và tích hợp end to end.

## Phạm vi sở hữu

- Quản lý đường dẫn và cấu hình trong `src/core/`.
- Điều phối baseline trong `src/pipelines/phase1.py`.
- Điều phối corruption, repair và comparison trong `src/pipelines/corruption_flow.py`.
- Xác minh hai entrypoint, artifact paths và tính nhất quán giữa JSON với Markdown.

## Input, output và kết quả

Pipeline nhận raw records và cấu hình môi trường, sau đó tạo clean datasets, ba Chroma collections, benchmark, quality/freshness reports, metrics và hai báo cáo Markdown.

Hai lệnh đã chạy exit code 0:

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

Baseline/corrupted/repaired retrieval hit rate lần lượt là 1.0, 0.4 và 1.0. Token F1 lần lượt là 1.0, 0.3644 và 1.0.

## Quyết định kỹ thuật

Các trạng thái dùng collection và manifest riêng, nhưng dùng chung benchmark. Flow repair dựng lại dữ liệu từ raw records và kiểm tra hai lần chạy bằng dataframe equality cùng SHA-256, tránh sửa trực tiếp dữ liệu lỗi.

## Giới hạn

External LLM Judge và Ragas là tùy chọn. Chế độ mặc định dùng deterministic token-overlap judge và ghi phương pháp trong artifact.

