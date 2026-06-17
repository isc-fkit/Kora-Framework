---
description: Connect a knowledge source. Choose MCP or API, then pick a source that method supports (Jira Server/Cloud via API; Atlassian, SharePoint, GitHub, Confluence… via MCP with OAuth).
---

The user invoked `/kora-connect` — set up a connection to a knowledge source.

Drive step by step with **AskUserQuestion** (each a card; stop and wait):

1. **Phương thức** → **[MCP]** / **[API]**.
2. **Nguồn** — chỉ hiện cái mà phương thức đã chọn HỖ TRỢ:
   - **API** → **[Jira Server / self-host]** / **[Jira Cloud]**.
   - **MCP** → **[Atlassian / Jira]** / **[SharePoint]** / **[GitHub]** / **[Confluence]** … (chỉ những
     Connector đang có trong Claude App/Cowork).
3. **Kết nối:**
   - **MCP** → gọi **OAuth**: hướng dẫn user bật/authorize Connector trong Claude App/Cowork
     (Settings → Connectors), rồi **verify** bằng cách gọi thử 1 MCP tool của nguồn đó.
   - **API** → hỏi **base URL + token**; **ghi `export KORA_<SRC>_TOKEN` / `_BASE_URL` vào `~/.zshrc`**
     (nhắc `source`); **KHÔNG in token ra chat**; nếu đã có env var thì dùng lại.
4. **Ghi nhận** kết nối vào `config/factory-config.yaml > connections:` (method, source, base_url,
   token_env hoặc mcp) để `/kora-scan` liệt kê được.

Báo rõ nguồn nào đã kết nối. Bảo mật: token chỉ ở env var, không vào chat/source.
