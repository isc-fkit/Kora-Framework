# Workflow 14 — Báo cáo tiến độ dự án (local, no-server)

> Trigger: "báo cáo tiến độ", "report tiến độ", "tiến độ dự án", "sinh báo cáo" (confirm ý định trước).
> Cũng được Pha 2 (lịch 8:00, `workflows/08-schedule-sync.md`) gọi TỰ ĐỘNG sau khi quét Jira thành công.
>
> Sinh report từ **dữ liệu vault đã quét** (không server, không đẩy đi đâu). Nhấn mạnh: **thời gian
> (ước tính/đã log/còn lại), sprint đang chạy (active), người phụ trách (assignee)**.

## Bước 0 — Kiểm tra dữ liệu

- 🚫 **Guard gói USER:** có `.claude-knowledge-user` (hoặc `package.type: user`) → máy NGƯỜI DÙNG, KHÔNG báo cáo/gửi
  mail. Báo nhẹ "chỉ HOST mới có báo cáo; máy này chỉ get&post KB chung" rồi DỪNG.
- Đọc `vault_path` từ `config/factory-config.yaml`. Vault chưa có note Jira (`source: jira`) →
  báo nhẹ + gợi ý **`quét jira`** trước (workflow 01). KHÔNG sinh report rỗng.
- Khuyến nghị: nếu vault quét bằng bản < v1.1.0 (thiếu `time_*_s` / `sprint_state`) → nhắc **quét lại**
  để có đủ số liệu thời gian/sprint.

## Bước 0.4 — Cổng mật khẩu vận hành (KORA_OPS_PW)

> 🔒 Báo cáo kéo dữ liệu **live** từ nguồn → PHẢI qua cổng vận hành TRƯỚC khi làm mới/sinh report.
> Cùng cổng với `/claude-knowledge-sync`, `/claude-knowledge-send-mail`, lịch nền — **KHÁC** mật khẩu archive. `/claude-knowledge-export-*` KHÔNG dùng cổng này.

`python3 tools/archive-gate/verify_ops_password.py` (đọc env `KORA_OPS_PW` — **KHÔNG hỏi qua card, KHÔNG in**;
Windows `py`). **Exit ≠ 0 → DỪNG**: không làm mới, không sinh report.
- Khác nhánh "dữ liệu CŨ + banner" ở Bước 0.5: nhánh đó chỉ áp **SAU** khi đã qua cổng mà không kéo được
  (mạng/MCP nội bộ) — KHÔNG phải khi cổng hỏng.
- Chế độ TỰ ĐỘNG/lịch (Cowork-scheduled chạy workflow này): mật khẩu lấy từ env
  (`KORA_OPS_PW` / `~/.config/claude-knowledge/ops-pw.env`); thiếu → cổng hỏng → bỏ lượt, KHÔNG sinh report.
- Gói `.claude-knowledge-user` đã bị chặn ở Bước 0 nên không tới bước này.

## Bước 0.5 — LÀM MỚI dữ liệu trước khi report (Pha 2)

> 🛑 **GIAO THỨC: HỎI NGUỒN TRƯỚC, CẤM QUÉT/BUILD TRƯỚC ĐÓ.** Trước khi gọi `check_connection`/`sharepoint_search`/
> `sharepoint_folder_search`/`getVisibleJiraProjects`/`searchJiraIssuesUsingJql`/`import_*`/`build_report`/`read_resource`,
> **BẮT BUỘC** đã qua cổng mật khẩu **VÀ** đã `AskUserQuestion` chọn nguồn. KHÔNG "tự đủ dữ liệu rồi build". 🔒 `build_report`
> TỪ CHỐI nếu vault >1 nguồn mà thiếu `--source-ids`.

> 🎯 **CÂU HỎI ĐẦU TIÊN — chọn NHÓM NGUỒN, multiSelect=true, ĐÚNG 3 NHÓM CỐ ĐỊNH (LUÔN đủ cả 3):**
> **[Jira] · [SharePoint] · [Local Excel]** (+ **[Tất cả]**).
> - ⛔ **KHÔNG dựng câu này từ `check_connection`** (đó là bước drill). **KHÔNG** liệt kê nguồn Jira cụ thể ở đây. **KHÔNG** bỏ SharePoint. **KHÔNG** single-select.
> - 📎 **SharePoint LUÔN hiện** nếu M365 MCP khả dụng (`sharepoint_search`/`sharepoint_folder_search`) — qua connector M365, KHÔNG nằm trong `connections:`, đừng vì thế mà bỏ.
> - ⚖️ **Chỉ GỘP khi chọn ≥2 nhóm**; chọn 1 nhóm → báo cáo CHỈ nhóm đó (không tự kéo Jira khi user chỉ chọn SharePoint).
>
> **Rồi DRILL từng nhóm đã chọn** (giờ mới đọc `check_connection.py --list`):
> - **[Jira]** → multi-select nguồn `jira_*`/`atlassian` (kèm MCP/API + domain) → project.
> - **[SharePoint] — BẮT BUỘC HỎI 2 BƯỚC, KHÔNG tự quét "file mới nhất":** ① `sharepoint_folder_search` → user chọn (các) **FOLDER**; ② `sharepoint_search folderName=<folder>` → user chọn (các) **FILE** (folder có thể có file REPORT task-data và/hoặc file MEETING/Standing-Meeting/OKR `.pptx/.docx` → để user chọn loại nào/cả 2).
>   🔎 **Ô "Other" = TÌM THEO KEYWORD/TÊN FILE:** user gõ keyword (vd `standing meeting`) → `sharepoint_search query="<keyword>"` (tìm theo tên toàn site, có thể kèm `folderName`) → liệt kê khớp → chọn. Dùng khi biết tên file (nhanh hơn duyệt folder).
> - **[Bảng tính (Excel / Google Sheet)]** → sub-hỏi **[Local .xlsx]** (`excel__local`/đường dẫn) hoặc **[Google Sheet (Composio)]**
>   (dán URL/ID hoặc gõ tên → `GOOGLESHEETS_SEARCH_SPREADSHEETS`; nhiều tab → `GOOGLESHEETS_GET_SHEET_NAMES`). ⚠️ Composio = TƯƠNG TÁC (không dùng lịch nền).
> **Mốc "dữ liệu mới"** = các mục có `updated >= last_import` (mốc RIÊNG mỗi nguồn ở `_system/last-import-<nguồn>.txt`); chưa có
> → kéo full. **Báo RÕ:** *"Đang lấy dữ liệu của `<nguồn>` từ mốc `<last_import>`."* (Nguồn Jira chưa quét lần nào → báo cần quét trước.)

> 🏷️ **CHỌN PROJECT — liệt kê ĐẦY ĐỦ TỪNG project + PREFIX NGUỒN:** lấy project của nguồn đã chọn (API `--list-projects`;
> MCP `getVisibleJiraProjects`, **phân trang lấy HẾT**) → hiện **mỗi project 1 dòng `KEY — Tên` kèm prefix** (vd
> `[Cloud·MCP] FA — FMC App`), **KHÔNG rút gọn/bỏ sót**; >4 project → **PHÂN TRANG** (rule #8) + **[✓ Tất cả project]**.
> ⚠️ **MCP refresh PHẢI ghi vault qua `import_jira.py --from-mcp` (mục A bên dưới)** — nếu chỉ đọc inline mà KHÔNG chạy
> `--from-mcp` thì report xong **vault không được cập nhật** (đúng lỗi "cập nhật báo cáo không lưu tri thức").

> 💡 Nếu `config > jira.effort_field` có giá trị (vd `customfield_10867`), **đặt biến
> `JIRA_EFFORT_FIELD=<id>` trước mọi lệnh `import_jira.py`** (token lẫn `--from-mcp`) để gộp field
> "ước tính theo giờ" vào est khi hạng mục công việc thiếu time-tracking chuẩn.
> 🧩 Tương tự với **Complexity**: đặt `JIRA_COMPLEXITY_FIELD=<id>` (từ `config > jira.complexity_field`; rỗng → tool tự
> dò field tên "Complexity") trước `import_jira.py` → ghi frontmatter `complexity`. Khi build report, truyền
> `--complexity-high <config jira.complexity_high, mặc định 7>` để báo cáo lấy nhóm điểm ≥ ngưỡng làm TRỌNG TÂM.

Kiểm tra độ mới: `python3 tools/jira-to-obsidian/import_jira.py --check-fresh` (Windows `py`) → JSON
`{last_import, is_stale, age_days, done_today}`. **`done_today:true` & `is_stale:false` → BỎ QUA làm mới**
(dữ liệu đủ mới), sang Bước 1. Ngược lại, làm mới **theo (CÁC) NGUỒN user đã chọn** (`check_connection.py --list --json`
→ đọc `method` + `source_type` + `base_url` + `creds` mỗi entry). **NHIỀU nguồn → LẶP, mỗi nguồn route riêng** (API host +
API Atlassian + MCP, nhiều domain đều quét được; tích lũy CÙNG vault):

**A) Nguồn `method: mcp` (`source_type` = `atlassian` Rovo **hoặc** `jira_cloud`):** kéo qua **MCP TOOL** (KHÔNG import_jira API)
→ nạp vào vault. (Liệt kê project: `getVisibleJiraProjects`.):
1. `since` = `last_import` (chưa có → kéo full).
2. MCP `searchJiraIssuesUsingJql`: `project = <KEY> AND updated >= "<since>"` (hoặc `project=<KEY>` nếu
   full), `fields:["*all"]`. Kết quả lớn MCP **tự lưu ra file** → dùng path đó; nhỏ (inline) → ghi ra
   `reports/_mcp-pull-<PROJECT>.json` (đặt tên **theo từng project** để tránh đè khi quét nhiều project). (KHÔNG nạp cả khối vào ngữ cảnh — xử lý qua file.)
3. Lấy map tên field 1 lần: `getJiraIssue` 1 hạng mục công việc `expand=names` → ghi `{id:name}` ra `reports/_mcp-names.json`.
4. Nạp vào vault (tái dùng toàn bộ logic ghi note): `python3 tools/jira-to-obsidian/import_jira.py
   --from-mcp <file> --names reports/_mcp-names.json --since` (cờ `--since` để bật idempotent-per-day).
5. Reindex: `python3 tools/kb-indexer/build_index.py --root .`.
> 🔄 **Chắc chắn MỚI NHẤT (status + comment) → FULL-scan project báo cáo, GHI ĐÈ:** thay vì `--since` (có thể bỏ
> sót comment-only / task đã Done trên server), quét FULL `python3 tools/jira-to-obsidian/import_jira.py --jql
> "project in (<KEYS>)"` (KHÔNG `--since`). `_purge_stale` đảm bảo **1 file/issue, ghi đè, không nhân bản** — local
> luôn khớp server. (Lịch nền cũng làm bước này trước khi build — xem orchestrator.)
> Phiên scheduled nền **thiếu MCP** → coi như không kéo được → xử như nhánh "cũ" của B (báo cũ + nhắc mở Cowork gõ "báo cáo tiến độ").

**B) Nguồn `method: api` (jira_server self-host / jira_cloud qua API):** kéo bằng **`import_jira.py`** với env CỦA ĐÚNG
nguồn — đặt ở đầu lệnh: `JIRA_BASE_URL=<entry.base_url>` (+ `JIRA_AUTH_MODE=server` nếu jira_server; token:
`creds.kind=dotenv` → `JIRA_ENV_FILE=<dotenv_path>`, `kind=env` → token đã ở shell env). FULL-scan:
`import_jira.py --jql "project in (<KEYS>)"` (không `--since`). **Nhiều nguồn API khác domain → mỗi nguồn 1 bộ env riêng** (lặp).
- **Khi MÁY chạy tới được Jira** (interactive trên máy user, đúng VPN/mạng) → kéo trực tiếp như trên.
- **Khi KHÔNG tới được** (sandbox Cowork / lịch nền tới host nội bộ) → `is_stale:false` report bình thường;
  `is_stale:true` → **vẫn sinh report (dữ liệu CŨ, có banner)** rồi in **lệnh terminal copy-paste** (OS-dynamic) cho user tự kéo:
  `JIRA_BASE_URL=<base_url> [JIRA_AUTH_MODE=server] python3 "<TOOL_DIR>/import_jira.py" --jql "project in (<KEYS>)"`.
  Nhắc: "Chạy lệnh trên để cập nhật, rồi gõ **'báo cáo tiến độ'** lại → báo cáo mới." User kéo xong → chạy lại workflow.

**C) Nguồn `source_type: excel`/`sheet` (Excel/Google Sheet/SharePoint) → GỘP vào báo cáo như Jira** (CHỈ tương tác):
- **`method: local_file`** (file .xlsx): `python3 "<TOOL_DIR>/excel-to-obsidian/import_excel.py" --file <entry.file_path>
  [--sheet <entry.sheet_name>] --source-id <entry.id> [--project <KEY>] [--map '<json nếu tên cột lạ>']`. Parse bằng thư
  viện chuẩn (zipfile+xml), tự nhận cột Việt/Anh, ghi note `source: excel` vào `07_Imported/<id>/` (ghi đè trọn — idempotent).
- **EXCEL/SHEET TRÊN SHAREPOINT 365 — 2 cách (chọn theo nhu cầu):**
  **① QUA M365 MCP — DÙNG FILE CSV (KHÔNG cần Graph token, đơn giản nhất):** vì `read_resource` trả **text NGUYÊN VẸN cho file CSV**
  (chỉ .xlsx mới bị lệch cột). Bước:
  1. Upload bảng dưới dạng **`.csv`** lên SharePoint (UTF-8). `sharepoint_search` `query="<tên>" fileType="csv"` → chọn file.
  2. `read_resource` URI → trả **text CSV** → Claude ghi y nguyên ra `reports/_sheet-<id>.csv`.
  3. `python3 "<TOOL_DIR>/excel-to-obsidian/import_excel.py" --from-rows reports/_sheet-<id>.csv --map <…> --source-id <id> [--project <KEY>]`.
  - Tạo CSV mẫu: `python3 "<TOOL_DIR>/excel-to-obsidian/make_sample.py" <out>.csv 100`.
  **② QUA GRAPH (quyền READ) — cho file .XLSX, đáng tin + chạy được nền:** `sharepoint_search fileType="xlsx"` → URI
  `file:///{driveId}/{itemId}` → `import_excel.py --graph-item "<driveId>/<itemId>"` → xin Graph token (creds `SHAREPOINT_*`,
  app Azure AD **Sites.Read.All**) → `GET /drives/.../content` → parse ô CHUẨN (honor `HTTPS_PROXY`).
  > ⚠️ **KHÔNG** dùng `read_resource` để lấy ô của **.xlsx** (text lệch cột, không downloadUrl). Với .xlsx qua MCP → dùng **Graph (②)**;
  > muốn MCP thuần không token → để file dạng **CSV (①)**.
- **`method: composio` — GOOGLE SHEET QUA COMPOSIO (TƯƠNG TÁC, không cần Publish-CSV/Graph):** `COMPOSIO_SEARCH_TOOLS`
  (use_case "read google sheet") kiểm `googlesheets` ACTIVE → `GOOGLESHEETS_BATCH_GET` `{spreadsheet_id:"<ID/URL>",
  ranges:["<Tab>!A1:Z10000"], valueRenderOption:"UNFORMATTED_VALUE"}` → chuẩn hoá ragged rows (header + pad theo header) →
  ghi `reports/_sheet-<id>.csv` → `import_excel.py --from-rows reports/_sheet-<id>.csv --map <…> --source-id gsheet_<id>`.
  Sheet lớn → đọc **theo khối 10000 dòng** (grid-limit + rate 60 reads/phút). ⚠️ MCP → **chỉ tương tác**, KHÔNG dùng cho lịch nền.
  - **Google Sheet**: "Publish to web → CSV" → `import_excel.py --from-url "<csv_url>"`.
- Sau nạp: reindex `build_index.py --root .`. build_report **tự gộp** note `source: excel` chung với Jira (cùng schema:
  status/assignee/story_points/complexity/time_*; vai trò PM/QC vẫn áp). Cột bắt buộc tối thiểu: **summary** + **status**.

## Bước 0.6 — Xác định VAI TRÒ thành viên (để hiểu CONTEXT phân tích từng người)

> 🎯 **BẮT BUỘC HỎI user nhập TÊN + VAI TRÒ TRƯỚC khi build** — để báo cáo hiểu ĐÚNG context mỗi người, tránh
> đánh giá sai (vd báo PM "thiếu giờ"). 🔒 **CODE-GATE:** `build_report.py` **TỪ CHỐI build** report tiến độ (>1 người)
> khi config CHƯA có `pm_members`/`qc_members` **VÀ** thiếu `--roles-confirmed` → KHÔNG thể lỡ bỏ qua bước này.
> Vai trò quyết định cách đo:
> - **Dev** — đo bằng **giờ-công** (đã log so giờ chuẩn; cảnh báo OT/thiếu).
> - **PM/PO** — **CHỈ ĐIỀU PHỐI, KHÔNG log task**: tạo Epic/Request/US → **KHÔNG đo bằng giờ-công, KHÔNG cảnh
>   báo "chưa log giờ", loại khỏi capacity team**. Đánh giá bằng số hạng mục điều phối.
> - **QC/tester** — tạo Bug → đo bằng **số Bug**, không đo giờ-công.

1. Lấy danh sách thành viên có trong dữ liệu đã chọn (assignee + reporter từ vault / `progress-data-<ngày>.json`).
2. **AskUserQuestion** (đa lựa chọn, kèm ô **"Other"** để gõ tên chưa có trong danh sách):
   - **"Ai là PM/PO (chỉ điều phối, KHÔNG log task)?"** → ghi `reports.pm_members`.
   - **"Ai là QC/tester (tạo Bug, không log giờ)?"** → ghi `reports.qc_members`.
   - Còn lại mặc định **Dev**.
   - Đã có `reports.pm_members` / `reports.qc_members` trong config → **vẫn HIỆN ra + AskUserQuestion [Dùng đúng vậy] /
     [Điều chỉnh]** (xác nhận nhanh — KHÔNG tự dùng im lặng, KHÔNG hỏi lại từ đầu). [Điều chỉnh] → hỏi lại như trên.
   - User xác nhận **tất cả là Dev** (không PM/QC) → truyền **`--roles-confirmed`** cho `build_report.py`; khi đó tool
     vẫn **TỰ NHẬN DIỆN** PM/QC theo dấu hiệu (PM: 0 logtime + tạo Epic/Request/US; QC: 0 logtime + tạo Bug). ⛔ KHÔNG
     có role config **VÀ** KHÔNG `--roles-confirmed` → tool **TỪ CHỐI** (code-gate ở trên) để buộc hỏi.
3. Ghi vào `config/factory-config.yaml` mục `reports:` dạng inline list:
   `pm_members: ["Tên A","Tên B"]` / `qc_members: ["Tên C"]` (build_report đọc đúng định dạng này).
   Đây là **DATA** → lần sau dùng lại + sửa được bất cứ lúc nào (không cần hỏi lại nếu đã đúng).
4. Chế độ **TỰ ĐỘNG / lịch nền** → KHÔNG hỏi; đọc thẳng `reports.pm_members` / `qc_members` từ config (hoặc auto-detect).

## Bước 1 — Sinh số liệu + dashboard

> 🚫 **TUYỆT ĐỐI KHÔNG tự viết file HTML báo cáo bằng tay** (sẽ mất banner + thiếu section + sai layout — đúng lỗi đã gặp).
> Báo cáo CHỈ được sinh bởi `build_report.py` (chuẩn: banner, trạng thái, theo người, complexity, 🗺️ roadmap, capacity, rủi ro).
> Mọi nguồn (Jira/SharePoint/Excel) đã import vào vault ở Bước 0.5 → build_report tự GỘP. Đừng ghép HTML từ nhiều nguồn.

Chạy (Claude tự chạy trong sandbox; user chạy tay thì OS-dynamic — Windows `py`). **Scope đúng project đã chọn**
bằng `--projects` (báo cáo CHỈ gồm project đó; rỗng = tất cả) — dữ liệu đã được làm mới ở Bước 0.5:

```bash
python3 tools/progress-report/build_report.py --source-ids "<SRC_IDS>" --projects "<KEYS đã chọn>" [--scope sprint|recent|all] [--recent-days 30]
```
> 🏷️ **`--source-ids` (lọc NGUỒN — quan trọng):** báo cáo **CHỈ gồm nguồn user đã chọn** (Bước 0.5). Token: `jira`
> = mọi note `source: jira`; `<source_id>` = đúng lần import Excel/SharePoint (vd `local_kehoach,sp_standup`). Rỗng =
> mọi nguồn. **Không lọc → vault còn note Jira cũ + import khác lẫn vào → mail ra "dữ liệu cũ"/sai nguồn.** Row import
> (Excel/SharePoint) là snapshot → KHÔNG bị `--scope recent` loại (đã fix), nhưng vẫn cần `--source-ids` để đúng phạm vi nguồn.
> 📊 **Phạm vi (dự án lớn):** `--scope sprint` (chỉ sprint đang chạy, fallback N ngày) · `--scope recent --recent-days N`
> (hạng mục công việc `updated` trong N ngày) · bỏ qua = toàn bộ. Báo cáo hiện **nhãn phạm vi** trên chip header. Scan tương ứng nên
> bound `... AND updated >= -Nd` cho nhẹ.

Tạo trong `reports/`:
- `progress-data-<ngày>.json` — số liệu thô (nguồn cho UI inline).
- `progress-report-<ngày>.html` + `progress-report-latest.html` — **dashboard standalone** (mở bằng
  trình duyệt, chia sẻ được; phong cách tối glass; **biểu đồ SVG** (donut trạng thái + bar theo người/dự án),
  **filter tương tác luôn hiện** (dự án · thành viên · trạng thái · loại), bảng zebra/hover + chỗ `#kr-ai`).
- `email-body-<ngày>.html` + `email-body-latest.html` — **thân email tĩnh, responsive cho điện thoại** dùng để **GỬI**
  (email-safe, KHÔNG JS; banner = URL remote → `send_report` swap **CID** lúc gửi; có khối AI `<!--KR-AI-START-->`/`<!--KR-AI-END-->` điền ở Bước 1.5).
- `email-preview-latest.html` (+ `email-preview-<ngày>.html`) — **bản XEM TRƯỚC mail** giống hệt email-body nhưng
  **banner nhúng base64** → hiện được trong Cowork/trình duyệt (URL remote hay bị chặn khi xem). **Chỉ để preview, KHÔNG gửi** (Gmail/Outlook chặn `data:`).

## Bước 1.5 — PHÂN TÍCH AI (SPAWN 3 con agent chuyên biệt SONG SONG)

> Đọc `reports/progress-data-<ngày>.json` (time est/log/remaining, active sprint + `sprint_end`, by-assignee,
> complexity, status, risks). **BẮT BUỘC dùng Agent tool SPAWN 3 con agent quản lý SONG SONG** (mỗi con 1 góc
> chuyên môn, đều đọc `reports/progress-data-latest.json`) — KHÔNG bịa số, chỉ suy từ JSON; thiếu dữ liệu thì nói rõ.
> **Fallback DUY NHẤT:** môi trường KHÔNG có Agent tool (vd CLI tắt sub-agent) → Claude TỰ viết inline như cũ.

**🤖 3 LỆNH SPAWN (gửi CÙNG 1 lượt để chạy SONG SONG — mỗi con ghi ra 1 file tạm):**
- **Agent ĐIỀU HÀNH/STATUS** — `Agent(subagent dùng skill **operations:status-report**)`, prompt:
  > *"Đóng vai chuyên viên ĐIỀU HÀNH dự án, dùng skill `operations:status-report`. Đọc `reports/progress-data-latest.json`.
  > Viết MARKDOWN (trích SỐ cụ thể: mã hạng mục·giờ·%·ngày, CẤM chung chung): `## 📌 Tóm tắt điều hành` · `## 🟢 Điểm
  > tích cực` · `## 🎯 Hành động ưu tiên` (theo NGÀY) + KPI tiến độ. Ghi ra `reports/_ai-status.md`."*
- **Agent RỦI RO** — `Agent(subagent dùng skill **operations:risk-assessment**)`, prompt:
  > *"Đóng vai chuyên viên RỦI RO, dùng skill `operations:risk-assessment`. Đọc `reports/progress-data-latest.json`.
  > Viết: `## 🔴 Rủi ro cao (blocker)` · `## 🟡 Rủi ro vừa / Cần theo dõi` — MỖI rủi ro: SỐ + Mức độ + **Dự đoán & lý
  > do BẰNG SỐ** (giờ remaining·%done·ngày trễ·est/spent) + Tác động + Phương án giảm thiểu + KHI NÀO (mốc ngày). Ghi ra `reports/_ai-risk.md`."*
- **Agent NĂNG LỰC/SPRINT** — `Agent(subagent dùng skill **operations:capacity-plan**)`, prompt:
  > *"Đóng vai chuyên viên NĂNG LỰC nguồn lực, dùng skill `operations:capacity-plan`. Đọc `reports/progress-data-latest.json`.
  > Viết: `## 🧩 Độ phức tạp (TRỌNG TÂM)` (hạng mục điểm ≥ ngưỡng, ai ôm cụm khó) · `## 👥 Phân tích theo thành viên`
  > (BẢNG `| Thành viên | Vai trò | Tổng | Done | %Done | Giờ log | %Capacity | Bug | Ghi chú |` — **Dev** đo giờ/capacity;
  > **PM/QC** theo VAI TRÒ, %Capacity = '—', KHÔNG phạt) · `## 📅 Dự đoán sprint / timeline` (quỹ giờ, carry-over). Ghi ra `reports/_ai-capacity.md`."*

**TỔNG HỢP:** gộp 3 file tạm (`_ai-risk.md` + `_ai-capacity.md` + `_ai-status.md`) thành `reports/ai-analysis-latest.md`
**theo ĐÚNG THỨ TỰ MỤC dưới**. (NẾU user chọn "phân tích roadmap" → thêm **Agent CHIẾN LƯỢC/PM** skill
`operations:status-report` viết `## 🗺️ Roadmap & điều phối sprint` từ `roadmap` JSON + `reports/_okr-latest.txt`.)
KHÔNG tự viết HTML/chip tay — tool render CARD MÀU. Các mục (mỗi mục mở đầu `## `, ĐÚNG thứ tự):
   > 📁 **ĐẢM BẢO thư mục `reports/` tồn tại TRƯỚC khi ghi** (Write cần thư mục cha — thiếu sẽ báo *"Error writing
   > file"*). Bước 1 (`build_report.py`) đã tạo `reports/` ở CÙNG cwd; nếu chạy lẻ / Write lỗi → tạo trước:
   > macOS/Linux `mkdir -p reports` · Windows `New-Item -ItemType Directory -Force reports` rồi ghi lại. (build_report
   > nay ghi report vào `reports/` của **project hiện tại** — chạy mọi lệnh ở CÙNG thư mục project.)
   `## 🔴 Rủi ro cao (blocker)` · `## 🟡 Rủi ro vừa / Cần theo dõi` · `## 🟢 Điểm tích cực` ·
   `## 🧩 Độ phức tạp (TRỌNG TÂM)` (đọc `complexity` JSON — hạng mục công việc điểm ≥ ngưỡng, ai phụ trách, ưu tiên review/nguồn lực) ·
   `## 👥 Phân tích theo thành viên` (KÈM BẢNG markdown ĐẦY ĐỦ `| Thành viên | Vai trò | Tổng | Done | %Done | Giờ log | %Capacity | Bug | Ghi chú |` — PM/QC tách đúng vai trò, KHÔNG đo giờ-công) ·
   `## 📅 Dự đoán sprint / timeline` · `## 🎯 Hành động ưu tiên` · `## 📌 Tóm tắt điều hành`.
   - **NẾU user chọn "phân tích roadmap"** → thêm `## 🗺️ Roadmap & điều phối sprint`: đọc `roadmap` JSON (backlog/current/next
     + SP + done%) → bức tranh tổng; **đề xuất bốc task nào vào sprint KẾ** + **sắp xếp sprint HIỆN TẠI** cho hợp lý; gắn mục
     tiêu **OKR/chiến lược** từ `reports/_okr-latest.txt` (nếu có); viết theo góc **PM dự án** (người đã hỏi ở daily-report 5b/5c).
   - Mọi mục viết **CHI TIẾT + kèm BẢNG số liệu đầy đủ** (theo người/sprint/complexity/quá hạn) — từ DỮ LIỆU, không bịa.
   - 📋 **FILE OKR / STANDING-MEETING (non-task) → SECTION RIÊNG:** nếu user chọn file chiến lược → Claude cấu trúc nội dung
     thành `reports/_okr-blocks.json` **TRƯỚC khi build_report** → tool render **section riêng** (grid chia nhóm + khối AI
     phân tích RIÊNG cho OKR) ở **CẢ dashboard LẪN email**. Schema: `{"title","source","groups":[{"icon","label","items":[{"name","chips":[ "text" | {"text","tone":"ok|warn|risk|info"} ]}]}],"analysis_md":"## ...md phân tích riêng..."}`.
     Chia rõ từng nhóm/đầu việc cho dễ nhìn; `analysis_md` đối chiếu OKR ↔ tiến độ sprint, góc PM. (Khác mục 🗺️ Roadmap của task report.)
**RỒI — Render + chèn (BẮT BUỘC):** `python3 "$T/progress-report/build_report.py" --inject-ai reports/ai-analysis-latest.md`
   → tool tự thay khối `<!--KR-AI-->` bằng **CARD MÀU theo mục** + **bảng tô màu cột trạng thái** (Done=xanh lá ·
   In Review=xanh dương · In Progress=cam · Test=tím · Chưa làm=xám) trong **CẢ 3 file -latest cùng lúc**:
   `email-body` (gửi) · `email-preview` (xem trước) · `progress-report` (dashboard `#kr-ai`). ⇒ AI **LUÔN có ở cả email LẪN dashboard**.
   > 🔒 **Backstop:** `send_report.py` **TỪ CHỐI gửi** nếu khối AI còn placeholder (chưa `--inject-ai`) → buộc phải chèn AI thật trước khi gửi (bỏ qua: `--allow-empty-ai`).
**Bản inline Cowork** (Bước 2) dùng **CÙNG nội dung markdown** đó (dashboard `#kr-ai` đã được `--inject-ai` điền sẵn ở bước 2).
Mỗi rủi ro nêu đủ: **mức độ → khả năng/DỰ ĐOÁN + lý do bằng số liệu → tác động → PHƯƠNG ÁN ĐỀ XUẤT từng bước + ai làm + khi nào**. Nội dung mỗi mục:

0. **Đối chiếu theo CHUẨN (Cloud / industry best-practice) — nền cho mọi cảnh báo:** so số liệu với mốc
   chuẩn rồi gọi tên "vượt / đạt / dưới chuẩn" kèm con số (đọc `capacity`, `logged_by_type`, `work_no_log`
   trong JSON):
   - **Năng suất giờ công:** đã log so với **giờ công chuẩn** (ngày làm việc trong tháng × 8h × 5 ngày/tuần).
     `ot_seconds` > 0 → **cảnh báo OT** (nguy cơ burnout/ước tính thấp); đạt < ~80% chuẩn → **log thiếu**
     (nguy cơ under-report / dữ liệu nỗ lực không đủ). Nêu rõ % năng lực + OT/thiếu của nhóm VÀ từng thành viên.
     - ⚠️ **QC/tester (`role` = "QC", `pct_capacity` = null): KHÔNG đánh giá "thiếu giờ".** Họ report bug, không
       logtime như dev (hay chỉ join cuối sprint) → đo bằng **`bugs_reported`** (số bug tạo), KHÔNG so giờ-công.
       Team-capacity chỉ tính Dev. Đừng liệt QC vào "log thiếu / dưới chuẩn năng suất".
     - ⚠️ **PM/PO (`role` = "PM", `pct_capacity` = null): KHÔNG đánh giá "thiếu giờ" / "chưa log".** PM **CHỈ ĐIỀU
       PHỐI** (tạo Epic/Request/US), KHÔNG log task như Dev → KHÔNG đo bằng giờ-công, loại khỏi capacity team.
       Đánh giá PM bằng số hạng mục điều phối/điều hành & tiến độ chung, KHÔNG so giờ-công, KHÔNG liệt vào "log thiếu".
   - **Phủ logtime theo loại:** chỉ Task/Sub-task/Bug log giờ — Epic/User Story/Request KHÔNG; nếu nhiều
     `work_no_log` (Task/Sub-task chưa làm xong mà chưa log) → **dữ liệu nỗ lực không tin cậy**, cảnh báo.
   - **Sprint health:** % done so với % thời gian sprint đã trôi; WIP (đang-làm) quá cao so với sức nhóm; quá hạn.
   - **Phân bổ:** lệch tải giữa thành viên; hạng mục công việc thiếu estimate/assignee.
1. **Phân loại tình trạng (health) theo hạng mục công việc/nhóm:** 🟢 đúng tiến độ · 🟡 cần chú ý · 🔴 rủi ro cao.
   Tiêu chí: quá hạn (duedate < hôm nay & chưa done), sprint active sắp hết hạn mà chưa xong, thiếu
   estimate/assignee, `remaining_s` cao so với thời gian còn lại, **lệch chuẩn năng suất (OT/thiếu)**.
2. **Dự đoán TRƯỢT TIMELINE (mỗi active sprint):** so `sprint_end` với hôm nay → `days_left`; cân khối
   còn lại (`remaining_s`, số hạng mục công việc chưa done) → **nguy cơ trượt: Thấp / Vừa / Cao** + lý do (vd "còn 2
   ngày, 6 hạng mục công việc chưa done, remaining 40h ≫ sức chứa → **Cao**"). Nêu hạng mục công việc kéo lùi tiến độ.
3. **Đề xuất theo TỪNG THÀNH VIÊN:** mỗi assignee 1 dòng — quá tải / đúng nhịp / rảnh / đang trễ →
   hành động gợi ý (giãn việc, hỗ trợ, ưu tiên hạng mục công việc X…) dựa trên total/đang-làm/remaining/done của họ.
4. **Gợi ý GIẢI QUYẾT rủi ro:** mỗi rủi ro 🔴 → 1–2 hành động cụ thể (giao lại, tách nhỏ, dời sprint,
   thêm người…).
5. **Tổng kết điều hành (1–2 câu):** sức khỏe chung + việc cần làm NGAY.

## Bước 2 — Hiển thị UI trong Cowork (inline)

Đọc `reports/progress-data-<ngày>.json` → **render dashboard NGAY trong chat** bằng `visualize`:
1. Gọi `mcp__visualize__read_me` (modules: `chart`) — nạp guideline 1 lần.
2. `mcp__visualize__show_widget` với một dashboard **TUÂN guideline visualize** (KHÔNG dùng nền tối/
   màu cứng của file standalone): nền trong suốt + biến CSS `--color-*`, icon Tabler (không emoji),
   số làm tròn. Gồm:
   - **Thẻ metric:** Tổng hạng mục công việc · % hoàn thành · Đã log/Ước tính · Còn lại · Sprint active.
   - **Donut trạng thái** (Done / Đang làm / Chưa làm) + legend HTML.
   - **Bar ngang theo assignee:** giờ Đã log vs Ước tính.
   - **Bar theo PROJECT** (khi báo cáo nhiều project): tổng hạng mục công việc / % done mỗi project.
   - (Bảng chi tiết hạng mục công việc sprint/assignee → in dạng **markdown trong câu trả lời**, KHÔNG nhồi vào widget.)
3. Kèm tóm tắt text **+ khối 🤖 Phân tích AI (Bước 1.5)**: phân loại health, dự đoán trượt timeline mỗi
   sprint, đề xuất theo TỪNG thành viên, gợi ý giải quyết rủi ro, tổng kết điều hành.
4. **Nêu rõ PHẠM VI đã lọc** ở đầu dashboard: nguồn(`--source-ids`) + project(s) + thành viên + khoảng thời gian
   user đã chọn ở `/claude-knowledge-daily-report` (report sinh trên đúng tập đã lọc).
5. **PREVIEW CẢ EMAIL — không chỉ dashboard.** Sau dashboard, hiển thị thêm **bản xem trước MAIL**
   `reports/email-preview-latest.html` (banner base64 nên hiện được) để user **duyệt nội dung + giao diện mail trước
   khi gửi**. Cách hiện: mở/đính file cho user xem inline (hoặc `read` rồi render). **KHÔNG bỏ qua** — đây là yêu cầu:
   skill phải preview cả dashboard LẪN file email. (File GỬI thật vẫn là `email-body-latest.html`.)

## Bước 2.7 — Gửi báo cáo qua email (nếu `reports.email.enabled: true`)

Đọc `reports.email` từ `config/factory-config.yaml`. `enabled: false` → **BỎ QUA** bước này.

- **`method: smtp`** (full-auto, hợp lịch nền) — chạy (Claude tự chạy trong sandbox; user chạy tay thì Windows `py`).
  Đặt `KORA_MAILER_ENV` trỏ ĐÚNG `.env.local` (script CORE ở `~/.claude/kora-framework/...` không tự thấy file project):
  ```bash
  KORA_MAILER_ENV="$PWD/tools/report-mailer/.env.local" \
  python3 tools/report-mailer/send_report.py \
    --to "<nối reports.email.to bằng dấu phẩy>" \
    --html-file reports/email-body-latest.html \
    --no-attach-html \
    --banner "tools/../assets/banner-daily-report.jpg" \
    --attach reports/progress-report-latest.html
  ```
  (`--banner` → banner **nhúng CID inline** nên Outlook không chặn ảnh; bỏ qua nếu không có file thì email dùng link remote.)
  > 🏷️ **Tiêu đề ĐỘNG theo loại báo cáo — KHÔNG `[Kora]`:** BỎ `--subject` → `send_report` đọc `reports/_subject-latest.txt` do `build_report` ghi (vd `Báo cáo tiến độ — FMC — {date}` · `Báo cáo tài chính — …` · `Báo cáo cuộc họp — …`). Chỉ thêm `--subject "<reports.email.subject thay {date}>"` khi muốn **OVERRIDE** (config có giá trị). Header/footer mail dùng tên đơn vị `reports.company` (mặc định **FPT Telecom**) — KHÔNG còn "Claude AI"/"Kora".
  → thân thư = **email-body** (mobile, đã chèn AI ở Bước 1.5); đính kèm = **dashboard tương tác** (lọc trên máy tính).
  Mật khẩu/App Password ở `tools/report-mailer/.env.local` (gitignore). Thiếu `.env.local` → script tự
  báo lỗi rõ: nhắc user copy `.env.local.example` + tạo Google App Password. **TUYỆT ĐỐI không in mật khẩu.**
  > ⚡ **ƯU TIÊN `run_command` (MCP `local-terminal`, Claude Desktop):** khi `SMTP_UNREACHABLE`, nếu có tool `run_command`
  > → gọi nó chạy đúng lệnh `send_report.py` (từ `--emit-command`), cwd=project → GỬI THẲNG trên máy thật (ngoài sandbox),
  > KHÔNG cần bàn giao. Chỉ khi KHÔNG có `run_command` → mới bàn giao file lệnh dưới đây.
  > 🖥️ **Cowork sandbox chặn SMTP + KHÔNG có `run_command` → BÀN GIAO TERMINAL (không dead-end):** đọc stderr — nếu có **`SMTP_UNREACHABLE`**
  > (mạng bị chặn): báo cáo ĐÃ ở `reports/` (local thật) → chạy lại CÙNG lệnh + `--emit-command` (in 1 dòng lệnh path
  > tuyệt đối, KHÔNG gửi) → ghi `reports/claude-knowledge-send-mail.command` (`#!/bin/bash` + `chmod +x`; Windows `.bat`) → báo user
  > mở **Terminal** chạy `bash "reports/claude-knowledge-send-mail.command"` để **gửi tiếp việc dang dở** (terminal gửi SMTP được,
  > chỉ gửi không build lại). **`SMTP_AUTH_FAILED`** → nhắc sửa App Password, KHÔNG bàn giao. Terminal CLI: gửi thẳng.
- **`method: gmail_draft`** (bán tự động) — gọi tool `create_draft` của Gmail connector: `to`=list,
  `subject`, `htmlBody`=nội dung `email-body-latest.html` (đã chèn AI). Báo user: mở Gmail → Drafts → **Gửi**.
- **Lần ĐẦU bật gửi:** ✋ gửi thử tới 1 địa chỉ của user trước, xác nhận nhận được rồi mới gửi cả `to`.
- **Phiên nền thiếu creds/connector → KHÔNG fail im:** vẫn giữ report ở `reports/`, báo user cách khắc phục.

## Bước 3 — Báo file + bước kế

- Báo đường dẫn `reports/progress-report-latest.html` (mở bằng trình duyệt / gửi cho sếp).
- **Đề xuất bước kế (AskUserQuestion):** `[A] Đặt lịch 8:00 tự động pull→report (workflows/08) ·
  [B] Quét Jira lấy dữ liệu mới (workflows/01) · [C] Phân loại hạng mục công việc thành tri thức (workflows/03) · [D] Dừng`.

## Guardrails
- Mặc định **local-only**. CHỈ gửi ra ngoài khi `reports.email.enabled: true` — và chỉ tới đúng `reports.email.to` user đã cấu hình (xác nhận lần đầu). KHÔNG ghi vào `docs/` KB chính — report là artifact ở `reports/`.
- `reports/` là DATA (gitignore + giữ khi update) — không commit báo cáo của user.
- Thiếu số liệu (hạng mục công việc thiếu time/sprint) → report vẫn chạy, nêu rõ "X hạng mục công việc thiếu dữ liệu", không bịa.
