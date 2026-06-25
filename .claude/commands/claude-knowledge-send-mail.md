---
description: Send a progress-report email to chosen recipients — now or on a schedule. PRIORITIZES automatic SMTP send (Gmail via App Password), not manual drafts. Scans the chosen Jira project for latest data, builds the report (banner + cards + charts), then sends. Password-gated (operations password); only this gated entry can send mail. Triggers (vi): «gửi mail báo cáo», «email tiến độ cho team», «gửi report qua mail» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-send-mail` — gửi email báo cáo tiến độ. **CÓ CỔNG MẬT KHẨU vận hành
(`KORA_OPS_PW`)** — phải qua cổng mới vào được phần này.

**Luồng (đúng thứ tự — chọn nguồn → người nhận → gửi):**
1. **Chọn nguồn Jira đã kết nối (CÓ THỂ NHIỀU):** `check_connection.py --list --json` → lọc entry **Jira-capable**
   `source_type ∈ {jira_server, jira_cloud, **atlassian**}` (**`atlassian` = Atlassian Rovo CÓ Jira**). AskUserQuestion
   **multi-select** (kèm `method` API/MCP + `base_url` để phân biệt domain) — chọn **1 HOẶC NHIỀU** Jira. (Chưa có → `/claude-knowledge-connect`.)
2. **Chọn project trong (mỗi) Jira đó — THEO `method`:** API → `import_jira.py --list-projects` (env nguồn đó); MCP
   (`atlassian`/`jira_cloud`) → `getVisibleJiraProjects` → AskUserQuestion **multi-select project** (+ **[Chọn tất cả]**).
2b. **Chọn PHẠM VI báo cáo (dự án LỚN — không lấy hết):** AskUserQuestion **[Sprint đang chạy] / [N ngày gần đây —
   mặc định 30] / [Toàn bộ]** → `SCOPE` (sprint/recent/all), `NDAYS`. SCOPE≠all → scan thêm `AND updated >= -<NDAYS>d` + build_report `--scope`.
   (Thẻ hợp lệ: `header` ≤12 ký tự vd "Phạm vi", mỗi option có `description`, `multiSelect:false` — CLAUDE.md rule #8.)
3. **Chọn người nhận (mail gửi đến):** danh bạ `reports.email.to` (multi-select) + **[+ Thêm mới]**
   (ô "Other" → gõ địa chỉ → **lưu vào `reports.email.to`**). Đây là nguồn người nhận DUY NHẤT mà lịch/task đọc.
4. **Gửi ngay hay đặt lịch:** AskUserQuestion **[Gửi ngay] / [Đặt lịch]** (thẻ hợp lệ: `header` NGẮN ≤12 ký tự
   vd "Gửi/Lịch", mỗi option có `description`, `multiSelect:false` — xem CLAUDE.md rule #8; header dài → `Invalid tool parameters`).
   - **[Gửi ngay]:**
     a. **CỔNG MẬT KHẨU vận hành `KORA_OPS_PW`** → `python3 tools/archive-gate/verify_ops_password.py`
        (đọc env **HOẶC** `~/.config/claude-knowledge/ops-pw.env` — đặt 1 lần bằng `/claude-knowledge-ops-password`; **KHÔNG hỏi qua card, KHÔNG in**). Exit ≠ 0 → **DỪNG**.
     b. **Kênh gửi — ƯU TIÊN TỰ ĐỘNG GỬI:** AskUserQuestion **[Gửi tự động (SMTP / Gmail App Password) — khuyến nghị]**
        / **[Tạo nháp gửi tay (MCP)]**. Gmail **dùng App Password qua SMTP** = auto-send (KHÔNG phải draft). Mặc định auto.
     c. **FULL-SCAN MỚI NHẤT — VỚI MỖI nguồn đã chọn, route theo `method` (vòng lặp, GHI ĐÈ, tích lũy CÙNG vault):**
        - **api** (jira_server/jira_cloud): đặt env đúng instance `JIRA_BASE_URL=<entry.base_url>` (+ `JIRA_AUTH_MODE=server`
          nếu jira_server; token shell env hoặc `JIRA_ENV_FILE=<creds.dotenv_path>`) → `import_jira.py --jql "project in (<KEYS>)"`
          (KHÔNG `--since`; `_purge_stale` ghi đè, không nhân bản).
        - **mcp** (`atlassian`/`jira_cloud`): MCP `searchJiraIssuesUsingJql` `project in (<KEYS>)` `fields:["*all"]` →
          `import_jira.py --from-mcp <file> --names <names>` (KHÔNG import_jira API). Chọn MCP thì **bắt buộc** đi nhánh MCP.
        (SCOPE≠all → mỗi `--jql` thêm `AND updated >= -<NDAYS>d` để nhẹ.) Quét hết → reindex `build_index.py --root .` →
        `python3 "$T/progress-report/build_report.py" --projects "<UNION KEYS>" <--scope <SCOPE> --recent-days <NDAYS> nếu ≠all>`.
     c2. **PHÂN TÍCH AI + chèn CARD MÀU vào email (BẮT BUỘC trước khi gửi):** viết phân tích theo
        `workflows/14-progress-report.md` Bước 1.5 → **`mkdir -p reports`** (Windows `New-Item -ItemType Directory -Force
        reports`) rồi ghi `reports/ai-analysis-latest.md` (Write cần thư mục cha — thiếu → "Error writing file"; build_report
        ở bước c đã tạo `reports/` nếu chạy CÙNG cwd project) (markdown 7 mục: 🔴 rủi ro cao ·
        🟡 vừa · 🟢 tích cực · 👥 BẢNG theo thành viên · 📅 dự đoán · 🎯 hành động · 📌 tóm tắt) → `python3
        "$T/progress-report/build_report.py" --inject-ai reports/ai-analysis-latest.md` (tool render **card màu theo mục +
        bảng tô màu trạng thái** vào `email-body-latest.html`). **KHÔNG gửi** khi khối AI còn trống/placeholder.
     > ⛔ **THÂN MAIL chỉ được là `reports/email-body-latest.html`** (bản tóm tắt CÓ BANNER). **TUYỆT ĐỐI KHÔNG** dùng
     > `reports/progress-report-latest.html` (dashboard/"processing") làm `--html-file` — nó KHÔNG có banner, sai UI mail; dashboard CHỈ là `--attach`. KHÔNG tự dán/chế HTML mail.
     d. **GỬI TỰ ĐỘNG (mặc định, kể cả Gmail).** ⚙️ **MỌI lệnh `send_report.py` đặt biến**
        `KORA_MAILER_ENV="$PWD/tools/report-mailer/.env.local"` ở ĐẦU (trỏ đúng file trong project — script CORE ở
        `~/.claude/kora-framework/...` không tự thấy). Kiểm file đó có `SMTP_USER`+`SMTP_PASS`:
        - **Chưa có** → hỏi **tài khoản gửi CHUYÊN DỤNG** (vd `ftel.medicare@gmail.com` — **KHÔNG tự điền email cá nhân
          của user**) → tạo **Gmail App Password** (bật 2FA → `myaccount.google.com/apppasswords`), `mkdir -p
          tools/report-mailer` rồi điền `tools/report-mailer/.env.local`: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`,
          `SMTP_USER=<tài khoản gửi>`, `SMTP_PASS=<app password 16 ký tự>`, `MAIL_FROM=<tài khoản gửi>`,
          `MAIL_FROM_NAME=Claude AI Daily Report` (tên hiển thị, đổi tự do) → verify
          `KORA_MAILER_ENV="$PWD/tools/report-mailer/.env.local" python3 "$T/report-mailer/send_report.py" --check`
          (tool in `ℹ️ Đọc cấu hình mail từ: …`; điền xong chạy lại là được, **KHÔNG cần `source`**). Token chỉ ở `.env.local`.
          Người nhận thấy *Claude AI Daily Report &lt;…&gt;*.
        - ✋ confirm → `KORA_MAILER_ENV="$PWD/tools/report-mailer/.env.local" python3 "$T/report-mailer/send_report.py" --to "<list>"
          --subject "<chủ đề>" --html-file reports/email-body-latest.html --no-attach-html --banner "$T/../assets/banner-daily-report.jpg"
          --attach reports/progress-report-latest.html --split` → **GỬI THẲNG** (banner **nhúng CID inline** → Outlook hết
          chặn; body = BÁO CÁO ĐẦY ĐỦ; dashboard tương tác đính kèm). **`--split` = gửi RIÊNG từng người** (mỗi mail To =
          1 người, không thấy nhau; 1 người lỗi vẫn gửi người khác). Tool in `ℹ️ Banner: nhúng CID …`. Báo "đã gửi tới <list>".
          > ⏱️ **build_report PHẢI chạy NGAY TRƯỚC** lệnh này (Bước c). send_report có **guard chống gửi bản cũ**: nếu
          > `email-body-latest.html` cũ hơn **30 phút** → DỪNG, báo "build lại". File đính kèm tự đổi **tên có ngày-giờ**
          > (`progress-report-<YYYY-MM-DD_HHMM>.html`) nên mỗi mail một bản KHÁC, client không lấy lại bản cũ cùng tên.
        - ⚡ **ƯU TIÊN: có MCP `local-terminal` (`run_command`) → GỬI THẲNG, KHÔNG bàn giao.** Khi `send_report.py` in
          **`SMTP_UNREACHABLE`**, TRƯỚC khi bàn giao: nếu có tool **`run_command`** (MCP `local-terminal`, Claude Desktop)
          → gọi `run_command(command="<đúng lệnh send_report.py vừa chạy, lấy từ `--emit-command`>", cwd="<PROJECT>")`
          → gửi mail THẲNG trên máy thật (ngoài sandbox), lấy kết quả về báo user. Chỉ khi **KHÔNG có** `run_command` → mới bàn giao file lệnh dưới.
        - 🖥️ **BÀN GIAO TERMINAL khi Cowork chặn SMTP + KHÔNG có `run_command` (KHÔNG dead-end):** đọc stderr của `send_report.py`:
          - **`SMTP_UNREACHABLE`** (Cowork sandbox chặn mạng SMTP) → báo cáo ĐÃ build xong ở `reports/` (local thật). **Lấy
            lệnh bàn giao** = chạy lại CÙNG lệnh trên + cờ `--emit-command` (KHÔNG gửi, in 1 dòng lệnh path tuyệt đối) →
            **ghi file chạy được**: macOS/Linux `reports/claude-knowledge-send-mail.command` (thêm dòng đầu `#!/bin/bash` + `chmod +x`),
            Windows `reports/claude-knowledge-send-mail.bat`. Báo user RÕ: *"Cowork bị hạn chế gửi Gmail SMTP. Báo cáo đã tạo xong. Mở
            **Terminal** chạy: `bash "reports/claude-knowledge-send-mail.command"` (hoặc dán lệnh hiện ra) → gửi luôn báo cáo vừa tạo —
            terminal CHỈ gửi, không build lại."* (Đây là cách "tiếp tục việc dang dở ở Cowork, gửi mail luôn".)
          - **`SMTP_AUTH_FAILED`** → KHÔNG bàn giao vô ích; nhắc **sửa App Password** (16 ký tự) trong `tools/report-mailer/.env.local` rồi gửi lại.
        - **[Tạo nháp] = fallback PHỤ** (chỉ khi user chủ động chọn): tạo NHÁP Gmail/Outlook qua MCP → user bấm gửi.
   - **[Đặt lịch]:**
     a0. **Nếu nguồn Jira đã chọn là MCP-only** (method=mcp, vd `atlassian`/`jira_cloud` MCP) → **KHÔNG dead-end:**
        AskUserQuestion **[A]** kết nối Jira qua **API** (`/claude-knowledge-connect`) rồi lịch HĐH nền 24/7 (auto-mail SMTP — khuyến
        nghị) · **[B]** lịch **Cowork** (`mcp__scheduled-tasks__create_scheduled_task`, chạy khi mở app, mail draft). (Lý
        do: cron không gọi được MCP — token do app giữ.)
     a. **Provider** (lịch NỀN chỉ gửi **SMTP**).
     b. **Mốc giờ** — AskUserQuestion **multi-select** gợi ý `08:00 / 12:00 / 14:00 / 17:00` + ô **"Other"**
        (HH:MM tùy chỉnh). Cho chọn **NHIỀU mốc** (các mốc phải cùng số phút; khác phút → tạo lịch riêng).
     c. **Tần suất** — AskUserQuestion **[Mỗi ngày] / [Thứ 2–6] / [Ngày tùy chọn]**.
     d. ✋ confirm (đọc lại "gửi lúc nào, cho ai, PHẠM VI nào") → đăng ký bằng **`--times/--days`** (KORA tự dựng cron):
        `python3 tools/kora-scheduler/schedule.py register --id <slug> --times "08:00,14:00" --days mon-fri
        --scan <jira-id> --report-projects "<KEYS>" --report-scope <SCOPE> --report-recent-days <NDAYS>
        --mail-provider smtp --email "<list>"` (`post_list` rỗng). Lịch nền tự áp phạm vi này mỗi lần chạy.
        (`--days`: `every` = mỗi ngày · `mon-fri` = thứ 2–6 · hoặc csv `mon,wed,fri`. Power-user vẫn dùng được `--cron`.)
     e. → **Task xuất hiện trong danh sách `/claude-knowledge-schedule`** — quản lý tại đó: **Bật/Tắt (active/inactive)**
        (`schedule.py enable|disable --id <slug>`) hoặc **Xóa** (`remove`). Nếu in `⚠️CHƯA-CÀI-HĐH` →
        lịch đã LƯU nhưng chưa cài được vào HĐH (enabled=false); thử `enable` lại hoặc dùng cơ chế **Cowork** làm fallback.
     f. **VERIFY (bắt buộc):** sau register, chạy `python3 "$T/kora-scheduler/schedule.py" list` → xác nhận `id` vừa tạo
        XUẤT HIỆN; báo user rõ "đã lưu ở `tools/kora-scheduler/schedules.json` (lịch HĐH)". (Lịch nay LUÔN lưu được dù
        cài HĐH lỗi → hết cảnh 'tạo xong mà list không thấy'.)

Chỉ quét Jira tới bước **tạo report + gửi mail** (KHÔNG sync KB). Token/secret chỉ ở `.env.local`.
Windows: `python3` → `py`. Gói USER (`.claude-knowledge-user`) → report/mail bị TẮT → chặn tại đây.
