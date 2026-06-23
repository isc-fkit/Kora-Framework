---
description: Schedule + MANAGE automatic get→report→mail and optional KB sync. Lists & manages BOTH OS-level schedules (disk, run when app closed) AND Cowork scheduled tasks (RAM+disk, run when app open) — list/enable/disable/edit/delete each — plus customize report email recipients. Sync step is password-gated (operations password). Triggers (vi): «đặt lịch quét jira», «đặt lịch báo cáo», «tự động đồng bộ», «quản lý lịch» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-schedule`. Follow `workflows/08-schedule-sync.md` for full detail.
Skill này **quản lý ĐẦY ĐỦ cả 2 loại lịch** — lịch HĐH (`schedule.py`, lưu ở disk `schedules.json`) **và**
lịch Cowork (`mcp__scheduled-tasks__*`, service giữ ở RAM + registry trên disk) — và **tùy chỉnh gửi mail**
(`reports.email` trong config). Tất cả vào ở **Bước 2** dưới đây.

### Bước 1 — Cơ chế lịch (AskUserQuestion)
> 🛡️ **Vì sao API/mail PHẢI chạy ở MÁY (OS), KHÔNG ở Cowork:** lịch Cowork chạy TRONG **sandbox** của app →
> **gọi API (quét Jira, đẩy Confluence/GitHub) và gửi SMTP thường bị CHẶN**. Lịch cấp HĐH chạy như **tiến
> trình local** của bạn (đúng mạng/VPN, tới được cả Jira nội bộ) nên **gọi API + gửi mail được**. ⇒ Mọi lịch
> có **scan / report / mail / sync** → **BẮT BUỘC chọn [Máy — HĐH]**. Cowork chỉ hợp việc nhẹ (tóm tắt, nhắc nhở).
- **[Máy — chạy cả khi ĐÓNG app] (khuyến nghị, BẮT BUỘC cho API/mail)** → lịch cấp HĐH (launchd/cron/schtasks)
  qua `tools/kora-scheduler/schedule.py`. Job là `orchestrator.py` Python thuần, chạy LOCAL ngoài sandbox
  (scan/get `--since` MỌI nguồn → đẩy Confluence → **FULL-scan project báo cáo từ MỌI nguồn Jira API trong scan_list
  (status/comment mới nhất, ghi đè — PULL dữ liệu server TRƯỚC khi build)** → report → **AI phân tích
  TỰ ĐỘNG bypass quyền** `--dangerously-skip-permissions` rồi **CHÈN vào email** → mail → lỗi thì tạo ticket). Chạy
  đúng giờ kể cả khi app đóng — **không kẹt prompt, không cần người bấm** (bypass tắt qua `scheduler.ai_risk_analysis.skip_permissions`).
  - 🔑 **Một-lần cho lịch nền CÓ report/mail/sync:** vì launchd/cron không có shell env, đặt mật khẩu
    vận hành vào **`~/.config/claude-knowledge/ops-pw.env`** (Windows: `%USERPROFILE%\.claude-knowledge\ops-pw.env`), nội dung
    `KORA_OPS_PW=<mật khẩu vận hành>`, rồi `chmod 600`. `orchestrator.py` TỰ nạp lúc chạy → cổng mới qua được.
    THIẾU file → lịch nền **vẫn chạy SCAN** (kéo tri thức về) nhưng **bỏ post/report/mail/sync** + ghi log.
- **[Cowork — chạy khi MỞ app]** → `mcp__scheduled-tasks__create_scheduled_task`. **CHỈ cho việc nhẹ không gọi
  API/mail** (sandbox chặn). Chạy bù khi mở app; KHÔNG chạy khi đóng app.

### Bước 1.5 — CỔNG MẬT KHẨU vận hành (quyết định LUỒNG tạo mới)
> Cổng này CHỈ gác **report / mail / sync / post** (ghi-phát ra ngoài). **SCAN (kéo tri thức về) KHÔNG cần
> mật khẩu.** Vì vậy mật khẩu quyết định bạn tạo được lịch loại nào:

1. **Kiểm mật khẩu** (KHÔNG in, KHÔNG lưu chat — rule secret):
   - Có `KORA_OPS_PW` (env) **hoặc** file `~/.config/claude-knowledge/ops-pw.env` → `python3 tools/archive-gate/verify_ops_password.py` (exit 0 = đúng).
   - Thiếu → hỏi user nhập mật khẩu vận hành → chạy `KORA_OPS_PW="<nhập>" python3 tools/archive-gate/verify_ops_password.py` (KHÔNG echo).
2. **Phân luồng theo kết quả:**
   - ❌ **Sai/không có** → chỉ mở **LUỒNG SCAN-ONLY** (Bước 3A): đặt lịch **kéo tri thức mới về** từ nguồn đã chọn.
     KHÔNG cho cấu hình report/mail/sync (báo: "report/mail/sync cần mật khẩu vận hành; đặt vào `~/.config/claude-knowledge/ops-pw.env` để mở").
   - ✅ **Đúng** → mở **LUỒNG ĐẦY ĐỦ** (Bước 3B): scan + chọn **Jira→project tạo report** + **mail người nhận** +
     **thời gian/tần suất** + **email ticket sự cố** (+ tùy chọn sync). Nhắc tạo `ops-pw.env` để lịch NỀN cũng qua cổng.
> (Quản lý ở Bước 2 — liệt kê/sửa/xóa — KHÔNG cần mật khẩu; cổng chỉ chặn việc TẠO lịch có outward + lúc CHẠY nền.)

### Bước 2 — Hành động (AskUserQuestion): **[Liệt kê & quản lý]** / **[Tạo mới]** / **[Tùy chỉnh gửi mail]**

**[Liệt kê & quản lý]** → **BẮT BUỘC chạy CẢ 2 lệnh** rồi hợp nhất (đừng bỏ sót — task từ `/claude-knowledge-send-mail [Đặt lịch]`
nằm ở **HĐH** `schedules.json`; nếu chỉ chạy 1 lệnh sẽ "không thấy"), gắn nhãn engine + cột **ENABLED**:
- **Lịch HĐH (disk — chạy cả khi ĐÓNG app):** `python3 tools/kora-scheduler/schedule.py list`
  (registry `tools/kora-scheduler/schedules.json`).
- **Lịch Cowork (RAM + disk — chạy khi MỞ app):** `mcp__scheduled-tasks__list_scheduled_tasks`
  (trạng thái LIVE từ service). Mỗi task: prompt ở `~/.claude/scheduled-tasks/<id>/SKILL.md`, lịch ở registry
  `~/Library/Application Support/Claude/.../scheduled-tasks.json`.

Với MỖI task → AskUserQuestion quản lý **theo loại engine**:

**A) Task HĐH** (`schedule.py`):
- **[▶️ Bật]** `schedule.py enable --id <id>` · **[⏸️ Tắt]** `disable --id <id>` (gỡ artifact OS, GIỮ trong danh sách)
- **[🗑️ Xóa]** `schedule.py remove --id <id>` (✋ confirm) · **[✏️ Sửa]** → Bước 3.

**B) Task Cowork** (`mcp__scheduled-tasks__*`) — **QUẢN LÝ ĐƯỢC qua MCP + file, KHÔNG chỉ panel app:**
- **[▶️ Bật / ⏸️ Tắt]** → `mcp__scheduled-tasks__update_scheduled_task` `{taskId, enabled: true|false}` (ghi thẳng service).
- **[✏️ Sửa giờ/tần suất]** → dựng cron bằng builder mốc giờ + [Mỗi ngày]/[Thứ 2–6] (như Bước 3 §5) →
  `update_scheduled_task` `{taskId, cronExpression: "<cron>"}`.
- **[✏️ Sửa việc task làm]** → Read `path` (SKILL.md) để xem prompt hiện tại → sửa →
  `update_scheduled_task` `{taskId, prompt: "<mới>"}` (hoặc sửa thẳng file SKILL.md).
- **[🗑️ Xóa hẳn]** (MCP **KHÔNG** có hàm delete → xóa ở DISK + restart):
  1. Tìm registry: `find ~/Library/Application\ Support/Claude -name scheduled-tasks.json` → `grep -l '"id": "<taskId>"'`.
  2. ✋ confirm → sao lưu `.bak` → **xóa entry `<taskId>`** khỏi mảng `scheduledTasks` (giữ JSON hợp lệ).
  3. Xóa thư mục prompt `~/.claude/scheduled-tasks/<taskId>/` nếu còn.
  4. Báo user: **khởi động lại app Claude** để service nạp lại registry đã dọn (service giữ trong RAM), hoặc bấm
     **nút thùng rác** trong panel "Scheduled tasks". Task đang `enabled:false` thì không tự chạy nên an toàn tới khi restart.
  > ⚠️ Đừng nhầm sang registry `local-agent-mode-sessions/.../scheduled-tasks.json` (lịch của project khác) —
  > chỉ sửa file chứa ĐÚNG `<taskId>` cần xóa.

**[Tạo mới]** → Bước 3.   **[Tùy chỉnh gửi mail]** → Bước 2b.

### Bước 2b — Tùy chỉnh GỬI MAIL của lịch báo cáo (`reports.email`)
> Mọi lịch report+mail — **cả HĐH lẫn Cowork** (vd task `kora-daily-report-email`) — **ĐỌC `reports.email`
> từ `config/factory-config.yaml` LÚC CHẠY (nguồn DUY NHẤT)**. Sửa ở đây là áp NGAY cho mọi lịch, **KHÔNG cần
> tạo lại task** (chỉ đổi giờ/tần suất mới cần sửa task).
- Đọc `reports.email` (`to` / `enabled` / `method` / `subject`), trình bày cho user.
- **Người nhận** → AskUserQuestion: **[Thêm]** (ô "Other" nhập email mới) / **[Bớt]** (chọn email đang có) — lặp tới
  khi hài lòng → ghi `reports.email.to` (nối phẩy). ✋ Đọc lại danh sách cuối (gửi mail = ra ngoài).
- **Bật/tắt auto gửi** → đổi `reports.email.enabled` (bật `true` cần `to` KHÔNG rỗng; lần ĐẦU bật → chạy
  `KORA_MAILER_ENV="$PWD/tools/report-mailer/.env.local" python3 tools/report-mailer/send_report.py --check` qua **cổng mật khẩu** trước khi `enabled: true`).
- **Tiêu đề** → sửa `reports.email.subject` (`{date}` = ngày chạy).
- `to` rỗng **hoặc** `enabled:false` → lịch **BỎ QUA gửi** (báo "chưa cấu hình người nhận", không fail).

### Bước 3 — Tạo / sửa (theo LUỒNG đã chốt ở Bước 1.5)

> **Luồng lịch khi CHẠY:** SCAN (kéo tri thức về — KHÔNG gác) → reindex → **[cổng `KORA_OPS_PW`]** → POST
> Confluence → report (project đã chọn) → gửi mail → (tùy chọn) SYNC → **lỗi thì tạo ticket + email người phụ trách**.
> Thiếu mật khẩu lúc nền chạy → vẫn SCAN, chỉ bỏ post/report/mail/sync (cảnh báo, không fail cứng).

#### Bước 3A — LUỒNG SCAN-ONLY (không có/sai mật khẩu)
1. **Nguồn để GET** — chọn scan-list từ `connections:` (multi-select, **[Chọn tất cả]**), giống `/claude-knowledge-scan`.
   Token: `jira:<env>`, `confluence:<space>`, **`github:<owner/repo>`** (KÉO KB host về local — vd máy USER pull
   KB chung từ GitHub private), **`sharepoint:<site>`**. SCAN không cần mật khẩu.
2. **Tiền kiểm CONNECTION** (mục §C dưới) + **Thời gian/tần suất** (mục §T dưới).
3. ✋ Confirm → `schedule.py register --id <slug> --times "08:00" --days mon-fri --scan a,b`
   (KHÔNG `--report-projects/--email/--sync-targets`). Lịch này mỗi lượt chỉ kéo tri thức mới về + reindex.

#### Bước 3B — LUỒNG ĐẦY ĐỦ (mật khẩu ĐÚNG)
1. **Nguồn để GET (scan)** — scan-list từ `connections:` (multi-select, **[Chọn tất cả]**).
2. **Lấy dữ liệu mới từ JIRA nào → PROJECT nào để report** — chọn **nguồn Jira** trong scan-list rồi
   **project** của nó (`--report-projects KEY1,KEY2`, multi-select; rỗng = tất cả). (Chỉ HOST; gói `user` không report/mail.)
3. **Gửi mail cho NHỮNG AI** — provider (`--mail-provider`, lịch nền chỉ **SMTP**); người nhận từ
   `reports.email.to` (multi-select) hoặc **[+ Thêm mới]** (lưu lại). (Quản lý tập trung ở Bước 2b.)
4. **Thời gian + tần suất** — mục §T dưới.
5. **Email TICKET SỰ CỐ (khi lịch lỗi)** — AskUserQuestion:
   - **Người nhận mail sự cố** → ghi `scheduler.error_recipients` (rỗng = dùng `reports.email.to`). Thêm/bớt như Bước 2b.
   - **Nơi tạo ticket** → `scheduler.ticket_issue.target` = **[Confluence] / [Jira] / [Không]** (+ space/jira_project nếu cần).
   - ⚙️ Đây là **cấu hình CHUNG** (đọc lúc chạy) → áp cho **MỌI lịch** và **được ship sẵn trong archive/export**
     (xem `/claude-knowledge-alert-mail` + `workflows/15-archive.md`): gói **USER** khi lỗi sẽ tự gửi mail ticket cho **người phụ trách** này.
6. **Tiền kiểm CONNECTION** (§C) + **(tùy chọn) Sync** — đẩy KB lên target (`--sync-targets confluence,github,sharepoint`), có cổng.
   > 🔌 **Nguồn scan là MCP-only** → **KHÔNG dead-end**: AskUserQuestion **[A]** kết nối Jira qua API + lịch HĐH nền 24/7
   > (khuyến nghị) · **[B]** lịch **Cowork** (`create_scheduled_task`, chạy khi mở app). (cron không gọi được MCP — token do app giữ.)
7. ✋ Confirm → `schedule.py register --id <slug> --times "08:00,14:00" --days mon-fri --scan a,b
   --report-projects KEY1,KEY2 --mail-provider smtp --email "x@y.com" [--sync-targets confluence,github,sharepoint]`.
   → **VERIFY:** chạy `schedule.py list` xác nhận `<slug>` xuất hiện (lịch nay LUÔN lưu được dù cài HĐH lỗi) + báo nơi lưu.

#### §T — Thời gian + tần suất (THÂN THIỆN — KHÔNG bắt gõ cron)
- **Mốc giờ** → AskUserQuestion **multi-select** `08:00 / 12:00 / 14:00 / 17:00` + ô **"Other"** (HH:MM). NHIỀU mốc
  được (cùng số phút; khác phút → lịch riêng). **Tần suất** → **[Mỗi ngày] / [Thứ 2–6] / [Ngày tùy chọn]**.
- KORA tự dựng cron qua `--times/--days` (power-user: `--cron "<expr>"`). Đọc lại tóm tắt "chạy lúc nào".

#### §C — Tiền kiểm CONNECTION (bắt buộc cho lịch HĐH)
- Mỗi nguồn trong scan-list phải có **credential chạy nền** (PAT/API token/OAuth còn refresh). Chỉ OAuth tương
  tác mà thiếu PAT → **từ chối tạo lịch**, mời `/claude-knowledge-connect` cấp PAT. Kiểm bằng `check_connection.py --check <id>`.

#### Fallback / Cowork
- **Cài HĐH lỗi:** `register` in `⚠️ … CHƯA cài được vào HĐH`, lưu `enabled=false` (`list` hiện `⚠️CHƯA-CÀI-HĐH`).
  Thử `enable --id <slug>` lại, hoặc dùng cơ chế **[Cowork]** ở Bước 1 (chỉ việc nhẹ, KHÔNG API/mail).
- Cowork → `create_scheduled_task` (`notifyOnCompletion:true`).

### Cấu hình kết nối
Skill này KHÔNG tự kết nối nguồn — dùng `/claude-knowledge-connect`. Chỉ ĐỌC `connections:` để hiện danh sách.

> Sửa danh sách email/scan/post: orchestrator + task ĐỌC config/registry lúc chạy → chỉ cần sửa
> `reports.email` / scan-list / post-list là lịch tự dùng giá trị mới, KHÔNG cần tạo lại task (trừ khi đổi giờ/tần suất).
