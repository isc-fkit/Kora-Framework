---
description: Initialize / set up the Kora knowledge base for this project. Run once to choose domain(s) — one, several, or all — rules, project name and vault. Triggers (vi): «khởi tạo dự án», «cài đặt hệ thống», «setup factory», «đổi domain», «init KB» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-init` — an explicit command to set up the project (equivalent to "@khởi tạo dự án"). Do NOT ask whether to run or just inform.

Read and execute `workflows/00-setup.md` (in the current project, or `~/.claude/kora-framework/workflows/00-setup.md` if installed via the installer), following `CLAUDE.md`:

- **If run in an EMPTY folder** (skills installed via the installer, no Kora project yet) →
  first **scaffold a LEAN project here** (00-setup Bước 0): create `docs/01-08` + `inbox/` + `.kb/`
  + the vault, copy `config/factory-config.example.yaml` → `config/factory-config.yaml` from
  `~/.claude/kora-framework/`, and write a tiny `CLAUDE.md` = `@~/.claude/kora-framework/CLAUDE.md`.
  CORE (workflows/tools/templates/presets) stays SHARED in `~/.claude/kora-framework/`. Then continue.
- **AUTO-pull domain phổ biến + rule (Bước 0b, IM LẶNG — không hỏi):** mỗi lần init, tự làm mới
  `config/domain-presets/` từ CORE `~/.claude/kora-framework/config/domain-presets/` (và thử kéo bản
  mới nhất từ repo framework; offline → dùng bản bundle). `config/domain-rules.md` chỉ làm mới nếu
  còn là template chưa chỉnh (user đã sửa thì giữ nguyên). Rồi mới tiếp các bước hỏi.
- Run **step by step**; each step STOPS and asks the user (AskUserQuestion) before the next.
- Never auto-pick defaults for the user; never run straight to the end.
- **Init is lightweight:** Domain(s) — chọn MỘT, NHIỀU hoặc TẤT CẢ (rule gộp) → Domain rule → Project name & language → Vault.
  Do NOT ask about source connection, tokens, or scheduling here — those live in the
  `claude-knowledge-connect` / `claude-knowledge-schedule` skills.
