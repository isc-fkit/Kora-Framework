---
description: Initialize / set up the Kora knowledge base for this project. Run once to choose domain, rules, project name and vault.
---

The user invoked `/kora-init` — an explicit command to set up the project (equivalent to "@khởi tạo dự án"). Do NOT ask whether to run or just inform.

Read and execute `workflows/00-setup.md` (in the current project, or `~/.claude/kora-framework/workflows/00-setup.md` if installed via the installer), following `CLAUDE.md`:

- Run **step by step**; each step STOPS and asks the user (AskUserQuestion) before the next.
- Never auto-pick defaults for the user; never run straight to the end.
- **Init is lightweight:** Domain → Domain rule → Project name & language → Vault → (Design optional).
  Do NOT ask about source connection, tokens, or scheduling here — those live in the
  `kora-daily-report` / `kora-schedule` skills.
