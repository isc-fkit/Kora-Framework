# tools/confluence-sync — Đồng bộ KB ↔ Confluence chung (GET & POST)

Đẩy tri thức cục bộ (vault + `docs/`) lên **một Confluence chung**, và kéo về cho user
chỉ-đọc. Đây là đường **headless** (chạy trong cron/scheduler, không cần app Claude).
Khi thao tác **trong app**, Kora dùng connector MCP Atlassian — cả hai cùng ghi một file
map (`<vault>/_system/confluence/confluence-map-<host>.json`) nên không tạo trang trùng.

Chỉ dùng thư viện chuẩn Python 3 — không cần `pip install`.

## Cài nhanh

1. Copy `.env.example` → `.env.local`, điền:
   - **API token** (hợp cho cron): `CONFLUENCE_BASE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`.
   - **HOẶC OAuth 2.0**: điền `CONFLUENCE_OAUTH_CLIENT_ID/_SECRET` rồi chạy `--login`.
2. Đặt `confluence.space_key` (+ `parent_page_id`, `permission`) trong `config/factory-config.yaml`.
3. Kiểm tra: `python3 tools/confluence-sync/sync_confluence.py --check`

## Lệnh

| Lệnh | Việc |
|---|---|
| `--check` | Kiểm tra kết nối (không ghi). |
| `--login` | Đăng nhập OAuth 2.0 (mở trình duyệt) 1 lần → lưu `.oauth-token.json` (tự refresh). |
| `--push [--space K --parent ID]` | Đẩy KB → Confluence (upsert idempotent, bỏ qua trang không đổi). |
| `--pull [--space K --into DIR]` | Kéo trang Confluence → vault (mặc định `<vault>/Confluence/`). |
| `--check-fresh` | In JSON độ mới (scheduler/report dùng). |
| `--dry-run` | In kế hoạch, KHÔNG ghi. `--force` đẩy lại tất cả (bỏ qua hash). |

Windows: thay `python3` bằng `py`.

## Phân quyền

- `confluence.permission: read_only` → `--push` bị **từ chối** (chỉ user write mới đẩy lên KB chung).
- `--pull` luôn cho phép.
- Trang đã bị **sửa tay** trên Confluence (version xa hơn mốc local) → push **bỏ qua** thay vì đè
  (`push.on_conflict: skip_human_edited`).

## Bảo mật

- Token chỉ ở `.env.local` / `.oauth-token.json` (đã gitignore). KHÔNG in ra log/chat.
- Lỗi từng trang được **gom** vào `<vault>/_system/confluence/confluence-sync-errors-<date>.{md,json}`
  và **không** làm dừng cả lượt chạy.
