# tools/github-sync — Đẩy KB → repo GitHub riêng tư (git push)

Anh em với `tools/confluence-sync`, nhưng target là một **git repo private**. Gom tri thức
cục bộ (`docs/` + vault) → **git push** lên repo. Đường **headless** (chạy được trong scheduler).

Chỉ thư viện chuẩn Python 3 + lệnh `git`.

## Cài nhanh

1. Tạo repo **private** trên GitHub (vd `isc-fkit/kb-mirror`).
2. Tạo **PAT** scope `repo` (Settings → Developer settings → Personal access tokens).
3. Copy `.env.example` → `.env.local`, điền `KORA_GITHUB_SYNC_TOKEN`.
4. Đặt trong `config/factory-config.yaml`:
   ```yaml
   github:
     enabled: true
     repo: "isc-fkit/kb-mirror"   # owner/name — PHẢI private
     branch: main
     permission: read_write
   ```
5. Kiểm tra: `python3 tools/github-sync/sync_github.py --check`

## Lệnh

| Lệnh | Việc |
|---|---|
| `--check` | Kiểm tra token + truy cập repo (không ghi). |
| `--push [--dry-run]` | Đẩy KB → repo (idempotent: không đổi thì không commit). `--force` chép lại tất cả. |
| `--pull` | Kéo file `.md` từ repo → `<vault>/GitHub/`. |
| `--source vault\|docs\|both` · `--scope <glob>` · `--subdir <path>` · `--repo owner/name` · `--branch <b>` | Ghi đè cấu hình. |

## Bảo mật

- Token CHỈ ở `.env.local` (gitignore). KHÔNG in ra log.
- Token bơm vào git qua biến môi trường `GIT_CONFIG_*` (http.extraHeader) → **không** vào
  `.git/config`, **không** vào `argv`/`ps`. Mọi output git đều scrub token.
- Repo đích là **gương 1 chiều**: mỗi push reset cứng worktree theo `origin` rồi chép lại note.
  Đừng sửa tay trên repo đích (sẽ bị ghi đè ở lần push kế). Lịch sử git là vết kiểm toán.

## Trạng thái

- Map idempotent: `<vault>/_system/github/github-map-<owner>-<repo>.json`.
- Worktree làm việc: `tools/github-sync/work/<owner>-<repo>/` (gitignore).

Windows: thay `python3` bằng `py`.
