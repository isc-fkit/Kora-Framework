# Workflow 08 — Lịch tự động đồng bộ (scheduled sync) + báo cáo

> Trigger: "đặt lịch quét jira", "tự động đồng bộ", "lên lịch sync", "đặt lịch báo cáo" (confirm ý định trước).
> Cũng được hỏi ở Bước 4 của setup khi user bật quét nguồn.

## 0. Chọn CƠ CHẾ lịch (hỏi đầu tiên, AskUserQuestion)

| | **Máy (HĐH)** — khuyến nghị | **Cowork** |
|---|---|---|
| Chạy khi ĐÓNG app? | ✅ Có (launchd/cron/schtasks) | ❌ Không (chỉ khi mở app, chạy bù) |
| MCP connector? | ❌ Không (dùng API/token + tool REST) | ✅ Có |
| Get & **Post** Confluence? | ✅ orchestrator tự đẩy | Hạn chế |
| Quản lý | `tools/kora-scheduler/schedule.py` (register/list/edit/remove/**enable/disable**) | panel "Scheduled tasks" của app |

- **Máy (HĐH):** dùng `scripts/schedule.command` / `.bat` → `schedule.py`. Job chạy
  `tools/kora-scheduler/orchestrator.py --run <id>`: **scan/auto-get (KHÔNG gác) → reindex → [CỔNG `KORA_OPS_PW`]
  → POST Confluence → report → mail → (sync) → lỗi thì ticket + email người phụ trách**. Cổng sai/thiếu →
  **vẫn scan/get**, chỉ bỏ post/report/mail/sync, cảnh báo — KHÔNG fail cứng. Đây là cách đáp ứng "chạy đúng
  giờ trong máy, không qua sandbox". Xem chi tiết ở **Mục A-HĐH** bên dưới.
- **Cowork:** giữ nguyên cách cũ (`mcp__scheduled-tasks__create_scheduled_task`) — Bước 1–3 + Mục B.
- **Liệt kê = hợp nhất** cả hai: `schedule.py list` + `mcp__scheduled-tasks__list_scheduled_tasks`.

## Mục A-HĐH — Lịch get & post cấp hệ điều hành

> 🔒 **CỔNG MẬT KHẨU gác bước PHÁT RA NGOÀI — KHÔNG gác scan/get.** Orchestrator: chạy **scan/get + reindex
> trước (không cần mật khẩu)**, rồi `verify_ops_password.py` (env `KORA_OPS_PW`) mới mở **post/report/mail/sync**.
> Sai/thiếu → **vẫn scan/get**, chỉ bỏ post/report/mail/sync (ghi log + cảnh báo, không fail cứng). ⇒ Lịch nền có
> outward PHẢI có mật khẩu ở `~/.config/kora/ops-pw.env` (Windows `%USERPROFILE%\.kora\ops-pw.env`), nội dung
> `KORA_OPS_PW=<mk>`, chmod 600 — `orchestrator.py` **TỰ nạp** lúc chạy (không cần wrapper). KHÁC mật khẩu archive.

1. **Tiền kiểm:** mỗi nguồn trong scan/post-list phải có credential **chạy nền được**
   (PAT/API token/OAuth còn refresh) — cron không mở trình duyệt. Kiểm bằng
   `python3 tools/connections/check_connection.py --check <id>`. Nguồn chỉ-MCP không quét nền được → báo user.
2. **Hỏi (THÂN THIỆN — KHÔNG bắt gõ cron):**
   - **Mốc giờ** → AskUserQuestion **multi-select** gợi ý `08:00 / 12:00 / 14:00 / 17:00` + ô **"Other"** (HH:MM).
     Cho chọn **NHIỀU mốc** (cùng số phút; khác phút → lịch riêng).
   - **Tần suất** → AskUserQuestion **[Mỗi ngày] / [Thứ 2–6] / [Ngày tùy chọn]** → `--days every|mon-fri|<csv>`.
   - **scan-list** (id nguồn trong `connections:`, vd `jira:local,confluence:KB`) · **post-list** (đích đẩy,
     vd `confluence:KB`) · (HOST) bật email báo cáo? (qua cổng mật khẩu `send_report.py --check`).
3. ✋ **Confirm** → `python3 tools/kora-scheduler/schedule.py register --id <slug> --times "08:00,14:00" --days mon-fri
   --scan <scan-list> --post <post-list> [--email <list>]` (Windows: `py` / `scripts\schedule.bat`).
   (Power-user: thay `--times/--days` bằng `--cron "<expr>"`. Cài HĐH lỗi → in `⚠️ CHƯA cài được vào HĐH`,
   lưu `enabled=false`; mời `enable` lại hoặc dùng cơ chế **Cowork** ở Mục 0 làm fallback.)
4. Báo user: lịch chạy lúc nào, ghi ở `schedules.json`, sửa scan/post/email KHÔNG cần tạo lại
   (`schedule.py edit`), **bật/tắt** bằng `schedule.py enable|disable --id <slug>` (tắt = gỡ artifact OS
   nhưng GIỮ trong danh sách → bật lại được), gỡ hẳn bằng `schedule.py remove --id <slug>`. Log ở `reports/scheduler-logs/`.

> Lỗi khi chạy nền: orchestrator **skip nguồn lỗi + ghi log**, cuối lượt **tạo ticket issue**
> (`scheduler.ticket_issue.target` = confluence|jira) **và email** `scheduler.error_recipients`
> (rỗng → `reports.email.to`). Idempotent theo ngày, có `.lock` chống chồng lượt.

---

## Điều kiện (cho Mục Cowork bên dưới)

- Đã cấu hình `.env.local` (token + URL) và quét đầy đủ ít nhất 1 lần (có mốc
  `_system/last-import-<host>.txt`).

## ⏰ Cách lịch chạy — NÓI RÕ cho user trước khi đặt

- **Chạy tại máy bạn khi app Claude đang mở** — KHÔNG phải cron đám mây chạy 24/7.
- **Đặt 9h mà 9h máy tắt / app đóng?** → task **chạy bù NGAY lần mở app kế tiếp** (vd 10h);
  không sót gì vì `--since` lấy mọi issue cập nhật **kể từ lần đồng bộ trước**.
- **Chỉ lấy MỚI:** mỗi lần chạy `import_jira.py --since` chỉ kéo issue tạo/sửa từ mốc lần
  trước rồi merge vào vault — không quét lại từ đầu.
- Cron tính theo **giờ địa phương** của máy.
- Mạng: chạy ở máy user nên dùng mạng/VPN của user → tới được cả Jira nội bộ
  (`company.vn`) lẫn Cloud. (Nếu môi trường chạy không ra được host nội bộ → lịch
  chuyển sang **nhắc user** chạy lệnh Terminal `python3 "<TOOL_DIR>/import_jira.py" --since`.)

## Bước 1 — Hỏi tần suất

> "Bạn muốn tự động lấy issue mới/cập nhật từ Jira bao lâu một lần?"
> - [A] Mỗi sáng (vd 8:00) — khuyến nghị
> - [B] Mỗi giờ làm việc
> - [C] Hằng tuần (thứ Hai)
> - [D] Tần suất khác — user tự nêu

## Bước 2 — Tạo scheduled task

Gọi `mcp__scheduled-tasks__create_scheduled_task` với:
- `cronExpression` theo lựa chọn (vd "0 8 * * *" cho mỗi sáng 8h).
- `prompt`: nội dung để phiên tự động chạy, đại ý:

  > "Chạy đồng bộ Jira tăng dần cho project này: vào `tools/jira-to-obsidian`,
  > chạy `python3 import_jira.py --since`. Đọc kết quả, nếu có issue mới/cập nhật thì
  > tóm tắt ngắn gọn (bao nhiêu issue, thuộc project/epic nào) và báo cho tôi.
  > KHÔNG ghi vào KB chính — chỉ cập nhật vault raw + relation graph. Có gì đáng chú ý
  > (vd story mới chưa có AC) thì nêu để tôi xử lý sau."

- Ghi `jira.scheduled_sync` (tần suất + task id) vào `factory-config.yaml`.

### Đa nguồn Jira (vd vừa `company.vn` vừa `myteam.atlassian.net`)

Mỗi nguồn = một file cấu hình riêng + một scheduled task riêng:
- Tạo `.env.<tên-nguồn>` (vd `.env.company`, `.env.cloud`) trong `tools/jira-to-obsidian/`,
  mỗi file là một bản `.env.local` trỏ đúng Jira đó.
- Lệnh trong prompt của từng task: `JIRA_ENV_FILE=.env.<tên-nguồn> python3 import_jira.py --since`.
- Mốc `--since` tách riêng theo host (`last-import-<host>.txt`) → 2 nguồn KHÔNG đè nhau;
  notes mỗi project ở thư mục riêng; quét full giờ cũng **merge** an toàn, không xoá nguồn kia.
- ⚠️ **Tránh 2 Jira trùng MÃ project** (vd cả hai đều có `PROJ`): node graph định danh theo mã
  issue → trùng mã sẽ đè nhau. Đặt `PROJECT_KEYS` không giao nhau giữa các nguồn.

## Xử lý lỗi khi chạy nền

- Phiên scheduled gặp lỗi (401 token hết hạn / mất mạng / Jira nội bộ không tới) → **báo cho
  user** (giữ `notifyOnCompletion`), KHÔNG im lặng. Mốc `last-import` chỉ cập nhật khi quét
  THÀNH CÔNG (script không lưu mốc nếu `die()`), nên lần sau tự quét lại từ mốc cũ — không sót.

## Bước 3 — Xác nhận

Báo user: lịch đã đặt, chạy lúc nào, đồng bộ kiểu gì, đổi/huỷ bằng cách nào
("đổi lịch sync" / "huỷ lịch sync" → dùng update/list scheduled task).

## Mục B — Đặt lịch BÁO CÁO tiến độ (trigger: "đặt lịch báo cáo")

> 🥇 **CÁCH KHUYẾN NGHỊ — lịch HĐH (quản lý được ở `/kora-schedule`).** Để lịch báo cáo+mail **hiện trong
> danh sách `/kora-schedule`, SỬA và XÓA được** (đúng yêu cầu quản lý), đăng ký qua **Mục A-HĐH** với
> `--report-projects` + `--email` (chạy cả khi đóng app, cùng `schedules.json`, cùng cổng `KORA_OPS_PW`):
> `schedule.py register --id <slug> --times "08:00" --days mon-fri --scan <jira-id> --report-projects "<KEYS>"
> --mail-provider smtp --email "<list>"`. ⚠️ **`--scan <jira-id>` BẮT BUỘC là nguồn chứa `<KEYS>`** → mỗi lượt lịch
> SCAN nguồn đó (lấy data mới nhất) → reindex → report **scope đúng `<KEYS>`** (orchestrator tự truyền `--projects`) → mail.
> Đây là cùng đường mà `/kora-send-mail` → [Đặt lịch] dùng. Hỗ trợ
> **nhiều mốc giờ** + **[Mỗi ngày]/[Thứ 2–6]**; bật/tắt/sửa/xóa bằng `schedule.py enable|disable|edit|remove`.

**Cách thay thế (chỉ khi app mở) — Cowork scheduled task qua `/schedule`:** chạy trọn chu trình mỗi ngày —
**kéo dữ liệu → sinh report tiến độ (workflow 14) → (tùy chọn) tự gửi email**. Task chạy LOCAL khi máy thức
và hiện trong panel "Scheduled tasks" của Cowork. **Vẫn quản lý được ở `/kora-schedule` Bước 2 mục B**:
bật/tắt/sửa giờ/sửa prompt qua `update_scheduled_task`; xóa hẳn = sửa registry `scheduled-tasks.json` + restart
(MCP không có hàm delete). ✋ Automation thường trực → **confirm trước khi tạo**.

1. **Hỏi tần suất** (mặc định **8:00 mỗi sáng** `0 8 * * *`) như Bước 1.

2. **Hỏi tự động gửi email?** (AskUserQuestion: "Tự động gửi báo cáo qua email mỗi lần chạy?" → [Có] / [Không]).
   - **Không** → đặt `reports.email.enabled: false`, sang bước 3.
   - **Có** →
     a. **Cổng MẬT KHẨU (bắt buộc):** chạy `KORA_MAILER_ENV="$PWD/tools/report-mailer/.env.local" python3 tools/report-mailer/send_report.py --check` (Windows `py`).
        `--check` chỉ thử đăng nhập SMTP, KHÔNG gửi.
        - ❌ Lỗi (chưa cấu hình / app password sai) → **CHƯA bật được auto-gửi**. Hướng dẫn user: copy
          `tools/report-mailer/.env.local.example` → `.env.local`, tạo Google App Password
          (myaccount.google.com/apppasswords), điền `SMTP_USER` + `SMTP_PASS`. Bí mật CHỈ ở `.env.local`
          (gitignore) — **KHÔNG hỏi/nhập password qua chat/card**. Xong → chạy lại `--check`.
        - ✅ OK → đi tiếp.
     b. **Danh sách người nhận (thêm/xoá tùy ý):** đọc `reports.email.to` hiện có trong
        `config/factory-config.yaml`, trình bày. Dùng AskUserQuestion cho user **thêm** (ô "Other" nhập
        email mới) / **xoá** (chọn email đang có) — lặp tới khi hài lòng. Ghi danh sách cuối vào
        `reports.email.to`. ✋ **Đọc lại danh sách cuối cho user xác nhận** (gửi mail = hành động ra ngoài).
     c. Đặt `reports.email.enabled: true`, `reports.email.method: smtp` trong config.

3. ✋ Confirm → tạo **Cowork scheduled task qua `/schedule`** = gọi `mcp__scheduled-tasks__create_scheduled_task`,
   `notifyOnCompletion:true`. Prompt = **1 task TỰ làm trọn chu trình mỗi lần chạy (kéo dữ liệu → report → gửi mail)**:
   > "Chạy `workflows/14-progress-report.md` chế độ TỰ ĐỘNG cho project này: làm mới dữ liệu
   > (Cloud→kéo qua MCP nạp vault; self-host→`--check-fresh`, không tự kéo) → sinh report
   > `reports/progress-report-latest.html`. Idempotent: hôm nay đã chạy thành công thì bỏ qua.
   > Báo cho user: tiến độ tóm tắt + đường dẫn report. **Nếu KHÔNG làm mới được** (phiên nền thiếu
   > MCP / Jira nội bộ không tới): vẫn sinh report (dữ liệu CŨ, có banner) + hướng dẫn cập nhật.
   > **ĐỌC `reports.email` TỪ config lúc chạy (nguồn DUY NHẤT):** nếu `enabled:true` → gửi tới
   > `reports.email.to`. method `smtp`: `KORA_MAILER_ENV="$PWD/tools/report-mailer/.env.local" python3 tools/report-mailer/send_report.py --to '<reports.email.to nối phẩy>' --subject '<subject, {date}=hôm nay>' --html-file reports/progress-report-latest.html` (lịch NỀN do orchestrator tự đặt biến này);
   > method `gmail_draft`: tạo nháp qua Gmail connector. Thiếu creds → báo user, KHÔNG fail im."
4. Ghi `reports.scheduled` (cron + task_id) vào config. Báo user: cách đổi/huỷ lịch + **cách sửa danh sách nhận** (mục dưới).

### Sửa danh sách / bật-tắt gửi mail (bất cứ lúc nào)
> Trigger: "sửa danh sách email báo cáo", "thêm/bớt người nhận mail", "bật/tắt auto gửi mail".

Vì scheduled task **đọc `reports.email` từ config lúc chạy**, nên chỉ cần sửa config là **lịch tự dùng
giá trị mới — KHÔNG phải sửa/tạo lại task** (đáp ứng "thêm/xoá → tự cập nhật lịch"):
- Đọc `reports.email.to`, trình bày; AskUserQuestion thêm/xoá; ghi lại config. Bật/tắt = đổi `enabled`.
- Bật auto-gửi lần đầu mà chưa có creds → chạy `--check` (cổng mật khẩu như trên) trước khi `enabled:true`.
- Báo user: "đã cập nhật — lịch sẽ gửi theo danh sách mới (không cần tạo lại lịch)."

> ⏰ Chạy bù khi mở app (như lịch sync). Lịch nền có thể thiếu MCP/connector → đã có nhánh "báo cũ +
> hướng dẫn" / "thiếu creds → báo, không fail" để không bao giờ fail im lặng.
>
> 🗂 **Quản lý task Cowork (RAM + disk) — `/kora-schedule` Bước 2 mục B làm được:**
> - **Bật/Tắt · Sửa giờ · Sửa prompt** → `mcp__scheduled-tasks__update_scheduled_task`
>   (`{taskId, enabled}` / `{cronExpression}` / `{prompt}`) — ghi thẳng service, KHÔNG cần restart.
> - **Xóa hẳn** (MCP KHÔNG có hàm delete) → xóa entry trong registry
>   `~/Library/Application Support/Claude/claude-code-sessions/<...>/scheduled-tasks.json` (sao lưu `.bak`, giữ JSON
>   hợp lệ) + xóa `~/.claude/scheduled-tasks/<id>/`, rồi **khởi động lại app** để service nạp lại (giữ RAM), hoặc
>   nút thùng rác trong panel. Đừng đụng registry `local-agent-mode-sessions/...` (project khác).
> - **Scope:** task tạo qua `/schedule` đăng ký theo phiên/agent tạo ra; muốn hiện trong panel Cowork thì tạo
>   **trong Cowork app**.
