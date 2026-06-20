---
description: Update the Kora app/skills to the latest release by RUNNING the bash update script on the CLI, keeping your knowledge intact. Do not ask "update what".
---

The user invoked `/kora-update` — cập nhật chương trình lên bản mới nhất (giữ nguyên tri thức).
**Do NOT ask "update what".** Cập nhật phải chạy bằng **bash script trên CLI** — KHÔNG reimplement bằng tay.

1. **Bản project folder** (có `scripts/update.command` + `version.json` trong thư mục): đọc
   `workflows/10-update.md` để so `version.json` local vs GitHub + confirm, rồi chạy **bash script** qua Bash tool:
   - macOS/Linux: `bash scripts/update.command`
   - Windows: `scripts\update.bat`
   Script kéo bản CORE mới (git pull nếu có `.git`, hoặc tải zip + rsync chỉ CORE), **KHÔNG đụng DATA**.
2. **Bản cài skill managed** (skill trong `~/.claude`, không có folder project): **chạy lại installer = cập nhật**:
   - macOS/Linux: `bash <(curl -fsSL https://raw.githubusercontent.com/isc-fkit/Kora-Framework/release/install.command)`
   - Windows: `curl -fsSL https://raw.githubusercontent.com/isc-fkit/Kora-Framework/release/install.bat -o "%TEMP%\kora-install.bat" && "%TEMP%\kora-install.bat"`
   Manifest-driven → skill mới tự thêm; refresh CẢ HAI nơi: `~/.claude/commands/` (CLI) **và**
   `<Downloads>/Knowledge-Base/Skill/` (upload tay vào Cowork). Dọn folder `Kora-Skills` cũ + zip nếu còn sót.
3. Báo `version.json` cũ → mới. Nếu kb-indexer đổi → nhắc chạy `python3 tools/kb-indexer/build_index.py --root .`.
