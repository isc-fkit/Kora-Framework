---
description: Schedule automatic data sync and daily reports. Also where source-connection setup (MCP or API) lives.
---

The user invoked `/kora-schedule` — an explicit command to set up scheduling.

Read and execute `workflows/08-schedule-sync.md` following `CLAUDE.md`:

- This skill **owns source-connection setup** (choose MCP or API; for API, write the token as an
  env var into `~/.zshrc` / `~/.bashrc`) — moved out of init.
- Ask which schedule via AskUserQuestion: **(A)** auto-sync sources, or **(B)** daily report at a chosen time.
- ✋ Confirm before creating any scheduled task.
