---
description: Generate a progress report. Choose one or more projects (multi-select), filter by members, pull data for a chosen time range from the sources, then build the dashboard. Password-gated (operations password) since it pulls live data. Triggers (vi): «báo cáo tiến độ», «report tiến độ», «tiến độ dự án», «cập nhật tiến độ», «sinh dashboard» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-daily-report` — build a progress report.

> 🚫 **Guard gói USER:** nếu có file `.claude-knowledge-user` ở gốc project (hoặc `package.type: user` trong config)
> → đây là máy NGƯỜI DÙNG, KHÔNG có báo cáo/gửi mail (chỉ HOST mới có). Báo nhẹ: *"Báo cáo & gửi mail
> chỉ chạy ở máy HOST. Máy này chỉ đồng bộ KB chung (get & post)."* rồi DỪNG, KHÔNG sinh report.

**Chọn NGUỒN → PROJECT (chi tiết, AskUserQuestion).** Resolve path tool (bản cài ở CORE):
`T=tools; [ -e "$T/connections/check_connection.py" ] || T="$HOME/.claude/kora-framework/tools"`.
1. 🔒 **CỔNG MẬT KHẨU vận hành (`KORA_OPS_PW`)** TRƯỚC — báo cáo kéo dữ liệu live nên PHẢI qua cổng:
   `python3 "$T/archive-gate/verify_ops_password.py"` (đọc env **HOẶC** `~/.config/claude-knowledge/ops-pw.env` — đặt 1 lần bằng
   `/claude-knowledge-ops-password`; **KHÔNG hỏi qua card, KHÔNG in**). Exit ≠ 0 → **DỪNG**, không kéo, không sinh report.
2. **CÂU HỎI ĐẦU TIÊN — BẮT BUỘC: chọn NHÓM NGUỒN (multi-select), TUYỆT ĐỐI KHÔNG tự chọn Jira.**
   AskUserQuestion **multiSelect=true**: **[Jira] · [SharePoint] · [Local Excel]** (+ **[Tất cả]**). Đây là câu hỏi
   ĐẦU TIÊN sau cổng mật khẩu — KHÔNG được mặc định/tự ý chọn Jira rồi chạy luôn. (Chỉ bỏ hỏi khi hệ thống có ĐÚNG
   1 nhóm nguồn khả dụng.) Không nhóm nào kết nối → mời `/claude-knowledge-connect`.
2a. **Với MỖI nhóm đã chọn → hỏi nguồn cụ thể của nhóm đó** (đọc `check_connection.py --list --json`):
   - **[Jira]** → liệt kê entry `jira_*`/`atlassian` (nhãn `[Jira·MCP] foxproject` / `[Jira·API] jira.fptmedicare.vn`) → multi-select **nguồn Jira nào**.
   - **[SharePoint]** → `sharepoint_folder_search` → chọn **FOLDER quét**; rồi `sharepoint_search folderName=<folder>` liệt kê file → chọn **(các) file daily-task** + (tùy chọn) **file OKR/Standing Meeting** (chiến lược — cho roadmap, KHÔNG import thành task).
   - **[Local Excel]** → entry `excel__local` (hoặc hỏi đường dẫn .xlsx qua ô "Other") → chọn file.
   > **>4 mục → phân trang** (rule #8). Xong nhóm này mới sang nhóm kế.
2b. **Chọn PHẠM VI báo cáo (quan trọng với DỰ ÁN LỚN — không lấy hết)** — AskUserQuestion:
   **[Sprint đang chạy] (khuyến nghị) / [N ngày gần đây — mặc định 30, ô "Other" tự nhập] / [Toàn bộ]**.
   → đặt `SCOPE` ∈ `sprint|recent|all`, `NDAYS` (mặc định 30). `SCOPE≠all` → **bound scan** (nhẹ) + lọc report.
3–4. **VỚI MỖI nguồn đã chọn → quét bằng ROUTE RIÊNG (vòng lặp), tích lũy vào CÙNG vault** (đọc `method`/`source_type`/
   `base_url`/`creds` từ `--json`):
   - **`method: api`** (jira_server/jira_cloud): đặt env CHO ĐÚNG instance ở đầu lệnh — `JIRA_BASE_URL=<entry.base_url>`
     (+ `JIRA_AUTH_MODE=server` nếu `jira_server`; token: `creds.kind=dotenv` → `JIRA_ENV_FILE=<dotenv_path>`, `kind=env`
     → token đã ở shell env). Liệt kê: `import_jira.py --list-projects` → multi-select project (hoặc [Tất cả]). FULL-scan:
     `import_jira.py --jql "project in (<KEYS>)<+ AND updated >= -<NDAYS>d nếu SCOPE≠all>"` (KHÔNG `--since` → hết status/comment, ghi đè, không nhân bản).
   - **`method: mcp`** (`atlassian`/`jira_cloud`): **DÙNG MCP TOOL, KHÔNG import_jira API** — `getVisibleJiraProjects`
     (liệt kê project → multi-select) → `searchJiraIssuesUsingJql` `project in (<KEYS>)<+ AND updated >= -<NDAYS>d nếu SCOPE≠all>` `fields:["*all"]` (kết quả lớn MCP
     tự lưu file → dùng path đó) + `getJiraIssue expand=names` (map field) → `import_jira.py --from-mcp <file> --names <names>`.
   - ⚠️ Chọn nguồn **MCP** thì **BẮT BUỘC** đi nhánh MCP — đừng im lặng chạy import_jira API (sẽ trúng nguồn/domain khác → thiếu project, lỗi "không có note").
   - **`source_type: excel` (method `local_file`)** → `python3 "$T/excel-to-obsidian/import_excel.py" --file <entry.file_path> [--sheet <entry.sheet_name>] --source-id <entry.id> [--project <KEY>] [--map '<json nếu cột lạ>']`. Tự nhận cột Việt/Anh; ghi note `source: excel` vào `07_Imported/<id>/` (idempotent).
   - **`source_type: sheet`/`excel` (method `mcp`) — SharePoint 365, 2 cách:**
     **① MCP + CSV (không cần Graph token):** file để dạng **.csv** → `sharepoint_search fileType="csv"` → `read_resource` (trả **text CSV nguyên vẹn**) → Claude ghi `reports/_sheet-<id>.csv` → `python3 "$T/excel-to-obsidian/import_excel.py" --from-rows reports/_sheet-<id>.csv --map … --source-id <id>`. (read_resource đọc CSV CHUẨN; chỉ .xlsx mới lệch cột.)
     **② Graph cho .xlsx:** `sharepoint_search fileType="xlsx"` → URI `file:///{driveId}/{itemId}` → `import_excel.py --graph-item "<driveId>/<itemId>"` (Graph token creds `SHAREPOINT_*` app **Sites.Read.All** → `/content` → parse ô chuẩn). App-only Sites.Read.All chạy được cả nền.
     ⚠️ KHÔNG dùng read_resource lấy ô của .xlsx (text lệch cột). **Google Sheet**: Publish-CSV → `--from-url`.
   Quét xong HẾT các nguồn → reindex **1 lần** `build_index.py --root .`. **Report trên UNION (Jira + Excel) vừa kéo** (task đã Done/đổi trạng thái sẽ đúng).
   > ⚠️ Nhiều domain **trùng mã project/issue** → vault đè nhau (giới hạn đã biết). Khác mã thì gộp thoải mái.
5. (Tùy chọn) **filter member** (assignee / team) — multi-select. Hỏi **khoảng thời gian**.
5b. **VAI TRÒ thành viên (HỎI TÊN + ROLE để hiểu CONTEXT phân tích từng người — workflow 14 Bước 0.6):** AskUserQuestion
   (multi-select + ô **"Other"** gõ tên chưa có) gán **PM/PO** (CHỈ ĐIỀU PHỐI, tạo Epic/Request/US, **KHÔNG log task**
   → `reports.pm_members`) và **QC** (tạo Bug → `reports.qc_members`); còn lại **Dev**. Ghi inline list vào
   `config/factory-config.yaml` mục `reports:` (`pm_members: ["A","B"]` / `qc_members: ["C"]`). Đã có sẵn → chỉ hỏi
   "đúng chưa / thêm bớt". Để TRỐNG → build_report **tự nhận diện**. ⚠️ **PM KHÔNG đo bằng giờ-công, KHÔNG cảnh báo
   "chưa log giờ", loại khỏi capacity team** — chỉ đánh giá theo việc điều phối.
   > 👤 **HỎI RÕ "Ai là PM dự án?"** (1 người) — để AI phân tích theo góc PM + roadmap điều phối, query đúng người. Ghi vào `reports.pm_members` (đứng đầu).
5c. **HỎI: "Có phân tích ROADMAP không?"** — AskUserQuestion [Có / Không].
   - **Có** → báo cáo thêm mục **🗺️ Roadmap & điều phối sprint** (build_report đã sinh section roadmap: backlog/current/next + SP).
   - Nếu nhóm SharePoint có chọn **file OKR/Standing Meeting/chiến lược** → ĐỌC nội dung file đó (SharePoint: `read_resource`/`--from-url`;
     local: đọc trực tiếp/`workflow 02`) → lưu `reports/_okr-latest.txt` làm **BỐI CẢNH** cho AI roadmap (KHÔNG nạp thành task/note).
6. **BẮT BUỘC dựng báo cáo QUA `build_report.py` — TUYỆT ĐỐI KHÔNG tự viết file HTML báo cáo bằng tay.**
   `python3 "$T/progress-report/build_report.py" --projects "<KEYS>" --scope <SCOPE> --recent-days <NDAYS>`
   (per `workflows/14-progress-report.md`) → ra dashboard CHUẨN (có **banner**, đủ section: trạng thái · theo người ·
   complexity · **🗺️ Roadmap/Sprint** · capacity · rủi ro) + `email-body-latest.html`. MỌI nguồn (Jira/SharePoint/Excel)
   phải **import vào vault rồi build_report** — kể cả khi GỘP nhiều nguồn (đừng ghép HTML tay → mất banner + sai layout).
   > 📧 **Banner mail**: gửi qua `send_report.py` (tự nhúng `cid:kora-banner` từ `assets/banner-daily-report.jpg`) → Outlook hiện banner. Đừng bỏ qua send_report.
- Dashboard + email PHẢI có khối **🤖 AI analysis** (workflow 14 — Bước 1.5), CHI TIẾT + đủ bảng số liệu: health
  (🟢/🟡/🔴), **dự đoán trượt timeline mỗi sprint** (kèm lý do), phân tích từng thành viên, giải pháp rủi ro, tóm tắt điều hành;
  **+ (nếu chọn roadmap) mục 🗺️ Roadmap & điều phối sprint**: backlog/current/next, **bốc task nào vào sprint kế** + sắp xếp
  sprint hiện tại, gắn OKR/chiến lược (`reports/_okr-latest.txt`), theo góc **PM đã hỏi**. Viết từ DỮ LIỆU, không bịa →
  ghi `reports/ai-analysis-latest.md` → `build_report.py --inject-ai reports/ai-analysis-latest.md` (đưa vào CẢ email lẫn dashboard).
> 📧 **THÂN MAIL (BẮT BUỘC) = `reports/email-body-latest.html`** (bản tóm tắt CÓ BANNER + đủ section, do build_report sinh).
> **TUYỆT ĐỐI KHÔNG lấy `progress-report-latest.html` (dashboard/"processing") làm thân mail** — đó CHỈ là **file ĐÍNH KÈM**.
> Lấy nhầm dashboard làm thân mail = **mất banner + sai UI** (đúng lỗi đang gặp). Luôn: `--html-file reports/email-body-latest.html
> --attach reports/progress-report-latest.html`. Và **KHÔNG tự dán/chế nội dung mail** — chỉ gửi đúng file email-body qua `send_report.py`.
- **Sau khi sinh report → đề xuất bước kế (AskUserQuestion, schema rule #8 — header ≤12 ký tự vd "Bước kế"):
  [Gửi mail ngay] / [Đặt lịch hằng ngày] / [Dừng].**
  - **[Gửi mail ngay]** → đi luồng GỬI của `/claude-knowledge-send-mail` ([Gửi ngay]): cổng `KORA_OPS_PW` → chọn người nhận
    (`reports.email.to`) → **tự dùng Gmail SMTP nếu đã setup** → gửi. **Cowork chặn SMTP → ưu tiên MCP `run_command`
    (local-terminal) GỬI THẲNG nếu có; không có → BÀN GIAO bash cho terminal** (xem claude-knowledge-send-mail "ƯU TIÊN/BÀN GIAO"): KHÔNG dead-end.
  - **[Đặt lịch hằng ngày]** → tạo **Cowork scheduled task qua `/schedule`** (theo `workflows/08-schedule-sync.md`
    Mục B) chạy mỗi ngày: **kéo dữ liệu → sinh report → tự gửi email** tới `reports.email.to` (gửi mail qua cổng `send_report.py --check`).
