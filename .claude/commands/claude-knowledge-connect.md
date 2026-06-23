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
- **[Xem nguồn đã kết nối]** → liệt kê **TẤT CẢ** entry trong `connections:` kèm trạng thái
  (`display_name` + method + ✓ connected · checked …). **API vs MCP hiển thị TÁCH RIÊNG** (mỗi method 1
  dòng — id `<source_type>__<method>` khác nhau). Mỗi dòng có **[⟳ Kiểm tra lại]** (`--check <id>`).
  Registry rỗng → báo "chưa kết nối nguồn nào". Xong → đề xuất bước kế (không ghi gì).
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
    **[Gmail SMTP (App Password — TỰ ĐỘNG GỬI mail)]**.
  > SharePoint API khác MCP Microsoft 365 (chỉ đọc): API Graph để **GHI** KB. Auth: app-only
  > client-credentials (cần admin consent `Sites.ReadWrite.All`, chạy nền) **hoặc** device-flow
  > (`sync_sharepoint.py --login`, tương tác). source_type = `sharepoint`, method = `api`.
  > **Gmail SMTP** = kênh GỬI mail tự động (báo cáo/lịch nền). source_type = `gmail_smtp`, method = `smtp`
  >   (không OAuth — dùng **App Password** + 2FA). Khác Gmail MCP (chỉ tạo nháp). Xem ▸ Gmail SMTP ở Bước 3.

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
     1. **HỎI tài khoản gửi CHUYÊN DỤNG** (vd `ftel.medicare@gmail.com`) — **TUYỆT ĐỐI KHÔNG tự điền email cá
        nhân / email đăng nhập của user**; nếu chưa rõ, dùng AskUserQuestion (gợi ý + ô "Other"). Tài khoản này bật
        **xác minh 2 bước** → tạo **App Password** (16 ký tự) tại *myaccount.google.com → Security → App passwords*.
        (App Password KHÔNG ra chat / KHÔNG vào card.)
     2. **Đặt creds — 2 cách (send_report đọc ENV TRƯỚC rồi tới file):**
        - **(A) KHUYẾN NGHỊ — `~/.zshrc`** (gom token 1 chỗ như Jira PAT; run_command source được nên Cowork+MCP gửi thẳng):
          `export SMTP_HOST=smtp.gmail.com SMTP_PORT=587 SMTP_USER=<tài khoản gửi> SMTP_PASS=<App Password> MAIL_FROM_NAME="Claude Knowledge AI Daily Report"`.
        - **(B) hoặc file** `"$PWD/tools/report-mailer/.env.local"` (NGOẠI LỆ `.env` hợp lệ; `mkdir -p tools/report-mailer`,
          copy từ `.env.local.example`; gitignore): cùng các key trên + `SMTP_SECURITY=starttls`, `MAIL_FROM=<tài khoản gửi>`.
        Người nhận thấy *Claude Knowledge AI Daily Report &lt;tài khoản gửi&gt;*. KHÔNG nhồi email cá nhân. **Lưu ý:** điền xong
        chạy lại verify là được — **KHÔNG cần `source`** (run_command/script tự đọc). App Password KHÔNG ra chat/card.
     3. `source_type = gmail_smtp`, method = `smtp`, `creds.kind = dotenv` (trỏ `tools/report-mailer/.env.local`).

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
