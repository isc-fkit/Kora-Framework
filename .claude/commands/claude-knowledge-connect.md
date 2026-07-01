---
description: Connect a knowledge source OR view already-connected sources. Entry asks [Connect new] vs [View connected]; new → choose MCP or API → pick a source that method supports (Jira/GitHub/GitLab/SharePoint via API OAuth 2.0; Gmail SMTP via App Password for auto-send; Atlassian, Gmail draft, Microsoft 365 via MCP), marking sources already connected. API and MCP count separately. Triggers (vi): «kết nối nguồn», «thêm Jira/GitHub/Gmail», «connect», «xem nguồn đã kết nối» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-connect` — set up a connection to a knowledge source, recorded in the
`connections:` registry of `config/factory-config.yaml`. Drive **step by step with AskUserQuestion**
(each a card; STOP and wait). **Bảo mật tuyệt đối:** token/secret CHỈ vào env var (`~/.zshrc`/`~/.bashrc`)
hoặc file `.env` — **KHÔNG bao giờ in token ra chat / vào `connections:`**. Registry chỉ TRỎ tới nơi
secret nằm (tên env var / đường dẫn `.env` / tên MCP connector).

### Bước 0 — Chọn nhánh (AskUserQuestion) → **[Kết nối mới]** / **[Xem nguồn đã kết nối]**
Chạy trước để biết hiện trạng — **đường dẫn tool TỰ RESOLVE** (bản cài để CORE ở `~/.claude/kora-framework/`),
**KHÔNG tự viết Python parse YAML** (không có `pyyaml` — `check_connection.py` đã có parser riêng, chỉ stdlib):
```
T=tools; [ -e "$T/connections/check_connection.py" ] || T="$HOME/.claude/kora-framework/tools"; python3 "$T/connections/check_connection.py" --list --config "$PWD/config/factory-config.yaml"
```
(Windows: `py` thay `python3`.) Rồi hỏi:
- **[Xem nguồn đã kết nối]** → xuất **BẢNG CHI TIẾT, ĐẦY ĐỦ** (KHÔNG chung chung), mỗi dòng đủ cột:
  **Nguồn · Method (MCP/API/SMTP) · Tài khoản · Trạng thái (LIVE-probe vs theo-config) · Phạm vi (projects/site) · Trong sổ `connections:`?**.
  Gồm CẢ (i) entry trong sổ (`--list`) LẪN (ii) **nguồn LIVE NGOÀI SỔ** — connector bật ở app/env mà CHƯA đăng ký
  (vd Jira Cloud qua Atlassian Rovo MCP, Jira Server qua token env): `mcp-registry list_connectors` + env (`JIRA_BASE_URL`)
  → **diff** với id trong sổ → cái chưa có = "❌ chưa trong sổ". **API vs MCP TÁCH RIÊNG.** Registry rỗng vẫn phải dò (ii).
  **KÊNH GỬI MAIL** (`gmail_smtp`/`gmail_api`) hiển thị mục RIÊNG "Kênh gửi mail" — KHÔNG lẫn vào danh sách nguồn tri thức.
  > ⛔ **"KIỂM TRA KẾT NỐI" = VERIFY HẾT MỌI NGUỒN, KHÔNG ĐƯỢC CHỈ PROBE JIRA.** Khi user nói "kiểm tra
  >   kết nối" / "kiểm tra các nguồn" / "check connections" mà **KHÔNG nêu đích danh 1 nguồn** → **MẶC ĐỊNH
  >   chạy [⟳⟳ Kiểm tra lại TẤT CẢ]**, lặp MỌI entry trong `--list` (Jira, Gmail, M365/SharePoint/Outlook,
  >   GitHub…). Chỉ kiểm 1 nguồn khi user CHỈ RÕ tên nguồn đó.
  Hai hành động:
  - **[⟳ Kiểm tra lại 1 nguồn]** → `check_connection.py --check <id> --config "$PWD/config/factory-config.yaml"`.
  - **[⟳⟳ Kiểm tra lại TẤT CẢ]** — BẮT BUỘC verify HẾT, KHÔNG dừng ở Jira:
    1. `check_connection.py --check-all --json --config "$PWD/config/factory-config.yaml"` → **mảng** kết quả MỌI nguồn.
    2. Nguồn `status: connected|error` (api/sharepoint/excel) → tool đã verify xong → lấy nguyên kết quả.
    3. Nguồn `status: needs_model_probe` → **TỰ chạy đúng probe cho TỪNG cái** (đọc `verify_tool`/`verify_cmd`
       trong JSON — ĐỪNG bỏ sót nguồn nào): MCP Jira→`searchJiraIssuesUsingJql`/`getVisibleJiraProjects` ·
       Confluence→`searchConfluenceUsingCql` · SharePoint→`sharepoint_folder_search` · Outlook→`outlook_email_search` ·
       Gmail draft→`list_drafts`/`list_labels` · `gmail_smtp`→`send_report.py --check` ·
       `gmail_api`→`send_report.py --check --transport https`.
    4. Tổng hợp **BẢNG CHI TIẾT** (đúng các cột trên) — PROBE LIVE điền trạng thái thật (vd MCP Jira `getVisibleJiraProjects`
       còn liệt kê project vào cột Phạm vi); không probe được → 🟡 "theo-config, chưa probe".
    5. **GHI kết quả vào sổ QUA GATE:** sau khi user ĐỒNG Ý → `check_connection.py --record-result <id>
       --status <connected|error|needs_model_probe> [--last-error "…"] --confirm`
       (cổng chống ghi lén: thiếu `--status` hoặc `--confirm` → tool TỪ CHỐI).
    6. **Nguồn LIVE NGOÀI SỔ → MỜI ĐĂNG KÝ:** AskUserQuestion "Ghi nguồn này vào sổ?" từng cái (Jira Cloud `jira_cloud__mcp`;
       Jira Server `jira_server__api__<host>` — nhắc đặt token ở `tools/jira-to-obsidian/.env.local` nếu env trống) → route Bước 2/3/4.
  Xong → đề xuất bước kế (chỉ XEM → KHÔNG ghi; có probe + user đồng ý → mới `--record-result`).
- **[Kết nối mới]** → sang Bước 1.

### Bước 1 — Phương thức  → **[MCP]** / **[API]** / **[← Huỷ]**
ESC hoặc [← Huỷ] = dừng, **KHÔNG ghi gì** vào `connections:`.

### Bước 2 — Nguồn (chỉ hiện cái phương thức đã chọn HỖ TRỢ). Quay lại = ESC.
> ⚠️ **AskUserQuestion tối đa 4 option/thẻ.** Khi danh sách >4 nguồn → **PHÂN TRANG**: 3 mục +
> **[Khác — xem thêm]** → lượt kế liệt kê phần còn lại. **KHÔNG** nhồi >4 option vào 1 thẻ (sẽ lỗi
> "Invalid tool parameters").

- **MCP** (3 nguồn → 1 thẻ) → **[Atlassian Rovo (Jira + Confluence)]** / **[Gmail — tạo NHÁP/draft]** /
  **[Microsoft 365 (SharePoint + Outlook)]** — Connector đang có trong Claude App/Cowork (Settings →
  Connectors) **hoặc** gõ **`/mcp`** (Claude Code/Desktop) để kết nối server trước.
  > ✉️ **KẾT NỐI GMAIL → LUÔN HỎI THẲNG "SMTP hay MCP", ƯU TIÊN SMTP:** khi user muốn nối Gmail (nói "kết nối gmail"/
  >   "gửi mail"), **AskUserQuestion**: **[Gmail SMTP — TỰ ĐỘNG GỬI (App Password) ✅ KHUYẾN NGHỊ]** / **[Gmail MCP — chỉ
  >   tạo NHÁP, gửi tay]**. **MẶC ĐỊNH/ưu tiên SMTP** (báo cáo + lịch nền cần tự gửi); **CHỈ fallback MCP** khi user chọn
  >   rõ hoặc KHÔNG lập được App Password/2FA. Chọn SMTP → đi luồng **API → Gmail SMTP** bên dưới (App Password ở `~/.zshrc`
  >   hoặc `.env.local`).
  - ▸ **Connector GỘP nhiều dịch vụ → HỎI sub-service** (AskUserQuestion; mỗi dịch vụ = 1 nguồn RIÊNG để
    verify/quét, đừng dừng ở "đã kết nối M365" rồi thôi): **Microsoft 365** → **[SharePoint] / [Outlook] /
    [Cả hai]**; **Atlassian Rovo** → **[Jira] / [Confluence] / [Cả hai]**. (Gmail là 1 dịch vụ — không hỏi.)
    Mỗi sub-service ghi entry riêng: `source_type` = `sharepoint`/`outlook`/`jira_cloud`/`confluence`, method `mcp`.
  > 🔁 **Atlassian Rovo phục vụ CẢ Jira:** report/scan (`/claude-knowledge-daily-report`, `/claude-knowledge-send-mail`, WF14) coi **cả
  >   `source_type: atlassian` (entry Rovo gộp)** lẫn `jira_cloud` (đã tách) là **nguồn Jira MCP** — entry `atlassian__mcp`
  >   sẵn có vẫn quét Jira được, KHÔNG cần kết nối lại. Nhiều Jira khác **domain** → mỗi cái 1 entry id riêng
  >   (`__<slug-host>`) + base_url + cred riêng (API: `JIRA_ENV_FILE`/token_env riêng) để quét song song không lẫn.
- **API** (6 nguồn → **PHÂN TRANG 2 thẻ**; ưu tiên **OAuth 2.0**, PAT là fallback):
  - **Thẻ 1:** **[Jira Cloud]** / **[Jira Server / self-host]** / **[GitHub]** / **[Khác — xem thêm]**.
  - Chọn **[Khác — xem thêm]** → **Thẻ 2:** **[GitLab]** / **[SharePoint (Microsoft Graph — ĐẨY/ghi KB)]** /
    **[Gmail SMTP (App Password — TỰ ĐỘNG GỬI mail)]** / **[Gmail API (OAuth2 — FALLBACK gửi khi SMTP bị chặn)]**.
  > SharePoint API khác MCP Microsoft 365 (chỉ đọc): API Graph để **GHI** KB. Auth: app-only
  > client-credentials (cần admin consent `Sites.ReadWrite.All`, chạy nền) **hoặc** device-flow
  > (`sync_sharepoint.py --login`, tương tác). source_type = `sharepoint`, method = `api`.
  > **Gmail SMTP** = kênh GỬI mail tự động (báo cáo/lịch nền). source_type = `gmail_smtp`, method = `smtp`
  >   (không OAuth — dùng **App Password** + 2FA). Khác Gmail MCP (chỉ tạo nháp). Xem ▸ Gmail SMTP ở Bước 3.
  > **Gmail API (OAuth2)** = **FALLBACK gửi mail qua HTTPS** khi mạng chặn SMTP (vd firewall công ty chỉ cho 443).
  >   `send_report.py` tự `SMTP → Gmail API` khi SMTP fail (`--transport auto`). source_type = `gmail_api`, method = `https`.
  >   Cần **Client ID + Client Secret** (OAuth client kiểu **Desktop app**, đã bật Gmail API). Xem ▸ Gmail API ở Bước 3.
- **EXCEL / SHEET (nguồn TASK cho báo cáo — gộp chung với Jira, chỉ TƯƠNG TÁC):**
  - **[Excel local .xlsx]** → KHÔNG auth: hỏi **đường dẫn file** (AskUserQuestion gợi ý + ô "Other") + **tên sheet** (bỏ trống = sheet đầu)
    → ghi entry `source_type: excel`, `method: local_file`, `file_path`, `sheet_name` (id `excel__local[__<slug>]`). Verify: thử
    `python3 tools/excel-to-obsidian/import_excel.py --file <path> [--sheet …]` chạy được (parse OK) rồi mới ghi.
  - **[Excel trên SharePoint 365]** → ĐỊNH VỊ bằng MCP **Microsoft 365** (đã *connected* trong Claude App) + TẢI bằng **Graph
    quyền READ**. Cần app Azure AD có **Sites.Read.All** (+ admin consent) → đặt `SHAREPOINT_TENANT_ID/CLIENT_ID/CLIENT_SECRET`
    ở `~/.zshrc` hoặc `tools/sharepoint-sync/.env.local` (device-flow: `sync_sharepoint.py --login`). Ghi entry `source_type: sheet`,
    `method: mcp`. Lúc báo cáo: `sharepoint_search` (fileType xlsx) → URI `file:///{driveId}/{itemId}` → `import_excel.py
    --graph-item "<driveId>/<itemId>"` (Graph token → tải .xlsx thật + parse ô chuẩn). ⚠️ KHÔNG dùng read_resource lấy ô
    (trả text lệch cột, không downloadUrl). Cột tối thiểu **summary + status**; cột lạ → `--map`/`excel.map`. App-only Sites.Read.All chạy được cả nền.
  - **[Google Sheet]** (chưa có MCP connector): "Publish to web → CSV" → `import_excel.py --from-url "<csv_url>"`; hoặc tải .xlsx → `--file`.

> 🔖 **Đánh dấu đã kết nối:** đối chiếu với `--list` — nguồn nào ĐÃ có entry `<source_type>__<method>`
> (đúng phương thức đang chọn) thì gắn badge **"✓ đã kết nối"** trên thẻ đó (chọn lại = kiểm tra/cập nhật,
> replace-in-place; KHÔNG tạo entry trùng).

> ⚠️ **API vs MCP tính RIÊNG:** cùng một nguồn (vd Jira Cloud) qua API và qua MCP = **2 entry riêng**
> (id khác nhau) → liệt kê/scan tách biệt. ID = `<source_type>__<method>[__<slug-host>]`
> (vd `jira_cloud__api`, `jira_cloud__mcp`, `jira_server__api__companyvn`).

### Bước 3 — Kết nối
- **MCP** → **gọi `/mcp` TRƯỚC** (Claude Code / Claude Desktop): liệt kê MCP server, **kết nối + authorize**
  server của nguồn (Atlassian / Microsoft 365 / Gmail) — phải connected rồi tool MCP mới gọi được. Trên
  **Cowork (web)** thì bật/authorize ở **Settings → Connectors** (OAuth do app quản lý). Chỉ khi server đã
  **connected** → **Verify TỪNG sub-service đã chọn** bằng đúng MCP tool (gọi được + trả kết quả = connected):
  **SharePoint → `sharepoint_folder_search`** (hoặc `sharepoint_search`) · **Outlook → `outlook_email_search`** ·
  **Jira → search Jira** · **Confluence → search Confluence**. OK mới sang Bước 4.
- **API** → ưu tiên **OAuth 2.0 Device Flow** (browser-OAuth chạy được từ CLI):
  1. Bắt đầu device flow với provider (GitHub `https://github.com/login/device/code`; GitLab/Jira **Cloud** tương đương). **Jira Server/DC KHÔNG có OAuth device-flow → dùng PAT (xem ▸ Jira bên dưới).**
  2. Hiện **verification URL + user code** cho user (KHÔNG phải secret) → user duyệt trên trình duyệt → poll token.
  3. Ghi **access token** vào **biến môi trường SHELL** — MẶC ĐỊNH, KHÔNG tạo `.env` trong project (rule §1.6):
     - `export KORA_<SRC>_TOKEN=...` (+ `_EMAIL` / `_BASE_URL` nếu cần) vào `~/.zshrc` (bash → `~/.bashrc`;
       chọn rc theo `$SHELL`). Token KHÔNG ra chat. Các tool đọc qua `os.getenv`.
     - 🔄 **LUÔN DÙNG `source` ĐỂ LẤY CONFIG MỚI:** sau khi ghi/ĐỔI token trong `~/.zshrc` → **luôn nhắc/chạy
       `source ~/.zshrc`** (hoặc mở Terminal mới) → giá trị MỚI có hiệu lực NGAY; verify lại bằng giá trị mới, **KHÔNG
       dùng config cũ**. (Qua `run_command`/MCP thì server **tự `source ~/.zshrc` mỗi lần** → đổi token KHÔNG cần restart.)
     - vd GitHub: `export KORA_GITHUB_TOKEN=...`; GitLab: `export KORA_GITLAB_TOKEN=...`.
  ▸ **Jira — chọn ĐÚNG theo nguồn ở Bước 2 (đừng để Server hoá Cloud):**
     - **Jira Server / self-host** (`source_type: jira_server`) → **PAT/Bearer**, KHÔNG OAuth, KHÔNG atlassian.net:
       `export JIRA_BASE_URL=https://jira.cong-ty.vn JIRA_PAT=<PAT> JIRA_AUTH_MODE=server`.
       **TUYỆT ĐỐI KHÔNG set `JIRA_EMAIL`** — có EMAIL → `import_jira._is_cloud()` hiểu nhầm là Cloud.
     - **Jira Cloud** (`source_type: jira_cloud`, `*.atlassian.net`) → **Basic email:token** (hoặc OAuth):
       `export JIRA_BASE_URL=https://<x>.atlassian.net JIRA_EMAIL=<email> JIRA_PAT=<API token> JIRA_AUTH_MODE=cloud`.
  3b. **CHỈ tạo `.env.local` trong project ở 2 NGOẠI LỆ:**
     - **Archive** (`/claude-knowledge-archive`): gói bàn giao ship đúng 1 `.env.local` read-only (key đọc KB chung).
     - **Lịch sync nền** (`/claude-knowledge-schedule`): mỗi NGUỒN user chọn auto-sync mới tạo `.env.local` RIÊNG cho
       nguồn đó (vd `tools/jira-to-obsidian/.env.<nguồn>`, `tools/github-sync/.env.local`) vì cron/launchd
       không đọc được shell tương tác. Ngoài 2 ca này → luôn dùng shell env.
  4. **Fallback PAT:** nếu user từ chối OAuth, hoặc nguồn sẽ dùng cho **lịch chạy nền** (cron không mở được
     trình duyệt) → yêu cầu **PAT/long-lived token** thay vì OAuth (xem cảnh báo headless ở `/claude-knowledge-schedule`).
  ▸ **Gmail SMTP (App Password — TỰ ĐỘNG GỬI):** KHÔNG OAuth, KHÔNG MCP — gửi trực tiếp qua SMTP để báo cáo/lịch
     nền **tự bắn mail** (không cần tạo nháp tay).
     1. **CARD NHẬP (AskUserQuestion) — Claude hỏi thẳng 2 trường KHÔNG bí mật, gợi ý sẵn + ô "Other" cho user gõ:**
        - **Email người gửi** (`SMTP_USER`) — tài khoản gửi CHUYÊN DỤNG (vd `ftel.medicare@gmail.com`). **TUYỆT ĐỐI
          KHÔNG tự điền email cá nhân / email đăng nhập của user** — bắt user chọn gợi ý hoặc gõ ở ô "Other".
        - **Tiêu đề mail mặc định** (`MAIL_FROM_NAME`, vd "Claude Knowledge AI Daily Report") — gợi ý + ô "Other".
        > ⛔ **App Password (mật khẩu) KHÔNG hỏi qua card/chat.** Nhập password vào ô chat = lộ secret trong hội thoại
        >   (vi phạm rule #8 + rule an toàn). Card CHỈ nhận `SMTP_USER` + tiêu đề; password đi qua FILE ở mục 3.
     2. **Tài khoản gửi phải bật xác minh 2 bước** → tạo **App Password** (16 ký tự) tại
        *myaccount.google.com → Security → App passwords*.
     3. **Claude TỰ TẠO + ĐIỀN SẴN file** `"$PWD/tools/report-mailer/.env.local"` (`mkdir -p tools/report-mailer`; gitignore).
        Điền `SMTP_USER` + `MAIL_FROM` + `MAIL_FROM_NAME` **từ card**, để **PLACEHOLDER** đúng dòng `SMTP_PASS` cho user tự dán:
        ```
        SMTP_HOST=smtp.gmail.com
        SMTP_PORT=587
        SMTP_SECURITY=starttls
        SMTP_USER=<email từ card>
        MAIL_FROM=<email từ card>
        MAIL_FROM_NAME=<tiêu đề từ card>
        SMTP_PASS=<DÁN APP PASSWORD 16 KÝ TỰ VÀO ĐÂY — KHÔNG dán vào chat>
        ```
        → **present file cho user** kèm đường dẫn folder tuyệt đối + cách mở nhanh (macOS Finder `Cmd+Shift+G`; file ẩn
        `Cmd+Shift+.` · Windows Explorer thanh địa chỉ). User **dán App Password THẲNG VÀO FILE** (KHÔNG qua chat).
        Người nhận thấy *&lt;tiêu đề&gt; &lt;email gửi&gt;*. Điền xong chạy verify — **KHÔNG cần `source`** (script tự đọc).
        *(User muốn gom ở `~/.zshrc` thay vì file → vẫn được: `export SMTP_HOST/PORT/USER/PASS/MAIL_FROM_NAME` tay, password KHÔNG qua chat.)*
     4. `source_type = gmail_smtp`, method = `smtp`, `creds.kind = dotenv` (trỏ `tools/report-mailer/.env.local`).

  ▸ **Gmail API (OAuth2 — FALLBACK gửi khi SMTP bị chặn):** khi mạng chặn MỌI cổng SMTP (587/465/25/2525) nhưng proxy
     cho CONNECT 443, gửi mail qua **Gmail API/HTTPS** thay SMTP. `send_report.py --transport auto` **TỰ fallback** SMTP→Gmail API
     khi SMTP lỗi kết nối (cùng tài khoản, cùng banner/đính kèm). Cài 1 lần (3 key `GMAIL_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN`):
     1. **Prereq** (user đã có): Google Cloud Console → bật **Gmail API** → **OAuth client "Desktop app"** → Client ID + Secret.
        Consent screen NÊN **Publish** (refresh token không hết hạn sau 7 ngày). **(Client ID/Secret KHÔNG ra chat/card.)**
     2. **FLOW TỰ TẠO file INPUT TẠM — user CHỈ dán 2 giá trị vào FILE (KHÔNG qua chat); KEY cuối CÙNG ở `~/.zshrc` (rule #6, KHÔNG rải .env.local trong source):**
        - `mkdir -p tools/report-mailer`; tạo file input tạm `tools/report-mailer/.oauth-input` với 3 dòng placeholder
          (nối thêm nếu thiếu, KHÔNG đè): `GMAIL_OAUTH_CLIENT_ID=` · `GMAIL_OAUTH_CLIENT_SECRET=` · `KORA_HTTPS_PROXY=http://proxy.hcm.fpt.vn:80` (proxy RIÊNG Kora, chỉ nếu mạng công ty chặn SMTP).
        - **Present file cho user** (card + đường dẫn tuyệt đối; macOS Finder `Cmd+Shift+G` dán path, file ẩn `Cmd+Shift+.`):
          user **dán Client ID/Secret vào ĐÚNG 2 dòng trong FILE** rồi báo "xong". **TUYỆT ĐỐI KHÔNG hỏi/nhận ID/Secret qua chat/card.**
     3. **Chạy OAuth → GHI vào `~/.zshrc` + XOÁ file input (KHÔNG in token):** ưu tiên `run_command` (Claude Desktop):
        `python3 "$T/report-mailer/gmail_oauth_setup.py" --env "$PWD/tools/report-mailer/.oauth-input" --write-zshrc`
        → đọc Client ID/Secret **từ file input** → mở **trình duyệt** uỷ quyền (loopback `127.0.0.1`) → đổi code→refresh token →
        **ghi `GMAIL_OAUTH_*` (+ `KORA_HTTPS_PROXY` nếu có proxy) vào `~/.zshrc`** (chmod 600, idempotent) — **KHÔNG in token**.
        Sau đó **`rm -f tools/report-mailer/.oauth-input`** (không để creds rải trong source) + `source ~/.zshrc`.
        - **LỊCH NỀN** (cron/launchd không đọc shell) → thay `--write-zshrc` bằng `--write-env tools/report-mailer/.env.local` (NGOẠI LỆ rule #6 cho nền).
        - Không có `run_command` → **BÀN GIAO**: user chạy đúng lệnh trên ở **Terminal**.
     4. **Verify:** `source ~/.zshrc; python3 "$T/report-mailer/send_report.py" --check --transport https` (exit 0 = OK).
     5. `source_type = gmail_api`, method = `https`, id `gmail_api__https`, **creds ở `~/.zshrc` (shell env, rule #6)** —
        TÁCH khỏi `gmail_smtp__smtp`; capability = **fallback gửi**. Proxy RIÊNG: **`KORA_HTTPS_PROXY`** (send_report đọc var này,
        KHÔNG đụng `HTTPS_PROXY` hệ thống — hợp với ai dùng proxy-toggle bật/tắt theo mạng).

### Bước 4 — Verify rồi mới GHI (KHÔNG ghi nửa chừng)
- **API:** chạy `python3 "$T/connections/check_connection.py" --check <id> --config "$PWD/config/factory-config.yaml"` (`T` resolve như Bước 0) → đọc JSON kết quả. *(tool đọc PROJECT config theo `--config`/cwd — KHÔNG phải CORE config.)*
- **Gmail SMTP:** verify bằng `KORA_MAILER_ENV="$PWD/tools/report-mailer/.env.local" python3 "$T/report-mailer/send_report.py" --check`
  (biến `KORA_MAILER_ENV` trỏ ĐÚNG file vừa điền — vì script CORE nằm ở `~/.claude/kora-framework/...` sẽ không tự thấy
  file trong project). Tool in `ℹ️ Đọc cấu hình mail từ: …` để xác nhận. Exit 0 = OK → ghi entry `gmail_smtp__smtp`. Lỗi
  auth → nhắc kiểm tra 2FA/App Password; báo "thiếu/không thấy file" → kiểm tra đúng đường dẫn `.env.local`.
- **MCP:** tự gọi 1 MCP tool để verify.
- **Chỉ khi verify THÀNH CÔNG** → ghi 1 entry đầy đủ vào `connections:` của `config/factory-config.yaml`
  (giữ id-uniqueness — trùng id thì replace-in-place), gồm: `id, method, source_type, display_name,
  auth_kind (oauth2|token|mcp_oauth), base_url, creds {kind: mcp_connector|env|dotenv, …pointer…},
  verify {tool|probe}, status: connected, last_checked: <ISO local>, last_error: ""`.
  Verify thất bại → báo lỗi rõ (token sai/hết hạn, connector chưa bật), **KHÔNG ghi entry**.
- **GitHub / GitLab (API) — CHỌN repo/project sau verify (KHÔNG bắt gõ tay):** verify OK → liệt kê để CHỌN
  (giống Jira `--list-projects`): `python3 "$T/connections/check_connection.py" --list-repos <id> --config
  "$PWD/config/factory-config.yaml"` → JSON (`full_name` cho GitHub · `path_with_namespace` cho GitLab) →
  **AskUserQuestion chọn repo/project** (phân trang nếu >4; thẻ đúng schema rule #8: header ≤12 ký tự, mỗi option có
  description, multiSelect) → ghi `github.repo` / `gitlab.repo` + `base_url` (+ `enabled: true`) vào config. Token:
  `KORA_GITHUB_TOKEN` / `KORA_GITLAB_TOKEN` (shell env; **lịch nền → PAT** ở `tools/github-sync|gitlab-sync/.env.local`
  với key `KORA_GITHUB_SYNC_TOKEN` / `KORA_GITLAB_SYNC_TOKEN`).

Kết thúc — **KHÔNG dead-end** (verify xong phải dẫn user đi tiếp, đừng dừng im): báo (các) nguồn/sub-service đã
kết nối, rồi đề xuất bước kế (AskUserQuestion, **item đầu = QUÉT NGAY**): **[A] Quét & lấy dữ liệu ngay
(`/claude-knowledge-scan`)** — SharePoint: *search thư mục (path) → chọn folder → get data về vault*; Outlook: *search email
→ get*; Jira/Confluence: lấy hạng mục công việc/trang · **[B] Kết nối nguồn khác** · **[C] Đặt lịch đồng bộ** · **[D] Dừng**.
