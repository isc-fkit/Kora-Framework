---
description: Scan & import knowledge from a source. Choose connection (API / MCP / All), then the specific source (Jira Cloud/Server, SharePoint, …). Scrapes every field, including comments.
---

The user invoked `/kora-scan` — an explicit command to scan & import knowledge from a source.

Drive the choices step by step with **AskUserQuestion** (each step a card; stop and wait):

1. **Connection method** → **[API]** / **[MCP]** / **[All]**.
2. **Source** — options depend on step 1 (only show what's relevant):
   - **MCP** → **[Jira Cloud]** / **[SharePoint]** / **[Confluence]** / **[All]** — only those whose
     Connector is enabled in Claude App/Cowork (guide the user to enable it if missing).
   - **API** → **[Jira Server / DC]** / **[All]** — token-based.
   - **All** → scan every configured source (skip step 2).
3. Then pull into the vault:
   - **Jira (API or MCP)** → read and execute `workflows/01-import-jira.md`; scrape **ALL fields,
     INCLUDING comments**.
   - **SharePoint (MCP)** → use `sharepoint_search` / `sharepoint_folder_search` to pull documents
     into the vault (scaffolding).
   - **Confluence (MCP)** → use the Confluence MCP search/fetch tools.

Rules:
- **MCP path** requires the Connector enabled in Claude App/Cowork — verify by calling one MCP tool first.
- **API path** → ask the user for the token, then **write `export KORA_<SRC>_TOKEN="..."` (+ base URL,
  e.g. `KORA_JIRA_BASE_URL`) into `~/.zshrc` / `~/.bashrc`** (remind to `source ~/.zshrc` or open a new
  terminal); **never print the token to chat**; reuse it if the env var is already set.
- Keep the Approval Gate before writing into `docs/` / vault.
