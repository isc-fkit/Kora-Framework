---
description: Generate a progress report. Choose one or more projects (multi-select), filter by members, pull data for a chosen time range from the sources, then build the dashboard.
---

The user invoked `/kora-daily-report` — build a progress report.

**Project selection (AskUserQuestion):**
1. If any project was scanned before → first offer **[Pick from already-scanned projects]** /
   **[Add a new project]**.
   - **Pick from already-scanned** → show the already-imported projects as a **multi-select
     checklist** (read the list from the vault / `config/factory-config.yaml`); the user ticks
     one or more.
   - **Add a new project** → ask the new project key/name; if not yet imported, scan it first
     (`/kora-scan`).
2. Always allow choosing **multiple projects** (AskUserQuestion with `multiSelect: true`).

**Then:**
- Offer **filters by project and by member** (assignee / team) — multi-select.
- Ask the **time range**, then pull data for that period from the configured sources
  (Jira via API/MCP, SharePoint via MCP).
- If no connection configured yet → ask **MCP / API / All** here (not at init).
- Build the dashboard (time-tracking / active sprint / assignee) per `workflows/14-progress-report.md`
  — inline Cowork UI + an HTML file.
