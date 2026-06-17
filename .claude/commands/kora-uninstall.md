---
description: Uninstall the Kora skills from ~/.claude and remove KORA_* environment variables.
---

The user invoked `/kora-uninstall` — an explicit command to remove the installed Kora skills.

Ask for confirmation first (AskUserQuestion: Confirm / Cancel), then:

- Remove `~/.claude/commands/kora-*.md` and the `~/.claude/kora-framework/` support directory.
- Print the `export KORA_*` lines found in `~/.zshrc` / `~/.bashrc` so the user can delete them
  (do NOT silently edit the shell rc without showing what is removed).
- Confirm what was removed.
- Note: this removes the **skills only** — your knowledge project (docs/vault) is untouched.
  This is the counterpart of the installer (`install.command` / `install.bat`).
