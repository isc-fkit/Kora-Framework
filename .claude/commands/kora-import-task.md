---
description: Import a single Jira task or epic by key. Example: /kora-import-task PROJ-102
argument-hint: <JIRA-KEY> (e.g. PROJ-102)
---

The user invoked `/kora-import-task $ARGUMENTS` — an explicit command to import one Jira issue.

Issue key: **$ARGUMENTS**

- If the key above is empty → ask the user for it (AskUserQuestion: a few suggestions + an "Other"
  field to type the real key); do NOT invent a key.
- Read and execute `workflows/01b-import-jira-single.md` for that key, scraping all fields
  **including comments**. Keep token security (env var / `.env.local`, removed after use).
