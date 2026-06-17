---
description: Update the Kora app/skills to the latest release, keeping your knowledge intact.
---

The user invoked `/kora-update` — an explicit command to update the program to the latest release
(knowledge preserved). Do NOT ask "update what".

- **Skills installed via the installer:** re-fetch via the installer's `update` action
  (manifest-driven, so new skills are auto-added) — `~/.claude/kora-framework/` + `~/.claude/commands/kora-*`.
- **Refresh skills in ALL 3 places** so Cowork (loads skills by path) gets the new ones — copy the latest
  `kora-*.md` into each: `~/.claude/commands/` (global) · the **current project's `.claude/commands/`**
  (if you're in a Kora project) · `~/Downloads/Kora-Skills/` (for manual Cowork upload).
- **A knowledge-project workspace:** read and execute `workflows/10-update.md` (compares
  `version.json` vs GitHub, confirms before overwriting CORE, never touches DATA).
