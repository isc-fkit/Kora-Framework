---
description: Export knowledge to DOCX/PDF for human readers. Triggers (vi): «xuất tài liệu», «export docx/pdf», «xuất file Word cho sếp» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-export-docs` — an explicit command to export documents.

Read and execute `workflows/06-export-docs.md` following `CLAUDE.md`:

- Ask which content + format (DOCX / PDF) via AskUserQuestion.
- Export into `docs/03-features/F-xxx/export/` (the reader-facing copy).
- Keep the Approval Gate.
