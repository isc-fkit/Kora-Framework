# Workflow 05 — Sync kết quả Claude Design về Knowledge Base

> Trigger: user nhắn "sync design", dán mô tả/screenshot/code prototype đã chỉnh.

## Bước 1 — Thu nhận thay đổi

Input chấp nhận: mô tả bằng lời, screenshot, file HTML/code prototype, hoặc file .md
xuất từ Claude Design. Đưa vào `inbox/raw/text/design-sync-<ngày>/`.

## Bước 2 — So sánh với KB

1. Đọc design brief + claude-context + BR/AC của feature liên quan.
2. Liệt kê các thay đổi phát hiện được, chia 3 nhóm:
   - **Chỉ thay đổi UI** (màu, layout) → cập nhật design note là đủ.
   - **Thay đổi hành vi** (luồng, validate, trạng thái) → ảnh hưởng BR/AC → phải sửa
     `03-business-rules.md` / `04-acceptance-criteria.md` / `01-user-document.md`.
   - **Mâu thuẫn với rule đã chốt** → cảnh báo rõ, đề nghị user quyết định.

## Bước 3 — ✋ GATE 3: Trình bày + confirm

Trình bày bằng tiếng Việt: "Prototype có N thay đổi, trong đó X ảnh hưởng nghiệp vụ...
File sẽ sửa: ...". Chờ user duyệt (all / chọn / từ chối).

## Bước 4 — Ghi (sau approve)

- Cập nhật các file trong `docs/03-features/F-xxx/source/`, bump version.
- Cập nhật note vault + backlink, `projects/_registry.md` (trạng thái màn hình).
- Cập nhật `.kb/relation-graph.json`, `source-registry.json`
  (source_type: `design_sync`), `changelog.md` + `source/changelog.md` của feature.
- Nếu là quyết định thiết kế lớn → tạo ADR trong `docs/06-decisions/`.
