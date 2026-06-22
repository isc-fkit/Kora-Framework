---
description: Uninstall the Kora skills by RUNNING the uninstall.command bash script on the CLI (not reimplemented by hand). Knowledge project (docs/vault) is untouched.
---

The user invoked `/claude-knowledge-uninstall`. Gỡ phải chạy bằng **bash script trên CLI** — KHÔNG xoá tay từng file.

1. **Confirm first** (AskUserQuestion: **[Gỡ skill] / [Hủy]**). Hủy → dừng, không làm gì.
2. On confirm, run the uninstall **bash script** via the Bash tool (đúng 1 lệnh, chạy trên CLI):
   - **Có `uninstall.command` ở project root** (bản project folder) → `bash ./uninstall.command`.
   - **Bản cài skill managed** (không có folder project) → one-liner đã phát hành:
     `bash <(curl -fsSL https://raw.githubusercontent.com/isc-fkit/Kora-Framework/release/uninstall.command)`
   - **Windows:** `curl -fsSL https://raw.githubusercontent.com/isc-fkit/Kora-Framework/release/uninstall.bat -o "%TEMP%\claude-knowledge-uninstall.bat" && "%TEMP%\claude-knowledge-uninstall.bat"`
   Script tự xoá `~/.claude/commands/claude-knowledge-*.md` + `~/.claude/kora-framework/` + folder `Skill/`, rồi
   **IN ra** các dòng `export KORA_*` trong `~/.zshrc`/`~/.bashrc` để user tự xoá (KHÔNG tự sửa shell rc).
   (Prompt `yes` của script: chuyển xác nhận của user qua; khi stdin không phải TTY, script tự tiếp tục.)
3. Thuật lại đúng những gì script đã xoá. **Chỉ gỡ skill — tri thức (docs/vault) KHÔNG bị đụng.**
   Đây là cặp đối ứng của installer (`install.command` / `install.bat`).
