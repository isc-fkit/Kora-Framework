# Workflow 16 — Sync KB lên target đã kết nối (`/kora-sync`)

> Đẩy tri thức cục bộ (vault + `docs/` + trang `_wiki` tổng hợp) lên **Confluence chung** và/hoặc
> **repo GitHub riêng tư**. Idempotent (KHÔNG nhân bản, chỉ mới/đổi) + versioning US↔Change-Request.
> **CÓ CỔNG MẬT KHẨU vận hành (`KORA_OPS_PW`).** Mỗi bước GHI đều DỪNG hỏi confirm (Approval Gate).
> Gói USER (`.kora-user`) chỉ đồng bộ KB chung theo cấu hình — vẫn áp cổng mật khẩu.

## Bước 1 — Chọn target
Đọc `confluence.enabled` / `github.enabled` (và `.env.local` tương ứng). **AskUserQuestion:**
**[Confluence] / [GitHub] / [Cả hai]** — chỉ hiện target đã cấu hình. Chưa có target nào →
sang **"Cấu hình target"** bên dưới rồi quay lại.

## Bước 2 — Cổng mật khẩu (BẮT BUỘC, trước mọi thao tác đẩy)
Hướng dẫn user đặt biến môi trường `KORA_OPS_PW` (**KHÔNG hỏi qua card, KHÔNG in ra**). Chạy:
```
KORA_OPS_PW="…" python3 tools/archive-gate/verify_ops_password.py
```
Exit `0` → tiếp. Khác `0` → **DỪNG** ("Sai mật khẩu — không đồng bộ"), không làm gì gated.
(Chạy nền/headless không hỏi được → mật khẩu nằm ở `~/.config/kora/ops-pw.env` chmod 600.)

## Bước 3 — Đánh dấu phiên bản US↔Change-Request
```
python3 tools/kb-sync/version_mark.py --root . --dry-run   # liệt kê cặp phát hiện
```
✋ confirm → `python3 tools/kb-sync/version_mark.py --root . --apply` (giữ US cũ + `superseded` +
banner + link CR; thêm cạnh `supersedes`). Rồi reindex: `python3 tools/kb-indexer/build_index.py --root .`.
> Đồ thị thiếu `link_type` (quét bằng bản cũ) → chỉ nhận theo issue-type; nhắc user **quét lại nguồn** cho đủ.

## Bước 4 — Xem trước (Gate 2)
```
python3 tools/confluence-sync/sync_confluence.py --push --dry-run   # nếu chọn Confluence
python3 tools/github-sync/sync_github.py --push --dry-run           # nếu chọn GitHub
```
Trình bày kế hoạch (+tạo / ~cập nhật / -xóa / =bỏ qua). ✋ confirm mới đẩy thật.

## Bước 5 — Đẩy thật (idempotent)
```
python3 tools/confluence-sync/sync_confluence.py --push
python3 tools/github-sync/sync_github.py --push
```
Báo kết quả; ghi `.kb/changelog.md` (ngày · target · số trang · người duyệt).

## Bước 6 — Lần đầu thành công → lưu cấu hình
Ghi vào `config/factory-config.yaml` để lần sau khỏi hỏi lại:
- Confluence: `confluence.enabled: true`, `base_url`, `space_key`, `parent_page_id`.
- GitHub: `github.enabled: true`, `repo`, `branch`.

---

## Cấu hình target (chạy 1 lần)

### Confluence chung (Requirement A — tool đã sẵn)
1. `tools/confluence-sync/.env.local` (copy `.env.example`): `CONFLUENCE_BASE_URL` + (`CONFLUENCE_EMAIL` +
   `CONFLUENCE_API_TOKEN`) **HOẶC** `--login` (OAuth 2.0).
2. Đặt `confluence.space_key` (+ `parent_page_id`) trong config.
3. `python3 tools/confluence-sync/sync_confluence.py --check`.
`confluence.permission: read_only` → `--push` bị từ chối (chỉ `--pull`).

### GitHub riêng tư (Requirement B — git push)
1. Tạo repo **private**; tạo **PAT** scope `repo`.
2. `tools/github-sync/.env.local` (copy `.env.example`): `KORA_GITHUB_SYNC_TOKEN=<PAT>`.
3. `github.repo: "owner/name"`, `branch`, `enabled: true` trong config.
4. `python3 tools/github-sync/sync_github.py --check`.
Token CHỈ ở `.env.local` (gitignore); bơm vào git qua `GIT_CONFIG_*` (KHÔNG vào `.git/config`/argv/log).
Repo đích là **gương 1 chiều** — đừng sửa tay (sẽ bị ghi đè); lịch sử git là vết kiểm toán.

## Bước kế (AskUserQuestion)
**[A]** Đặt lịch tự sync (`/kora-schedule`) · **[B]** Gửi báo cáo (`/kora-send-mail`) · **[C]** Dừng.
