---
description: Generate a progress report. Choose one or more projects (multi-select), filter by members, pull data for a chosen time range from the sources, then build the dashboard. Password-gated (operations password) since it pulls live data.
---

The user invoked `/kora-daily-report` — build a progress report.

> 🚫 **Guard gói USER:** nếu có file `.kora-user` ở gốc project (hoặc `package.type: user` trong config)
> → đây là máy NGƯỜI DÙNG, KHÔNG có báo cáo/gửi mail (chỉ HOST mới có). Báo nhẹ: *"Báo cáo & gửi mail
> chỉ chạy ở máy HOST. Máy này chỉ đồng bộ KB chung (get & post)."* rồi DỪNG, KHÔNG sinh report.

**Project selection (AskUserQuestion):**
1. If any project was scanned before → first offer **[Pick from already-scanned projects]** /
   **[Add a new project]**.
   - **Pick from already-scanned** → show the already-imported projects as a **multi-select
     checklist** (read the list from the vault / `config/factory-config.yaml`); the user ticks
     one or more.
   - **Add a new project** → ask the new project key/name; if not yet imported, scan it first
     (`/kora-scan`).
2. Always allow choosing **multiple projects** (AskUserQuestion with `multiSelect: true`).

**Then:**
- Offer **filters by project and by member** (assignee / team) — multi-select.
- 🔒 **CỔNG MẬT KHẨU vận hành (`KORA_OPS_PW`)** — báo cáo kéo dữ liệu live từ nguồn nên PHẢI qua cổng:
  `python3 tools/archive-gate/verify_ops_password.py` (đọc env `KORA_OPS_PW` — **KHÔNG hỏi qua card, KHÔNG in**;
  Windows `py`). Exit ≠ 0 → **DỪNG**, KHÔNG kéo dữ liệu, KHÔNG sinh report. (Cùng cổng với `/kora-sync`,
  `/kora-send-mail`, lịch nền — KHÁC mật khẩu archive. `/kora-export*` không dùng cổng này.)
- Ask the **time range**, then pull data for that period from the configured sources
  (Jira via API/MCP, SharePoint via MCP).
- If no connection configured yet → ask **MCP / API / All** here (not at init).
- Build the dashboard (time-tracking / active sprint / assignee + **by-project bar**) per
  `workflows/14-progress-report.md` — inline Cowork UI + an HTML file.
- The dashboard MUST include an **🤖 AI analysis** block (workflow 14 — Bước 1.5): issue health
  classification (🟢/🟡/🔴), **timeline-slip prediction per active sprint** (with reasoning),
  per-member recommendations, risk-resolution suggestions, and a 1–2 sentence executive summary —
  written by Claude from the data, never made up.
- **Sau khi sinh report → đề xuất (AskUserQuestion): "Đặt lịch tự động hằng ngày?"** Nếu **Có** → tạo một
  **Cowork scheduled task qua `/schedule` của Claude** (theo `workflows/08-schedule-sync.md` Mục B) chạy mỗi ngày:
  **kéo dữ liệu → sinh report → tự gửi email** tới `reports.email.to` (bật gửi mail cần qua cổng `send_report.py --check`).
