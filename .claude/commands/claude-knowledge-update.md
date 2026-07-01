---
description: Update the Kora app/skills/framework to the latest release by RUNNING the bash update script on the CLI, keeping your knowledge intact. Do not ask "update what" or "which framework". Triggers (vi): «cập nhật phiên bản», «cập nhật phiên bản mới nhất», «cập nhật ứng dụng», «cập nhật framework», «update framework», «lên bản mới nhất», «có bản mới không», «nâng cấp Kora / hệ thống» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork. "framework"/"Kora"/"hệ thống"/"app" đều là bí danh của CHÍNH ứng dụng này — KHÔNG hỏi lại "framework nào? ở đâu?".
---

The user invoked `/claude-knowledge-update` — cập nhật chương trình lên bản mới nhất (giữ nguyên tri thức).
**Do NOT ask "update what".** Cập nhật phải chạy bằng **bash script trên CLI** — KHÔNG reimplement bằng tay.

> ⚡ **CÁCH CHẠY LỆNH (Cowork sandbox CHẶN MẠNG):** MỌI lệnh của skill này (so version, curl, chạy installer/update
> script) — **có MCP `run_command` (local-terminal, Claude Desktop) → chạy QUA `run_command`** (thẳng trên máy,
> ngoài sandbox), **KHÔNG bàn giao Terminal, KHÔNG dừng nửa chừng**. Không có `run_command` → mới BÀN GIAO đúng
> 1 lệnh cho user dán vào Terminal. ⚠️ Bash tool trong sandbox curl fail ≠ "hết cách" — đó là tín hiệu phải đi
> `run_command`/bàn giao, ĐỪNG kết luận "không cập nhật được".

0. **Xác định bản cài + VERSION hiện tại (đừng đoán sai nhánh):**
   - Project có `scripts/update.command` + `version.json` → **bản project folder** (nhánh 1). `LOCAL` = `version.json` ở gốc project.
   - Project KHÔNG có `scripts/`/`version.json` (chỉ CLAUDE.md + `Skill/` + DATA — bản cài từ installer/git, project đã
     đăng ký) → **bản cài skill-managed** (nhánh 2). `LOCAL` = **`~/.claude/kora-framework/version.json`** (đọc qua
     `run_command: cat ~/.claude/kora-framework/version.json`). **TUYỆT ĐỐI KHÔNG** kết luận "không rõ bản đang cài /
     chưa cài" chỉ vì project thiếu `version.json`.
   - So với bản mới nhất + confirm theo `workflows/10-update.md` Bước 1–2 (không có `workflows/` trong project → đọc
     `~/.claude/kora-framework/workflows/10-update.md`).
1. **Bản project folder** → chạy **bash script** (qua `run_command` nếu Cowork):
   - macOS/Linux: `bash scripts/update.command`
   - Windows: `scripts\update.bat`
   Script kéo bản CORE mới (git pull nếu có `.git`, hoặc tải zip + rsync chỉ CORE), **KHÔNG đụng DATA**; **tự fallback
   PROXY** khi mạng công ty chặn tải trực tiếp (`KORA_UPDATE_PROXY` → `https_proxy` → proxy FPT) — curl trực tiếp fail
   thì CỨ chạy script, script tự lo. Từ v2.5.3 script còn **tự refresh skill `/claude-knowledge-*` vào `~/.claude/commands/`**
   + **reconcile MỌI project đã đăng ký/phát hiện** (Skill/ + CLAUDE.md + merge config). ⚠️ Bản CŨ (≤2.5.2) chưa có bước
   này → **chạy LẠI installer 1 lần** (nhánh 2).
2. **Bản cài skill-managed** → **chạy lại installer = cập nhật** (qua `run_command` nếu Cowork):
   - macOS/Linux: `bash <(curl -fsSL https://raw.githubusercontent.com/isc-fkit/Kora-Framework/release/install.command)`
   - Windows: `curl -fsSL https://raw.githubusercontent.com/isc-fkit/Kora-Framework/release/install.bat -o "%TEMP%\kora-install.bat" && "%TEMP%\kora-install.bat"`
   Installer tự fallback proxy như trên; manifest-driven → skill mới tự thêm; refresh **CẢ 3 nơi**: `~/.claude/commands/`
   (CLI) · CORE `~/.claude/kora-framework/` · **reconcile MỌI project Kora** (Skill/ + CLAUDE.md + merge config — in ra
   "Đã refresh N project"). Dọn folder `Kora-Skills` cũ + zip nếu còn sót.
3. **VERIFY — bắt buộc, đừng tin script chạy xong là xong:** đọc lại `version.json` đúng nhánh (nhánh 2 =
   `~/.claude/kora-framework/version.json`) → báo **cũ → mới** + số project đã reconcile. Version KHÔNG đổi → coi là
   FAIL, đọc output tìm nguyên nhân (mạng/proxy) — KHÔNG báo "đã cập nhật".
4. **Nhắc re-upload skill vào Cowork (bước hay bị quên → "update rồi mà hành vi vẫn cũ"):** update chỉ refresh skill
   trên ĐĨA (`~/.claude/commands/` + `<project>/Skill/`); **skill đã UPLOAD vào mục Skills của app Cowork/Claude KHÔNG
   tự cập nhật**. Đọc CHANGELOG bản mới → liệt kê các skill ĐỔI → nhắc user upload lại đúng các file đó từ
   `<project>/Skill/` vào mục Skills. (`CLAUDE.md` của project ĐÃ được thay tự động → luồng mới trong CLAUDE.md chạy
   ngay cả khi chưa re-upload skill.)
5. Nếu kb-indexer đổi → nhắc chạy `python3 tools/kb-indexer/build_index.py --root .`.
