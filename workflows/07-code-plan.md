# Workflow 07 — Implementation Plan cho Claude Code (tùy chọn)

> Trigger: user nhắn "lên kế hoạch code", "implementation plan". Chỉ chạy khi
> feature đã có BR + AC được duyệt.

## Bước 1 — Điều kiện

Kiểm tra `03-business-rules.md` + `04-acceptance-criteria.md` tồn tại và đã duyệt.
Chưa có → quay lại workflow 03, KHÔNG được sửa code khi chưa có BR/AC.

## Bước 2 — Sinh plan

Đọc `02-claude-context.md` (mục Code Rules + Guardrails), source map nếu có.
Tạo `source/06-implementation-plan.md`: file ảnh hưởng, thứ tự việc, rủi ro, test plan.

## Bước 3 — ✋ GATE 4

User approve plan → mới được sửa sourcebase (nếu repo code được kết nối).
Sau khi sửa: cập nhật `07-test-plan.md`, changelog, relation graph (feature → code file).
