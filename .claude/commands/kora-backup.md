---
description: Back up / export all your knowledge to a zip to move between machines.
---

The user invoked `/kora-backup` — an explicit command to back up/export knowledge.

Read and execute `workflows/11-export-import.md` **section A (export)** following `CLAUDE.md`:

- Package DATA (`docs/`, vault `*_Brain/`, `inbox/`, `.kb/*` except CORE files, `config/*`, `.env.local`)
  into `kora-kb-*.zip`.
- ⚠️ Consider token security in `.env.local` when moving machines.
- Keep the Approval Gate.
