---
description: Import all Jira issues into the knowledge vault — scrapes every field, including comments.
---

The user invoked `/kora-import-jira` — an explicit command to import all Jira issues.

Read and execute `workflows/01-import-jira.md` following `CLAUDE.md`:

- **Step 0:** let the user choose the connection method (MCP or API) and source/domain
  (internal Server or Atlassian Cloud) before scanning.
- **Scrape ALL fields (`fields=*all`) INCLUDING comments** — every issue's comments must be saved.
- Token security: keep tokens only in an env var / `.env.local`, never print to chat/log, remove after use.
