# Báo cáo thành viên 4 — Observability & Evaluation

**Họ tên/MSSV:** Cần thay bằng thông tin thật trước khi nộp  
**Vai trò:** Great Expectations, freshness, benchmark, metrics và reporting.

## Phạm vi sở hữu

- Quality Gate bằng Great Expectations 1.x ephemeral pandas datasource.
- Row count, non-null, unique ID và summary-length expectations.
- Freshness SLA với ngưỡng 180 ngày và stale ratio 25%.
- Benchmark cố định 10 câu thuộc summary, authors, date, category và multi-hop.
- Hit Rate, Token F1, judge metrics và Markdown reports.

## Kết quả

| Signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.0000 | 0.4000 | 1.0000 |
| Mean Token F1 | 1.0000 | 0.3644 | 1.0000 |
| Quality Gate | PASS | FAIL | PASS |
| Freshness | FRESH | STALE | FRESH |

Corrupted data có stale ratio 33.33%. Quality Gate phát hiện duplicate IDs và summaries quá ngắn.

## Quyết định kỹ thuật

Multi-hop retrieval chỉ được tính hit khi tìm đủ toàn bộ ground-truth document IDs. Ba trạng thái dùng cùng một test set. Judge mặc định là deterministic token overlap; phương pháp được ghi rõ để không trình bày nhầm thành external LLM Judge.

