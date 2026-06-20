# Workflow 15 — Archive bàn giao có PHÂN QUYỀN + mật khẩu

> Trigger: "archive", "đóng gói bàn giao", "handover", "đóng gói cho user dùng" (confirm trước).
> Khác `workflows/11-export-import.md` (sao lưu thuần, không cổng): luồng này có **cổng mật khẩu**,
> ship **key READ-ONLY** cloud-KB, và đánh dấu gói **HOST** hay **USER**.

## A. HOST tạo archive

1. **Cổng mật khẩu (bắt buộc).** Mật khẩu: `isc-fkit-kora` (chủ repo đổi được — hash trên nhánh
   release `config/archive-pw.sha256`). **KHÔNG hỏi mật khẩu qua card.** Đặt vào biến môi trường
   `KORA_ARCHIVE_PW` rồi để script tự kiểm (`tools/archive-gate/verify_password.py`). Sai → dừng.

2. **Hỏi (AskUserQuestion):**
   - **Loại gói:** **[USER]** (tắt report/mail, tự lên lịch get&post) / **[HOST]** (đầy đủ).
   - **Quyền:** **[read-only]** (chỉ GET KB chung) / **[read-write]** (được POST). read-write chỉ cấp
     cho người có nhiệm vụ đẩy — tránh rác dữ liệu.

3. **Key READ-ONLY (cho gói USER):** lấy bộ key đọc cloud-KB CHUNG (token Confluence read-only,
   scope theo space) — **KHÔNG dùng token cá nhân/write của host**. Truyền qua biến môi trường:
   `KORA_CLOUD_READ_BASE_URL`, `KORA_CLOUD_READ_USER`, `KORA_CLOUD_READ_TOKEN`, `KORA_CLOUD_SPACE`.
   (Token chỉ đi qua env → file `.env.local` trong gói; KHÔNG vào chat/manifest/git.)

3b. **Email TICKET SỰ CỐ cho gói USER (áp dụng sẵn).** Cấu hình `scheduler.error_recipients` (NGƯỜI PHỤ TRÁCH)
   + `scheduler.ticket_issue` trong `config/factory-config.yaml` **đi theo gói** (nằm trong DATA). ⇒ Khi lịch nền
   của USER **lỗi**, orchestrator tạo ticket + **gửi email cho người phụ trách này** (cùng cấu hình HOST đặt qua
   `/kora-alert-mail` hoặc `/kora-schedule` Bước 3B §5). TRƯỚC khi đóng gói:
   - Hỏi/确认 `scheduler.error_recipients` = email người phụ trách (HOST). `error_email.enabled: true`.
   - **Kênh GỬI cho USER (bắt buộc nếu muốn USER báo lỗi được):** gói chỉ có key Confluence READ → KHÔNG tự tạo
     ticket (cần write) / KHÔNG có SMTP. Chọn 1 kênh và ship qua env (như key READ):
     • **SMTP no-reply** → ship `tools/report-mailer/.env.local` (cred gửi 1 chiều, KHÔNG phải mail cá nhân host); hoặc
     • **Token WRITE tới space "incidents"** riêng (`scheduler.ticket_issue.target: confluence` + space đó).
     Không ship kênh nào → USER chỉ GHI LOG lỗi cục bộ (không báo ra ngoài) — báo rõ cho user.

4. ✋ **Confirm → chạy** `scripts/archive-kb.command` (Windows `scripts\archive-kb.bat`) với các biến
   trên. Tạo `kora-archive-<project>-<date>.zip` = thư mục `kora-archive/` {manifest, data/, .env.local
   (chỉ key READ), markers/package.type}. **AN TOÀN:** script loại mọi `.env` token write/mail/jira
   khỏi `data/` — chỉ ship 1 `.env.local` read-only.

5. Gửi file zip cho user (kèm đường dẫn tuyệt đối để copy). Key **WRITE** (nếu user được quyền push)
   cấp NGOÀI luồng (env `KORA_CLOUD_WRITE_*` hoặc `/kora-connect`), KHÔNG bỏ vào gói.

## B. NGƯỜI NHẬN import (máy base sạch)

1. Chép zip vào gốc repo → chạy `scripts/import-kb.command` (Windows `scripts\import-kb.bat`).
   Script nhận diện gói archive, bung `data/`, đặt **key READ** vào `tools/confluence-sync/.env.local`,
   tạo marker `.kora-user` nếu là gói USER, dựng lại index.

2. **Sau import (Claude làm, có Approval Gate):**
   - **Cấu hình:** đặt `package.type: user`, `package.permission: <từ manifest>`, `reports.email.enabled: false`,
     `cloud_kb.enabled: true`, `cloud_kb.sync.enabled: true` (+ `mode: pull` nếu read-only, `pull-push` nếu read-write).
   - **Tự lên LỊCH get&post** (gói USER có sẵn ý định sync): tạo lịch HĐH
     `schedule.py register --id cloud-sync --cron "0 8 * * *" --scan confluence:<space> --post confluence:<space>`
     (read-only → chỉ `--scan`, bỏ `--post`). ✋ confirm trước khi tạo.
   - **TẮT report/mail:** vì có `.kora-user`, các luồng báo cáo/gửi mail (WF14, WF08 Mục B, `/kora-daily-report`)
     tự chặn với thông báo "chỉ HOST".

> Quyền là CAPABILITY, không phải cờ: gói read-only **không có token write** → server Confluence từ
> chối POST. Marker/flag chỉ là UX. Mật khẩu `isc-fkit-kora` chỉ gác *việc tạo archive*, không bảo vệ dữ liệu.
