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
2. **HỎI CHỌN NGUỒN báo cáo (CÓ THỂ NHIỀU) — LIỆT KÊ ĐỦ Jira + Excel/Sheet** từ `connections:`:
   `python3 "$T/connections/check_connection.py" --list --json --config "$PWD/config/factory-config.yaml"` → lọc entry
   **báo-cáo-được**: Jira (`source_type ∈ {jira_server, jira_cloud, atlassian}`) **+ Excel/Sheet**
   (`source_type ∈ {excel, sheet}`, method `local_file`/`mcp`). **AskUserQuestion multi-select**, mỗi mục nhãn rõ
   để chọn ĐÚNG: vd `[Jira·MCP] foxproject`, `[Jira·API] jira.fptmedicare.vn`, `[Sheet·MCP] Kế hoạch Q2 (Google)`,
   `[Excel·Local] data/ke-hoach.xlsx` + **[Tất cả nguồn]** (>4 → phân trang). 1 nguồn duy nhất → khỏi hỏi. Không
   nguồn nào → mời `/claude-knowledge-connect`. **Đây là bước BẮT BUỘC HỎI** (user phải chọn đúng nguồn).
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
   - **`source_type: sheet`/`excel` (method `mcp`)** → **Claude LẤY DÒNG qua connector** (Google Sheets / SharePoint / M365 đã connected trong Cowork) → ghi tạm `reports/_sheet-<id>.csv` (hoặc .json list[dict], header dòng đầu) → `python3 "$T/excel-to-obsidian/import_excel.py" --from-rows reports/_sheet-<id>.csv --source-id <id> [--project <KEY>] [--map …]`. (MCP-connector không đọc được ô .xlsx → Claude lấy/chuẩn hoá thành rows; **chỉ TƯƠNG TÁC**, không chạy nền.)
   Quét xong HẾT các nguồn → reindex **1 lần** `build_index.py --root .`. **Report trên UNION (Jira + Excel) vừa kéo** (task đã Done/đổi trạng thái sẽ đúng).
   > ⚠️ Nhiều domain **trùng mã project/issue** → vault đè nhau (giới hạn đã biết). Khác mã thì gộp thoải mái.
5. (Tùy chọn) **filter member** (assignee / team) — multi-select. Hỏi **khoảng thời gian**.
5b. **VAI TRÒ thành viên (HỎI TÊN + ROLE để hiểu CONTEXT phân tích từng người — workflow 14 Bước 0.6):** AskUserQuestion
   (multi-select + ô **"Other"** gõ tên chưa có) gán **PM/PO** (CHỈ ĐIỀU PHỐI, tạo Epic/Request/US, **KHÔNG log task**
   → `reports.pm_members`) và **QC** (tạo Bug → `reports.qc_members`); còn lại **Dev**. Ghi inline list vào
   `config/factory-config.yaml` mục `reports:` (`pm_members: ["A","B"]` / `qc_members: ["C"]`). Đã có sẵn → chỉ hỏi
   "đúng chưa / thêm bớt". Để TRỐNG → build_report **tự nhận diện**. ⚠️ **PM KHÔNG đo bằng giờ-công, KHÔNG cảnh báo
   "chưa log giờ", loại khỏi capacity team** — chỉ đánh giá theo việc điều phối.
6. Build dashboard **scope đúng project + phạm vi**: `python3 "$T/progress-report/build_report.py" --projects "<KEYS>"`
   **`--scope <SCOPE> --recent-days <NDAYS>`** (nếu SCOPE≠all — lọc sprint active / N ngày) per
   `workflows/14-progress-report.md` — inline Cowork UI + HTML. Báo cáo hiện **nhãn phạm vi** (vd "Sprint đang chạy").
- The dashboard MUST include an **🤖 AI analysis** block (workflow 14 — Bước 1.5): hạng mục công việc health
  classification (🟢/🟡/🔴), **timeline-slip prediction per active sprint** (with reasoning),
  per-member recommendations, risk-resolution suggestions, and a 1–2 sentence executive summary —
  written by Claude from the data, never made up.
- **Sau khi sinh report → đề xuất bước kế (AskUserQuestion, schema rule #8 — header ≤12 ký tự vd "Bước kế"):
  [Gửi mail ngay] / [Đặt lịch hằng ngày] / [Dừng].**
  - **[Gửi mail ngay]** → đi luồng GỬI của `/claude-knowledge-send-mail` ([Gửi ngay]): cổng `KORA_OPS_PW` → chọn người nhận
    (`reports.email.to`) → **tự dùng Gmail SMTP nếu đã setup** → gửi. **Cowork chặn SMTP → ưu tiên MCP `run_command`
    (local-terminal) GỬI THẲNG nếu có; không có → BÀN GIAO bash cho terminal** (xem claude-knowledge-send-mail "ƯU TIÊN/BÀN GIAO"): KHÔNG dead-end.
  - **[Đặt lịch hằng ngày]** → tạo **Cowork scheduled task qua `/schedule`** (theo `workflows/08-schedule-sync.md`
    Mục B) chạy mỗi ngày: **kéo dữ liệu → sinh report → tự gửi email** tới `reports.email.to` (gửi mail qua cổng `send_report.py --check`).
