---
description: Connect a knowledge source OR view already-connected sources. Entry asks [Connect new] vs [View connected]; new → choose MCP or API → pick a source that method supports (Jira/GitHub/GitLab via API OAuth 2.0; Atlassian, Gmail, Microsoft 365 via MCP), marking sources already connected. API and MCP count separately.
---

The user invoked `/kora-connect` — set up a connection to a knowledge source, recorded in the
`connections:` registry of `config/factory-config.yaml`. Drive **step by step with AskUserQuestion**
(each a card; STOP and wait). **Bảo mật tuyệt đối:** token/secret CHỈ vào env var (`~/.zshrc`/`~/.bashrc`)
hoặc file `.env` — **KHÔNG bao giờ in token ra chat / vào `connections:`**. Registry chỉ TRỎ tới nơi
secret nằm (tên env var / đường dẫn `.env` / tên MCP connector).

### Bước 0 — Chọn nhánh (AskUserQuestion) → **[Kết nối mới]** / **[Xem nguồn đã kết nối]**
Chạy trước `python3 tools/connections/check_connection.py --list` (Windows: `py`) để biết hiện trạng, rồi hỏi:
- **[Xem nguồn đã kết nối]** → liệt kê **TẤT CẢ** entry trong `connections:` kèm trạng thái
  (`display_name` + method + ✓ connected · checked …). **API vs MCP hiển thị TÁCH RIÊNG** (mỗi method 1
  dòng — id `<source_type>__<method>` khác nhau). Mỗi dòng có **[⟳ Kiểm tra lại]** (`--check <id>`).
  Registry rỗng → báo "chưa kết nối nguồn nào". Xong → đề xuất bước kế (không ghi gì).
- **[Kết nối mới]** → sang Bước 1.

### Bước 1 — Phương thức  → **[MCP]** / **[API]** / **[← Huỷ]**
ESC hoặc [← Huỷ] = dừng, **KHÔNG ghi gì** vào `connections:`.

### Bước 2 — Nguồn (chỉ hiện cái phương thức đã chọn HỖ TRỢ) + **[← Quay lại]**
- **MCP** → **[Atlassian Rovo (Jira + Confluence)]** / **[Gmail]** / **[Microsoft 365 (SharePoint + Outlook)]**
  — chỉ những Connector đang có trong Claude App/Cowork (Settings → Connectors).
- **API** (ưu tiên **OAuth 2.0**, PAT là fallback) → **[Jira Server / self-host]** / **[Jira Cloud]** /
  **[GitHub]** / **[GitLab]** / **[SharePoint (Microsoft Graph — ĐẨY/ghi KB)]**.
  > SharePoint API khác MCP Microsoft 365 (chỉ đọc): API Graph để **GHI** KB. Auth: app-only
  > client-credentials (cần admin consent `Sites.ReadWrite.All`, chạy nền) **hoặc** device-flow
  > (`sync_sharepoint.py --login`, tương tác). source_type = `sharepoint`, method = `api`.

> 🔖 **Đánh dấu đã kết nối:** đối chiếu với `--list` — nguồn nào ĐÃ có entry `<source_type>__<method>`
> (đúng phương thức đang chọn) thì gắn badge **"✓ đã kết nối"** trên thẻ đó (chọn lại = kiểm tra/cập nhật,
> replace-in-place; KHÔNG tạo entry trùng).

> ⚠️ **API vs MCP tính RIÊNG:** cùng một nguồn (vd Jira Cloud) qua API và qua MCP = **2 entry riêng**
> (id khác nhau) → liệt kê/scan tách biệt. ID = `<source_type>__<method>[__<slug-host>]`
> (vd `jira_cloud__api`, `jira_cloud__mcp`, `jira_server__api__companyvn`).

### Bước 3 — Kết nối
- **MCP** → hướng dẫn user bật/authorize Connector trong **Claude App → Settings → Connectors** (OAuth do
  app quản lý). **Verify** bằng cách gọi thử 1 MCP tool của nguồn (vd `atlassian` search). OK mới sang Bước 4.
- **API** → ưu tiên **OAuth 2.0 Device Flow** (browser-OAuth chạy được từ CLI):
  1. Bắt đầu device flow với provider (GitHub `https://github.com/login/device/code`; GitLab/Jira tương đương).
  2. Hiện **verification URL + user code** cho user (KHÔNG phải secret) → user duyệt trên trình duyệt → poll token.
  3. Ghi **access token** vào **biến môi trường SHELL** — MẶC ĐỊNH, KHÔNG tạo `.env` trong project (rule §1.6):
     - `export KORA_<SRC>_TOKEN=...` (+ `_EMAIL` / `_BASE_URL` nếu cần) vào `~/.zshrc` (bash → `~/.bashrc`;
       chọn rc theo `$SHELL`) → nhắc user `source`. Token KHÔNG ra chat. Các tool đọc qua `os.getenv`.
     - vd Jira: `export JIRA_BASE_URL=... JIRA_EMAIL=... JIRA_PAT=...`; GitHub: `export KORA_GITHUB_TOKEN=...`.
  3b. **CHỈ tạo `.env.local` trong project ở 2 NGOẠI LỆ:**
     - **Archive** (`/kora-archive`): gói bàn giao ship đúng 1 `.env.local` read-only (key đọc KB chung).
     - **Lịch sync nền** (`/kora-schedule`): mỗi NGUỒN user chọn auto-sync mới tạo `.env.local` RIÊNG cho
       nguồn đó (vd `tools/jira-to-obsidian/.env.<nguồn>`, `tools/github-sync/.env.local`) vì cron/launchd
       không đọc được shell tương tác. Ngoài 2 ca này → luôn dùng shell env.
  4. **Fallback PAT:** nếu user từ chối OAuth, hoặc nguồn sẽ dùng cho **lịch chạy nền** (cron không mở được
     trình duyệt) → yêu cầu **PAT/long-lived token** thay vì OAuth (xem cảnh báo headless ở `/kora-schedule`).

### Bước 4 — Verify rồi mới GHI (KHÔNG ghi nửa chừng)
- **API:** chạy `python3 tools/connections/check_connection.py --check <id>` → đọc JSON kết quả.
- **MCP:** tự gọi 1 MCP tool để verify.
- **Chỉ khi verify THÀNH CÔNG** → ghi 1 entry đầy đủ vào `connections:` của `config/factory-config.yaml`
  (giữ id-uniqueness — trùng id thì replace-in-place), gồm: `id, method, source_type, display_name,
  auth_kind (oauth2|token|mcp_oauth), base_url, creds {kind: mcp_connector|env|dotenv, …pointer…},
  verify {tool|probe}, status: connected, last_checked: <ISO local>, last_error: ""`.
  Verify thất bại → báo lỗi rõ (token sai/hết hạn, connector chưa bật), **KHÔNG ghi entry**.

Kết thúc: báo nguồn đã kết nối + đề xuất bước kế (AskUserQuestion): **[A] /kora-scan nạp tri thức ·
[B] Kết nối nguồn khác · [C] Đặt lịch đồng bộ · [D] Dừng**.
