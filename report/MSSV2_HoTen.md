# Báo cáo thành viên 2 — Data Foundation & Recovery

**Họ tên/MSSV:** Cần thay bằng thông tin thật trước khi nộp  
**Vai trò:** Crossref ingestion, cleaning, data modeling và repair.

## Phạm vi sở hữu

- Parse Crossref response thành `PaperRecord`.
- Hỗ trợ API retry và local snapshot fallback.
- Bảo toàn raw response và parsed records.
- Chuẩn hóa JATS/HTML, Unicode entities và whitespace.
- Tính `age_days`, deduplicate `paper_id` và tạo embedding text năm phần.
- Phục hồi dữ liệu từ `data/raw/crossref_records.json`.

## Data contract

`text_for_embedding` có năm phần: Title, Authors, Published, Categories và Summary. Snapshot hiện không có subject labels nên category dùng fallback minh bạch `Uncategorized`.

## Kết quả và xác minh

Clean baseline và repaired dataset đều có 24 unique papers. Repair được chạy hai lần với cùng raw input; hai SHA-256 giống nhau và repaired hash khớp baseline. Bằng chứng nằm tại `data/results/repair_verification.json`.

## Quyết định kỹ thuật

Raw artifacts không bị sửa trong cleaning hoặc corruption. Mọi derived dataset có thể tái tạo từ raw, giúp repair idempotent và giữ data lineage.

