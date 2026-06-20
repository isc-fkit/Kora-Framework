---
description: Configure the INCIDENT alert email — recipients + on/off for the issue-ticket mail that scheduled (background) flows send when a run fails. Editing here OVERRIDES all running schedules (read at run time, no need to recreate any schedule). Also sets where incident tickets go (Confluence/Jira/none). Different from /kora-send-mail (which sends the progress report).
---

The user invoked `/kora-alert-mail` — cấu hình **EMAIL CẢNH BÁO SỰ CỐ (issue ticket)** của lịch nền.

> 🎯 Đây là mail orchestrator **tự gửi khi một lịch nền LỖI** (scan/get · post · report · mail · sync thất
> bại) — kèm việc tạo **ticket issue**. KHÁC `/kora-send-mail` (mail BÁO CÁO tiến độ) và `reports.email`.
> ⭐ **Sửa ở đây = OVERRIDE cho TẤT CẢ lịch đang chạy.** Orchestrator đọc `config/factory-config.yaml`
> **lúc chạy** nên KHÔNG cần tạo lại lịch nào — lần chạy kế của MỌI lịch tự dùng người nhận/thiết lập mới.

### Bước 1 — Đọc & trình bày cấu hình hiện tại
Đọc từ `config/factory-config.yaml`:
- `scheduler.error_recipients` — người nhận mail sự cố (**override toàn cục**).
- `scheduler.error_email.enabled` — bật/tắt gửi mail sự cố (mặc định **bật**).
- `scheduler.ticket_issue.{enabled, target, space_key, jira_project}` — nơi tạo ticket (Confluence / Jira / none).

Tóm tắt cho user bằng lời thường: *đang gửi cho ai · bật hay tắt · ticket đi đâu*. Nếu `error_recipients`
rỗng → nói rõ: hiện đang dùng người nhận của **từng lịch** (fallback `reports.email.to`).

### Bước 2 — Chọn việc cần chỉnh (AskUserQuestion, `multiSelect: true`)
**[Sửa người nhận (override)]** · **[Bật/Tắt gửi mail sự cố]** · **[Đổi nơi tạo ticket]** · **[Gửi thử kiểm tra SMTP]**

### Bước 3 — Người nhận (override toàn cục)
- Hiện danh sách `scheduler.error_recipients`. AskUserQuestion **thêm** (ô **"Other"** gõ email mới) /
  **xóa** (chọn email đang có) — lặp tới khi hài lòng. Gợi ý nhanh: chào các email trong `reports.email.recipients`
  (danh bạ) để chọn lại.
- ✋ **Đọc lại danh sách cuối cho user xác nhận** (mail = hành động ra ngoài).
- Ghi **INLINE list** (bắt buộc — để orchestrator đọc được): `error_recipients: [a@x.com, b@y.com]`.
- **Để TRỐNG (`[]`)** = tắt override → mỗi lịch dùng người nhận của nó, cuối cùng fallback `reports.email.to`.

### Bước 4 — Bật / Tắt gửi mail sự cố
AskUserQuestion **[Bật]** / **[Tắt]** → ghi `scheduler.error_email.enabled: true|false`.
Tắt = lịch lỗi **vẫn TẠO ticket** (nếu `ticket_issue.enabled`) nhưng **KHÔNG gửi mail**.

### Bước 5 — Nơi tạo ticket (tùy chọn)
AskUserQuestion **[Confluence]** / **[Jira]** / **[Không tạo ticket]**:
- **Confluence** → hỏi `space_key` (ô "Other") → ghi `ticket_issue.enabled: true`, `target: confluence`, `space_key`.
- **Jira** → hỏi `jira_project` (ô "Other") → ghi `target: jira`, `jira_project`.
- **Không** → ghi `ticket_issue.enabled: false`.

### Bước 6 — Gửi thử kiểm tra SMTP (tùy chọn)
`python3 tools/report-mailer/send_report.py --check` (Windows `py`) — chỉ thử đăng nhập SMTP, **KHÔNG gửi**.
Lỗi → nhắc cấu hình `tools/report-mailer/.env.local` (copy `.env.local.example`, điền `SMTP_USER` + Google App
Password). **Bí mật CHỈ ở `.env.local`** — KHÔNG hỏi/nhập password qua chat/card.

### Sau khi ghi
Báo user: *"Đã cập nhật — áp dụng cho MỌI lịch nền từ lần chạy kế (không cần tạo lại lịch nào)."* Rồi đề xuất
bước kế (AskUserQuestion): **[Xem/sửa lịch — `/kora-schedule`]** · **[Gửi thử cảnh báo]** · **[Dừng]**.

> 📌 **Override & runtime:** `scheduler.error_recipients` (khi != rỗng) **đè** người nhận của TỪNG lịch cho mail
> sự cố; thứ tự: **override → người nhận của lịch → `reports.email.to`**. Lịch nền đọc config lúc chạy → áp
> NGAY cho mọi lịch, KHÔNG cần tạo lại.
> 🔒 **Không cần cổng `KORA_OPS_PW`:** skill này chỉ **SỬA config** (không gửi gì). Việc GỬI mail sự cố nằm
> TRONG lượt lịch nền — đã qua cổng `KORA_OPS_PW`. (Lịch nền chỉ gửi được **SMTP**.)
> Windows: `python3` → `py`. Gói USER (`.kora-user`) vẫn cấu hình được (lịch get&post của user cũng cảnh báo lỗi).
