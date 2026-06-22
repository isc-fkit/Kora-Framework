# tools/gitlab-sync — Đẩy KB → repo GitLab riêng tư (git push)

Anh em với `tools/github-sync` / `tools/confluence-sync`, target là một **git repo GitLab private**.
Gom tri thức cục bộ (`docs/` + vault) → **git push** lên repo. Đường **headless** (chạy được trong scheduler).

Chỉ thư viện chuẩn Python 3 + lệnh `git`.

## Cài nhanh

1. Tạo repo (project) **private** trên GitLab (vd `isc-fkit/kb-mirror`; hỗ trợ nhóm con `group/sub/name`).
2. Tạo **PAT** scope `api` (hoặc `read_repository` + `write_repository`) — Settings → Access Tokens.
3. Copy `.env.example` → `.env.local`, điền `KORA_GITLAB_SYNC_TOKEN`.
4. Đặt trong `config/factory-config.yaml`:
   ```yaml
   gitlab:
     enabled: true
     repo: "isc-fkit/kb-mirror"      # group/name (nhóm con: group/sub/name) — PHẢI private
     branch: main
     base_url: "https://gitlab.com"  # hoặc GitLab self-hosted: https://gitlab.company.com
     permission: read_write
   ```
5. Kiểm tra: `python3 tools/gitlab-sync/sync_gitlab.py --check`

## Lệnh

| Lệnh | Việc |
|---|---|
| `--check` | Kiểm tra token + truy cập repo (không ghi). |
| `--push [--dry-run]` | Đẩy KB → repo (idempotent: không đổi thì không commit). `--force` chép lại tất cả. |
| `--pull` | Kéo `.md` từ repo → `<vault>/GitLab/<group>-<name>/` thành **document chuẩn wiki**: thêm frontmatter metadata (`source: gitlab`, `gitlab_repo/branch/path/url/commit`, `title`, `imported_at`) + dòng **link nguồn** đầu bài, và dựng lại trang hub `_GitLab-Index.md` (idempotent; file xoá trên repo cũng biến mất). |
| `--source vault\|docs\|both` · `--scope <glob>` · `--subdir <path>` · `--repo group/name` · `--branch <b>` | Ghi đè cấu hình. |

## Bảo mật

- Token CHỈ ở `.env.local` (gitignore). KHÔNG in ra log.
- Token bơm vào git qua `GIT_CONFIG_*` (http.extraHeader, `Authorization: Basic base64("oauth2:"+token)`) →
  **không** vào `.git/config`, **không** vào `argv`/`ps`. Mọi output git đều scrub token.
- Repo đích là **gương 1 chiều**: mỗi push reset cứng worktree theo `origin` rồi chép lại note.
  Đừng sửa tay trên repo đích (sẽ bị ghi đè ở lần push kế). Lịch sử git là vết kiểm toán.

## Trạng thái

- Map idempotent: `<vault>/_system/gitlab/gitlab-map-<group>-<name>.json`.
- Worktree làm việc: `tools/gitlab-sync/work/<group>-<name>/` (gitignore).

Windows: thay `python3` bằng `py`.
