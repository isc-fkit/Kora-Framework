---
description: Scan & import a single Jira task or epic by key. Example: /claude-knowledge-scan-jira-task PROJ-102
argument-hint: <JIRA-KEY> (e.g. PROJ-102)
---

The user invoked `/claude-knowledge-scan-jira-task $ARGUMENTS` — scan one Jira hạng mục công việc by key.

Hạng mục công việc key: **$ARGUMENTS**

- If the key above is empty → ask the user for it (AskUserQuestion: a few suggestions + an "Other"
  field); do NOT invent a key.
- If connection not configured yet → ask **[API]** / **[MCP]** first.
- Read and execute `workflows/01b-import-jira-single.md` for that key, scraping all fields
  **including comments**. Keep token security (env var / `.env.local`, removed after use).
