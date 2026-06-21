---
description: Generate a progress report. Choose one or more projects (multi-select), filter by members, pull data for a chosen time range from the sources, then build the dashboard. Password-gated (operations password) since it pulls live data.
---

The user invoked `/kora-daily-report` — build a progress report.

> 🚫 **Guard gói USER:** nếu có file `.kora-user` ở gốc project (hoặc `package.type: user` trong config)
> → đây là máy NGƯỜI DÙNG, KHÔNG có báo cáo/gửi mail (chỉ HOST mới có). Báo nhẹ: *"Báo cáo & gửi mail
> chỉ chạy ở máy HOST. Máy này chỉ đồng bộ KB chung (get & post)."* rồi DỪNG, KHÔNG sinh report.

**Chọn NGUỒN → PROJECT (chi tiết, AskUserQuestion).** Resolve path tool (bản cài ở CORE):
`T=tools; [ -e "$T/connections/check_connection.py" ] || T="$HOME/.claude/kora-framework/tools"`.
1. 🔒 **CỔNG MẬT KHẨU vận hành (`KORA_OPS_PW`)** TRƯỚC — báo cáo kéo dữ liệu live nên PHẢI qua cổng:
   `python3 "$T/archive-gate/verify_ops_password.py"` (đọc env **HOẶC** `~/.config/kora/ops-pw.env` — đặt 1 lần bằng
   `/kora-ops-password`; **KHÔNG hỏi qua card, KHÔNG in**). Exit ≠ 0 → **DỪNG**, không kéo, không sinh report.
2. **Chọn NGUỒN Jira (CÓ THỂ NHIỀU)** từ `connections:`: `python3 "$T/connections/check_connection.py" --list --json
   --config "$PWD/config/factory-config.yaml"` → lọc entry **Jira-capable**: `source_type ∈ {jira_server, jira_cloud,
   atlassian}` (**`atlassian` = Atlassian Rovo CÓ Jira**). AskUserQuestion **multi-select** — hiện kèm `method` (API/MCP)
   + `base_url` (phân biệt nhiều domain) — cho chọn **1 HOẶC NHIỀU** nguồn (lẫn API + MCP, nhiều domain đều được). Không
   nguồn Jira nào → mời `/kora-connect`.
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
   Quét xong HẾT các nguồn → reindex **1 lần** `build_index.py --root .`. **Report trên UNION project vừa kéo** (task đã Done/đổi trạng thái sẽ đúng).
   > ⚠️ Nhiều domain **trùng mã project/issue** → vault đè nhau (giới hạn đã biết). Khác mã thì gộp thoải mái.
5. (Tùy chọn) **filter member** (assignee / team) — multi-select. Hỏi **khoảng thời gian**.
6. Build dashboard **scope đúng project + phạm vi**: `python3 "$T/progress-report/build_report.py" --projects "<KEYS>"`
   **`--scope <SCOPE> --recent-days <NDAYS>`** (nếu SCOPE≠all — lọc sprint active / N ngày) per
   `workflows/14-progress-report.md` — inline Cowork UI + HTML. Báo cáo hiện **nhãn phạm vi** (vd "Sprint đang chạy").
- The dashboard MUST include an **🤖 AI analysis** block (workflow 14 — Bước 1.5): issue health
  classification (🟢/🟡/🔴), **timeline-slip prediction per active sprint** (with reasoning),
  per-member recommendations, risk-resolution suggestions, and a 1–2 sentence executive summary —
  written by Claude from the data, never made up.
- **Sau khi sinh report → đề xuất (AskUserQuestion): "Đặt lịch tự động hằng ngày?"** Nếu **Có** → tạo một
  **Cowork scheduled task qua `/schedule` của Claude** (theo `workflows/08-schedule-sync.md` Mục B) chạy mỗi ngày:
  **kéo dữ liệu → sinh report → tự gửi email** tới `reports.email.to` (bật gửi mail cần qua cổng `send_report.py --check`).
