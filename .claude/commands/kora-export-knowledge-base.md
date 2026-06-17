---
description: Export the entire knowledge base to a zip — for backup, moving machines, or handover.
---

The user invoked `/kora-export-knowledge-base` — export all knowledge to a zip.

Read and execute `workflows/11-export-import.md` **section A (export)** following `CLAUDE.md`:

- Package DATA (`docs/`, vault `*_Brain/`, `inbox/`, `.kb/*` except CORE files, `config/*`, `.env.local`)
  into `kora-kb-*.zip`.
- ⚠️ Consider token security in `.env.local` when moving / handing over.
- Keep the Approval Gate.
