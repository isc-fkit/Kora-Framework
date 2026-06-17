---
description: Generate a progress report. Asks which project, filters by project and members, pulls data for the chosen time range from the sources, then builds the dashboard.
---

The user invoked `/kora-daily-report` — an explicit command to build a progress report.

Read and execute `workflows/14-progress-report.md` following `CLAUDE.md`:

- **Ask which project** to report on; offer **filters by project and by member** (assignee / team).
- **Ask the desired time range**, then **pull data for that period** from the configured sources
  (Jira via API/MCP, SharePoint via MCP).
- If no connection is configured yet, ask **MCP or API right here** (not at init).
- Produce the dashboard (time-tracking / active sprint / assignee) as inline Cowork UI + an HTML file.
