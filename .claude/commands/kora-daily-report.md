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
2. **Chọn NGUỒN** từ `connections:` (không đoán mò): `python3 "$T/connections/check_connection.py" --list
   --config "$PWD/config/factory-config.yaml"` → AskUserQuestion chọn 1 nguồn (vd `jira_cloud__mcp`, `jira_server__api`).
   Chưa kết nối → mời `/kora-connect`.
3. **Chọn PROJECT TRONG nguồn đó** — Jira: `python3 "$T/jira-to-obsidian/import_jira.py" --list-projects` (JSON
   `[{key,name}]`) → **multi-select + [Tất cả]**. (SharePoint MCP: chọn folder/path qua `sharepoint_folder_search`.)
4. **QUÉT LẤY DỮ LIỆU MỚI NHẤT (BẮT BUỘC) cho project đã chọn** — theo `workflows/14-progress-report.md` Bước 0.5:
   Jira Cloud → MCP `searchJiraIssuesUsingJql` `project=<KEY> AND updated>="<since>"` → `import_jira.py --from-mcp`;
   self-host → `import_jira.py --since` (PROJECT_KEYS=<KEYS>). Rồi reindex `build_index.py --root .`. **Report luôn trên data vừa kéo.**
5. (Tùy chọn) **filter member** (assignee / team) — multi-select. Hỏi **khoảng thời gian**.
6. Build dashboard **scope đúng project**: `python3 "$T/progress-report/build_report.py" --projects "<KEYS>"`
   (time-tracking / active sprint / assignee + **by-project bar**) per `workflows/14-progress-report.md` — inline Cowork UI + HTML.
- The dashboard MUST include an **🤖 AI analysis** block (workflow 14 — Bước 1.5): issue health
  classification (🟢/🟡/🔴), **timeline-slip prediction per active sprint** (with reasoning),
  per-member recommendations, risk-resolution suggestions, and a 1–2 sentence executive summary —
  written by Claude from the data, never made up.
- **Sau khi sinh report → đề xuất (AskUserQuestion): "Đặt lịch tự động hằng ngày?"** Nếu **Có** → tạo một
  **Cowork scheduled task qua `/schedule` của Claude** (theo `workflows/08-schedule-sync.md` Mục B) chạy mỗi ngày:
  **kéo dữ liệu → sinh report → tự gửi email** tới `reports.email.to` (bật gửi mail cần qua cổng `send_report.py --check`).
