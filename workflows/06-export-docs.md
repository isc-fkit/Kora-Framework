# Workflow 06 — Xuất tài liệu DOCX / PDF cho người đọc

> Trigger: user nhắn "xuất tài liệu", "export", hoặc chọn [B] sau workflow 03.

## Bước 1 — Hỏi phạm vi

- Xuất feature nào? (liệt kê từ `docs/03-features/`) hay toàn bộ KB?
- Loại tài liệu: URD (từ `01-user-document.md`), SRS (tổng hợp BR + AC + context),
  hay cả hai?
- Định dạng: DOCX, PDF, hay cả hai?

## Bước 2 — Sinh tài liệu

1. Đọc source `.md` của feature (KHÔNG sửa source khi export).
2. Dùng skill docx/pdf tạo file đặt tên:
   `F-xxx-<slug>-URD-v<version>.docx` (version lấy từ frontmatter).
3. Lưu vào `docs/03-features/F-xxx/export/`.
4. Nội dung phải: tiếng Việt chuẩn, có mục tiêu/phạm vi/luồng/rule/tiêu chí nghiệm thu,
   header-footer có tên project + version + ngày.

## Bước 3 — Bàn giao

- Present file cho user mở trực tiếp.
- Ghi changelog (file xuất, version, ngày).
