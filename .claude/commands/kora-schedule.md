---
description: Schedule automatic sync / daily reports, or cancel an existing schedule. Choose one or more projects. Also where source-connection setup (MCP / API) lives.
---

The user invoked `/kora-schedule`.

**First, AskUserQuestion:** **[Create / update a schedule]** / **[Cancel a schedule]** / **[List schedules]**.

- **Cancel a schedule** → list the existing scheduled tasks as a **multi-select checklist**
  (read from the scheduler / config) → user ticks which to cancel → ✋ confirm → remove them.
- **List schedules** → show the current schedules (project, type, time, next run).
- **Create / update a schedule:**
  1. **Projects** — choose **one or more** (AskUserQuestion `multiSelect: true`). If any project was
     scanned before, first offer **[Pick from already-scanned (checklist)]** / **[Add new]**.
  2. **Type** — **(A)** auto-sync sources, or **(B)** daily report at a chosen time.
  3. **Connection** — this skill OWNS source-connection setup: choose **MCP / API / All**; for API,
     write the token as an env var into `~/.zshrc` / `~/.bashrc` (never to chat).
  4. ✋ **Confirm before creating / changing any scheduled task.**

Follow `workflows/08-schedule-sync.md`.
