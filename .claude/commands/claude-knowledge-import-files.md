---
description: Import documents (PDF/DOCX/images/Obsidian zip) into the knowledge base.
---

The user invoked `/claude-knowledge-import-files` — an explicit command to import documents as knowledge.

- If no file is attached → ask the user to drag files into chat (PDF / DOCX / PNG / JPG / Obsidian zip),
  then wait for the files.
- Once files are present → read and execute `workflows/02-import-files.md` following `CLAUDE.md`.
- Keep the Approval Gate: only write into `docs/` after the user approves.
