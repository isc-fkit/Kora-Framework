# Workflow 11 — Sao lưu & dời máy (export → import tri thức)

> Trigger EXPORT: "sao lưu", "xuất tri thức", "backup", "chuyển máy", "dời máy".
> Trigger IMPORT: "nhập tri thức", "khôi phục", "restore", hoặc đưa file `kora-kb-*.zip` / `kora-archive-*.zip`.
> (confirm ý định trước). Tri thức = DATA: vault + `.kb` data + nội dung `docs/` + config setup + `inbox/`.
>
> 📦 **Bàn giao có phân quyền + mật khẩu?** → dùng `workflows/15-archive.md` (`/claude-knowledge-archive`) thay vì luồng này.
> Luồng 11 là **sao lưu/dời máy thuần** (không cổng, không phân quyền). `import-kb` nhận được CẢ hai loại gói.

## A. EXPORT (máy cũ) — đóng gói tri thức

1. Chạy `scripts/export-kb.command` (Claude tự chạy trong Cowork).
   → tạo `kora-kb-<project>-<ngày>.zip` ở gốc repo: DATA + `manifest.json`
   (version, `vault_path`, `project_name`).
2. Báo user đường dẫn file zip (kèm folder tuyệt đối để copy) + "Chép file zip này sang máy mới."
3. **Token:** `.env.local` (token Jira) CÓ trong gói. Nhắc user cân nhắc bảo mật — hoặc xoá
   `.env.local` trước khi export rồi điền lại token ở máy mới.

## B. IMPORT (máy mới) — bung tri thức vào base sạch

Điều kiện: máy mới đã có **base sạch** (tải zip app + giải nén + mở Cowork) và đã chép
`genesis1-kb-*.zip` vào gốc repo.

1. Chạy `scripts/import-kb.command` (hoặc truyền đường dẫn zip).
   → đọc `manifest.json`, bung DATA về đúng chỗ, đặt lại `vault_path` cho khớp,
   **thay sạch** vault cũ nếu trùng tên (hỏi y/N trước).
2. Script tự chạy `python3 tools/kb-indexer/build_index.py --root .` (Windows: `py`) → index khớp tri thức vừa nhập.
3. Báo user: đã nhập N file, vault ở đâu, mở Obsidian "Open folder as vault".
4. Token: nếu `.env.local` không đi kèm → hướng dẫn điền lại để quét Jira tiếp.

## Lưu ý
- Export/import chỉ thao tác DATA, KHÔNG đụng CORE → an toàn với mọi bản app tương thích.
- Gói `kora-kb-*.zip` / `kora-archive-*.zip` đã được gitignore (không lọt vào repo).
- Đây là cách CHÍNH thức "không mất tri thức khi đổi máy": export ở máy cũ → import ở máy mới.
