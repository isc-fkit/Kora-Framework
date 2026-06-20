---
description: Send a progress-report email to chosen recipients via Gmail/Outlook/SMTP — now or on a schedule. Scans the chosen Jira, builds the report, then sends. Password-gated (operations password); only this gated entry can send mail.
---

The user invoked `/kora-send-mail` — gửi email báo cáo tiến độ. **CÓ CỔNG MẬT KHẨU vận hành
(`KORA_OPS_PW`)** — phải qua cổng mới vào được phần này.

**Luồng (đúng thứ tự — chọn nguồn → người nhận → gửi):**
1. **Chọn nguồn Jira đã kết nối:** đọc `connections:` (source_type ∈ `jira_cloud`/`jira_server`) →
   AskUserQuestion liệt kê **các Jira ĐÃ kết nối** (kèm trạng thái ✓). Chọn Jira cần report.
   (Chưa có Jira nào → mời chạy `/kora-connect` trước.)
2. **Chọn project trong Jira đó:** lấy danh sách project của Jira đã chọn (API `/rest/api/2/project`
   hoặc MCP `getVisibleJiraProjects`) → AskUserQuestion **multi-select project cần report** (+ **[Chọn tất cả]**).
3. **Chọn người nhận (mail gửi đến):** danh bạ `reports.email.recipients` (multi-select) + **[+ Thêm mới]**
   (ô "Other" → gõ địa chỉ → **lưu vào `reports.email.recipients`**).
4. **Gửi ngay hay đặt lịch:** AskUserQuestion **[Gửi ngay] / [Đặt lịch]**.
   - **[Gửi ngay]:**
     a. **CỔNG MẬT KHẨU vận hành `KORA_OPS_PW`** → `python3 tools/archive-gate/verify_ops_password.py`
        (env — **KHÔNG hỏi qua card, KHÔNG in**). Exit ≠ 0 → **DỪNG**.
     b. **Provider:** AskUserQuestion **[Gmail] / [Outlook] / [SMTP]** (theo `connections:`).
     c. Quét Jira đã chọn (`import_jira.py --since` hoặc MCP) → `python3 tools/progress-report/build_report.py`.
     d. **SMTP:** ✋ confirm → `python3 tools/report-mailer/send_report.py --to "<list>" --html-file reports/email-body-latest.html --no-attach-html --attach reports/progress-report-latest.html`
        (body = email có **banner** + phân tầng dự án; dashboard đính kèm riêng). **Gmail/Outlook:** tạo **NHÁP** qua MCP → user gửi.
   - **[Đặt lịch]:**
     a. **Provider** (lịch NỀN chỉ gửi **SMTP**).
     b. **Mốc giờ** — AskUserQuestion **multi-select** gợi ý `08:00 / 12:00 / 14:00 / 17:00` + ô **"Other"**
        (HH:MM tùy chỉnh). Cho chọn **NHIỀU mốc** (các mốc phải cùng số phút; khác phút → tạo lịch riêng).
     c. **Tần suất** — AskUserQuestion **[Mỗi ngày] / [Thứ 2–6] / [Ngày tùy chọn]**.
     d. ✋ confirm (đọc lại "gửi lúc nào, cho ai") → đăng ký bằng **`--times/--days`** (KORA tự dựng cron):
        `python3 tools/kora-scheduler/schedule.py register --id <slug> --times "08:00,14:00" --days mon-fri
        --scan <jira-id> --report-projects "<KEYS>" --mail-provider smtp --email "<list>"` (`post_list` rỗng).
        (`--days`: `every` = mỗi ngày · `mon-fri` = thứ 2–6 · hoặc csv `mon,wed,fri`. Power-user vẫn dùng được `--cron`.)
     e. → **Task xuất hiện trong danh sách `/kora-schedule`** — quản lý tại đó: **Bật/Tắt (active/inactive)**
        (`schedule.py enable|disable --id <slug>`) hoặc **Xóa** (`remove`). Nếu in `⚠️CHƯA-CÀI-HĐH` →
        lịch đã LƯU nhưng chưa cài được vào HĐH (enabled=false); thử `enable` lại hoặc dùng cơ chế **Cowork** làm fallback.

Chỉ quét Jira tới bước **tạo report + gửi mail** (KHÔNG sync KB). Token/secret chỉ ở `.env.local`.
Windows: `python3` → `py`. Gói USER (`.kora-user`) → report/mail bị TẮT → chặn tại đây.
