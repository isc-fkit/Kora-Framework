---
description: Schedule automatic get→report→mail and optional KB sync (Confluence/GitHub) at the OS level so it runs even when the app is closed. List shows existing schedules with report/mail/sync; create, edit, or cancel. The sync step is password-gated (operations password).
---

The user invoked `/kora-schedule`. Follow `workflows/08-schedule-sync.md` for full detail.

### Bước 1 — Cơ chế lịch (AskUserQuestion)
- **[Máy — chạy cả khi ĐÓNG app] (khuyến nghị)** → lịch cấp HĐH (launchd/cron/schtasks) qua
  `tools/kora-scheduler/schedule.py`. Job là orchestrator Python thuần (scan → đẩy Confluence →
  report → mail → lỗi thì tạo ticket). Chạy đúng giờ kể cả khi app đóng.
- **[Cowork — chạy khi MỞ app]** → `mcp__scheduled-tasks__create_scheduled_task` (chạy bù khi mở app;
  có sẵn MCP connector). Đơn giản nhưng KHÔNG chạy khi đóng app.

### Bước 2 — Hành động (AskUserQuestion): **[Liệt kê & quản lý]** / **[Tạo mới]**
- **Liệt kê & quản lý** → hợp nhất 2 nguồn: `python3 tools/kora-scheduler/schedule.py list` (lịch HĐH)
  **và** `mcp__scheduled-tasks__list_scheduled_tasks` (Cowork), gắn nhãn engine + cột **ENABLED
  (active / inactive)**. Với MỖI task (lịch HĐH) → AskUserQuestion quản lý:
  - **[▶️ Bật — active]** → `schedule.py enable --id <id>` (cài lại artifact OS từ cron đã lưu).
  - **[⏸️ Tắt — inactive]** → `schedule.py disable --id <id>` (gỡ artifact OS nhưng **GIỮ trong danh sách**;
    orchestrator cũng tự bỏ qua nếu `enabled:false`).
  - **[🗑️ Xóa]** → `schedule.py remove --id <id>` (✋ confirm).
  - **[✏️ Sửa]** → sang Bước 3.
  (Cowork: bật/tắt/xóa bằng panel app — MCP không có hàm enable/disable/delete.)
- **Tạo mới** → sang Bước 3.

### Bước 3 — Tạo / sửa (khi chọn ở Bước 2)
> **Luồng lịch khi chạy:** **CỔNG MẬT KHẨU (`KORA_OPS_PW`)** gác CẢ lượt → (sai/thiếu → DỪNG TOÀN BỘ,
> KỂ CẢ auto-get; chỉ cảnh báo) → auto-get nguồn đã chọn → report từ project đã chọn → gửi mail →
> (tùy chọn) **SYNC** KB lên target.
1. **Nguồn để GET** — chọn scan-list từ `connections:` (multi-select, có **[Chọn tất cả]**), giống `/kora-scan`.
2. **Báo cáo** — chọn **project Jira** để tạo report (`--report-projects`, multi-select; rỗng = tất cả).
   (Chỉ HOST — gói `user` (`.kora-user`) KHÔNG có report/mail.)
3. **Gửi mail** — hiện gmail/outlook đã kết nối → chọn **provider** (`--mail-provider`); người nhận lấy từ
   `reports.email.recipients` (multi-select) hoặc **[+ Thêm mới]** (lưu lại). Lịch NỀN chỉ gửi được **SMTP**.
4. **Sync (tùy chọn — CÓ CỔNG MẬT KHẨU)** — hỏi có đẩy KB lên target (`--sync-targets confluence,github`).
   ⚠️ Cổng `KORA_OPS_PW` **gác CẢ lượt** (orchestrator gọi `verify_ops_password.py` ngay đầu): sai/thiếu →
   **bỏ qua TOÀN BỘ — kể cả auto-get/scan**, post, report, mail, sync (chỉ cảnh báo, không fail cứng).
   Lịch nền không hỏi được → đặt mật khẩu ở `~/.config/kora/ops-pw.env` (chmod 600) cho wrapper source.
5. **Thời gian + tần suất (THÂN THIỆN — KHÔNG bắt user gõ cron):**
   - **Mốc giờ** → AskUserQuestion **multi-select** gợi ý `08:00 / 12:00 / 14:00 / 17:00` + ô **"Other"** (HH:MM).
     Cho chọn **NHIỀU mốc** (vd 8:00 và 14:00). Các mốc phải **cùng số phút** (khác phút → tạo lịch riêng).
   - **Tần suất** → AskUserQuestion **[Mỗi ngày] / [Thứ 2–6] / [Ngày tùy chọn]**.
   - KORA tự dựng cron qua `--times/--days` (KHÔNG cần user hiểu cron). Đọc lại bản tóm tắt "chạy lúc nào".
6. **Tiền kiểm CONNECTION (bắt buộc cho lịch HĐH):** mỗi nguồn trong scan-list phải có **credential chạy
   nền được** (PAT/API token/OAuth còn refresh). Chỉ có OAuth tương tác mà thiếu PAT → **từ chối tạo lịch**,
   mời `/kora-connect` cấp PAT. Kiểm bằng `check_connection.py --check <id>`.
7. ✋ **Confirm trước khi tạo/đổi bất kỳ scheduled task nào.**
   - Máy → `schedule.py register --id <slug> --times "08:00,14:00" --days mon-fri --scan a,b
     --report-projects KEY1,KEY2 --mail-provider smtp --email "x@y.com" [--sync-targets confluence,github] [--post x,y]`.
     (`--days`: `every` / `mon-fri` / csv `mon,wed,fri`. Power-user vẫn dùng `--cron "<expr>"` thay cho `--times/--days`.)
   - **Fallback nếu cài HĐH lỗi:** `register` in `⚠️ … CHƯA cài được vào HĐH` và lưu lịch `enabled=false`
     (`list` hiện `⚠️CHƯA-CÀI-HĐH`). Mời user thử `enable --id <slug>` lại, hoặc chọn cơ chế **[Cowork]** ở Bước 1.
   - Cowork → `create_scheduled_task` (`notifyOnCompletion:true`).

### Cấu hình kết nối
Skill này KHÔNG tự kết nối nguồn — dùng `/kora-connect`. Chỉ ĐỌC `connections:` để hiện danh sách.

> Sửa danh sách email/scan/post: orchestrator + task ĐỌC config/registry lúc chạy → chỉ cần sửa
> `reports.email` / scan-list / post-list là lịch tự dùng giá trị mới, KHÔNG cần tạo lại task (trừ khi đổi giờ/tần suất).
