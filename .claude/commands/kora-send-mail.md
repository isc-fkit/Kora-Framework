---
description: Send a progress-report email to chosen recipients — now or on a schedule. PRIORITIZES automatic SMTP send (Gmail via App Password), not manual drafts. Scans the chosen Jira project for latest data, builds the report (banner + cards + charts), then sends. Password-gated (operations password); only this gated entry can send mail.
---

The user invoked `/kora-send-mail` — gửi email báo cáo tiến độ. **CÓ CỔNG MẬT KHẨU vận hành
(`KORA_OPS_PW`)** — phải qua cổng mới vào được phần này.

**Luồng (đúng thứ tự — chọn nguồn → người nhận → gửi):**
1. **Chọn nguồn Jira đã kết nối:** đọc `connections:` (source_type ∈ `jira_cloud`/`jira_server`) →
   AskUserQuestion liệt kê **các Jira ĐÃ kết nối** (kèm trạng thái ✓). Chọn Jira cần report.
   (Chưa có Jira nào → mời chạy `/kora-connect` trước.)
2. **Chọn project trong Jira đó:** lấy danh sách project của Jira đã chọn (API `/rest/api/2/project`
   hoặc MCP `getVisibleJiraProjects`) → AskUserQuestion **multi-select project cần report** (+ **[Chọn tất cả]**).
3. **Chọn người nhận (mail gửi đến):** danh bạ `reports.email.to` (multi-select) + **[+ Thêm mới]**
   (ô "Other" → gõ địa chỉ → **lưu vào `reports.email.to`**). Đây là nguồn người nhận DUY NHẤT mà lịch/task đọc.
4. **Gửi ngay hay đặt lịch:** AskUserQuestion **[Gửi ngay] / [Đặt lịch]**.
   - **[Gửi ngay]:**
     a. **CỔNG MẬT KHẨU vận hành `KORA_OPS_PW`** → `python3 tools/archive-gate/verify_ops_password.py`
        (đọc env **HOẶC** `~/.config/kora/ops-pw.env` — đặt 1 lần bằng `/kora-ops-password`; **KHÔNG hỏi qua card, KHÔNG in**). Exit ≠ 0 → **DỪNG**.
     b. **Kênh gửi — ƯU TIÊN TỰ ĐỘNG GỬI:** AskUserQuestion **[Gửi tự động (SMTP / Gmail App Password) — khuyến nghị]**
        / **[Tạo nháp gửi tay (MCP)]**. Gmail **dùng App Password qua SMTP** = auto-send (KHÔNG phải draft). Mặc định auto.
     c. **QUÉT lấy DỮ LIỆU MỚI NHẤT của (các) project đã chọn (BẮT BUỘC, trước report):** `import_jira.py --since`
        (đặt `PROJECT_KEYS=<KEYS>`) hoặc MCP `searchJiraIssuesUsingJql` `project=<KEY> AND updated>="<since>"` →
        `import_jira.py --from-mcp` → reindex `build_index.py --root .` →
        `python3 tools/progress-report/build_report.py --projects "<KEYS>"` (report scope ĐÚNG project vừa quét).
     d. **GỬI TỰ ĐỘNG (mặc định, kể cả Gmail):** kiểm `tools/report-mailer/.env.local` có `SMTP_USER`+`SMTP_PASS`.
        - **Chưa có** → hướng dẫn tạo **Gmail App Password** (bật 2FA → `myaccount.google.com/apppasswords`), điền
          `tools/report-mailer/.env.local`: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER=<email>`,
          `SMTP_PASS=<app password 16 ký tự>` (KHÔNG dùng mật khẩu Gmail thường) → `send_report.py --check`. Token chỉ ở `.env.local`.
        - ✋ confirm → `python3 tools/report-mailer/send_report.py --to "<list>" --subject "<chủ đề>" --html-file
          reports/email-body-latest.html --no-attach-html --attach reports/progress-report-latest.html` → **GỬI THẲNG**
          (body = banner `cid` + phân tầng dự án; dashboard đính kèm). Báo "đã gửi tới <list>".
        - **[Tạo nháp] = FALLBACK** (chỉ khi user chọn / không gửi SMTP được): tạo NHÁP Gmail/Outlook qua MCP → user bấm gửi.
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
