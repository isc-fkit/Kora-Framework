# CHANGELOG — Lịch sử BẢN APP (AI Product Factory)

> File này ghi lịch sử **phiên bản của ứng dụng** (CORE: CLAUDE.md, workflows, templates,
> tools, scripts…) — tức là phần đi theo repo khi bạn tải/cập nhật.
>
> ⚠️ **Khác với `.kb/changelog.md`**: file đó ghi lịch sử **tri thức của user** (DATA:
> mỗi lần ghi/sửa tài liệu trong `docs/`, vault, ai duyệt, vì sao). Khi bạn cập nhật app
> (`scripts/update.command`), `CHANGELOG.md` này có thể đổi, còn `.kb/changelog.md` của
> bạn được GIỮ NGUYÊN.

---

## v2.9.7 "Kora-1" — 2026-06-22

- **🔌 Kết nối API hoàn chỉnh cho GitHub & GitLab.** Sau khi verify, connect nay **LIỆT KÊ repo (GitHub
  `/user/repos`) / project (GitLab `/projects`) để CHỌN** — không phải gõ tay (`check_connection.py --list-repos`,
  cùng mẫu Jira `--list-projects`). Tô-ken: `KORA_GITHUB_TOKEN` / `KORA_GITLAB_TOKEN` (shell env; lịch nền → PAT).
- **🦊 GitLab thành nguồn ĐẦY ĐỦ như GitHub.** Thêm tool **`tools/gitlab-sync/sync_gitlab.py`** (mirror github-sync):
  `--check/--push/--pull` KB ↔ repo GitLab qua git + PAT (Basic `oauth2:<token>`, idempotent, gương 1 chiều), kéo
  `.md` → `<vault>/GitLab/` + `_GitLab-Index.md`. Thêm section config `gitlab:` + `.env.example` + README. Gắn vào
  **`/kora-scan`** (pull), **`/kora-sync`** + WF16 (push, target `gitlab`, cổng `KORA_OPS_PW`), và **lịch nền**
  (orchestrator: scan `gitlab:<repo>` pull + sync push). Self-hosted: đổi `gitlab.base_url`.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.9.6 "Kora-1" — 2026-06-22

- **📱 Banner email FULL-WIDTH trên mobile (hết khoảng trắng 2 bên).** Thân email thiếu `<meta viewport>` nên trên
  điện thoại không kích hoạt responsive → banner co lại, dư trắng. Nay thêm `meta viewport` + mở rộng
  `@media (max-width:600px)`: card (`.kcard`) + banner (`.kbanner`) **full-bleed sát mép** (bỏ padding 2 bên của
  `.kbody`, bỏ bo góc) — text bên trong vẫn có lề. Desktop (≥600px) GIỮ card 600px căn giữa, bo góc. ✅ Preview 375px/720px.
- **✉️ Gửi report nhiều người → TÁCH riêng từng email.** `send_report.py --split`: mỗi người nhận **một mail riêng**
  (To = chính họ, không thấy nhau), tái dùng 1 kết nối SMTP, **một người lỗi vẫn gửi người khác** + báo ai fail.
  `kora-send-mail` + lịch nền (orchestrator) tự dùng `--split`. Không `--split` → giữ hành vi cũ (1 mail nhiều địa chỉ).
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.9.5 "Kora-1" — 2026-06-22

- **🧭 Quét Jira ghi ĐÚNG vault (hết lệch "KB-Vault" ↔ report).** `import_jira.py` trước đây **không đọc
  `vault_path`** và neo vault mặc định `./KB-Vault` theo **vị trí script** → ghi nhầm `KB-Vault` (hoặc thư mục KF),
  trong khi `build_report` (v2.9.4) đọc `vault_path` từ config (vd `FPT_Medicare_Brain`) → **import ghi một nơi,
  report đọc một nơi** → báo cáo rỗng/sai nguồn. Nay import_jira dùng `data_root()` + đọc `vault_path` từ config
  project, neo theo **project (cwd)** — KHỚP build_report. Ưu tiên: `OBSIDIAN_VAULT` > config `vault_path` >
  `./KB-Vault`; thêm cờ **`--vault`**.
  > ⚠️ **DATA:** nếu trước đó đã quét vào `KB-Vault`, **quét lại** (ghi vào vault đúng) hoặc **di chuyển**
  > `KB-Vault/* → <vault_path>/` rồi `build_index.py --root .`.
- Thuần **CORE**, KHÔNG migration DATA tự động. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.9.4 "Kora-1" — 2026-06-22

- **🗂️ Hết "Error writing file" khi tạo báo cáo (report theo PROJECT, không theo script).** `build_report.py`
  trước đây tính `REPO_ROOT` theo **vị trí script** → bản cài (`~/.claude/kora-framework`) chạy trong project sẽ ghi
  report + đọc config/vault vào **KF** chứ không phải project (cwd) → `project/reports/` không được tạo → ghi
  `reports/ai-analysis-latest.md` báo lỗi. Nay thêm `data_root()`: nếu cwd có `config/factory-config.yaml` → dùng
  **cwd (project)** cho `out` + `config` + `vault`; ngược lại giữ `REPO_ROOT` (bản dev / lịch nền không đổi).
- **Phòng thủ:** `inject_ai_into_email` tự `os.makedirs(reports/)`; skill `kora-send-mail` + `workflows/14` thêm bước
  **`mkdir -p reports`** (OS-dynamic) trước khi ghi file phân tích AI.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.9.3 "Kora-1" — 2026-06-22

- **🃏 Hết lỗi thẻ chọn "Invalid tool parameters".** Bổ sung **HỢP ĐỒNG SCHEMA** cho AskUserQuestion vào
  `CLAUDE.md` rule #8 (nạp mỗi phiên → áp cho MỌI skill): `header` **≤ 12 ký tự** (lỗi hay gặp nhất — header
  dài như "Gửi ngay / Đặt lịch"), mỗi `option` phải có CẢ **`label` + `description`**, **`multiSelect` bắt
  buộc**, `options` **2–4** (>4 → phân trang). Skill `kora-send-mail` (bước 2b/4) ghi rõ shape hợp lệ;
  `.kb/system-lessons.md` ghi bài học để không lặp.
- Thuần **CORE (guidance)**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.9.2 "Kora-1" — 2026-06-22

- **🆕 Report đính kèm luôn MỚI & KHÁC TÊN (hết "gửi mail bản cũ").** File báo cáo đính kèm nay đổi **tên có
  ngày-giờ** mỗi lần gửi (`progress-report-<YYYY-MM-DD_HHMM>.html`) → client mail KHÔNG lấy lại bản cũ cùng tên.
  `send_report.py` thêm **guard `--stale-after-min` (mặc định 30)**: nếu `email-body-latest.html` cũ hơn 30' → **DỪNG**,
  báo "build lại" — chặn việc lặng lẽ gửi `-latest` cũ khi schedule/sendmail không build lại. Skill + orchestrator
  khẳng định build_report chạy NGAY trước send.
- **🖼️ Banner header NHẸ + hiện chắc trong body.** Nén `assets/banner-daily-report.png` (547KB) → **`banner-daily-report.jpg`
  117KB** (4.7× nhẹ hơn, chữ vẫn rõ). Nhúng **CID inline** (image/jpeg) → ảnh hiện cả khi client chặn ảnh remote — hết
  "load fail" trong thân email. Mọi tham chiếu chuyển sang `.jpg` (send_report vẫn fallback `.png` cho bản cũ).
- **🎨 Màu OT/Thiếu đúng: ÂM = ĐỎ, DƯƠNG = XANH.** `_ot_cell` + KPI + text email: **vượt kỳ vọng (OT, `+`) → XANH**,
  **thiếu (`−`) → ĐỎ** (trước đây ngược: OT đỏ / thiếu xám-amber).
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.9.1 "Kora-1" — 2026-06-22

- **🕘 Tên file report gắn NGÀY-GIỜ tạo.** File trong thư mục ngày nay đặt tên kèm ngày-giờ:
  `reports/<YYYY-MM-DD>/progress-report-<YYYY-MM-DD_HHMM>.html` (+ `email-body-<…>.html` · `progress-data-<…>.json`).
  Chạy nhiều lần trong ngày = **nhiều bản riêng, không ghi đè**, tra cứu theo thời điểm dễ. Bản `-latest` ở gốc giữ
  nguyên cho mailer/orchestrator. Thuần **CORE**, không migration DATA.

## v2.9.0 "Kora-1" — 2026-06-22

- **🧩 Field `Complexity` làm TRỌNG TÂM.** Nạp field Jira "Complexity" (số càng lớn càng phức tạp; **≥7 = phức tạp cao**)
  → frontmatter `complexity` (`import_jira` đọc `JIRA_COMPLEXITY_FIELD`, rỗng → tự dò field tên "Complexity"). Báo cáo có
  **section nổi bật "🧩 Độ phức tạp"** (email + dashboard): KPI *số issue ≥7*, **bar phân bố** (≥7 tô đỏ), **bảng issue phức
  tạp cao** (điểm/người/trạng thái). **AI ưu tiên** phân tích nhóm điểm cao. Cấu hình `jira.complexity_field` / `jira.complexity_high` (7).
- **🔌 Lịch nguồn Jira MCP — KHÔNG báo lỗi cụt.** MCP không chạy được cron nền (token do app giữ) → nay **CHO CHỌN**:
  **[A]** kết nối Jira qua **API** + lịch HĐH nền 24/7 (auto-mail SMTP) · **[B]** lịch **Cowork** (chạy khi mở app). Landing
  (Connect + Schedule) **nói rõ** vì sao MCP không chạy nền + bảng so OS-cron vs Cowork-task.
- **🐞 FIX task tạo từ `/kora-send-mail` không hiện trong `/kora-schedule` list.** `schedule.py cmd_register` nay **LUÔN
  lưu registry** dù `_os_install` lỗi (try/except → enabled=false + install_error) → task luôn findable. `[Liệt kê]` BẮT
  BUỘC gộp cả lịch HĐH + Cowork; **verify** sau khi tạo (chạy `list` xác nhận id + báo nơi lưu).
- **🗂️ Daily report lưu theo THƯ MỤC NGÀY** `reports/<YYYY-MM-DD>/` (progress-report.html · email-body.html · progress-data.json)
  — lịch sử từng ngày; vẫn giữ `-latest` + `progress-data-<ngày>.json` ở gốc cho mailer/orchestrator.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.8.9 "Kora-1" — 2026-06-22

- **🕛 Chuẩn lại mốc tính ngày-công: HÔM NAY chỉ tính SAU 24:00 (hết ngày), KHÔNG phải 17:00.** Ngày chưa qua hết thì
  chưa kỳ vọng 8h logtime cho hôm nay → report **bất kỳ lúc nào trong ngày** (8:00, 12:00, 18:00…) đều KHÔNG báo
  *"thiếu 8h"* oan cho hôm nay. `working_days_elapsed` = số ngày làm việc đến **HẾT HÔM QUA**. Mặc định mốc đổi từ 17 → **24**
  (env `KORA_WORKDAY_END_HOUR` vẫn override được, vd đặt 17 nếu muốn tính sau giờ tan làm). Nhãn báo cáo: *"hôm nay CHƯA tính (chỉ tính sau khi HẾT NGÀY)"*.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.8.8 "Kora-1" — 2026-06-22

- **🐞 FIX tính sai năng suất khi report ĐẦU NGÀY.** Trước đây capacity tính **HÔM NAY** là 1 ngày làm việc đã hoàn
  thành ngay từ 0:00 → report lúc **8:00** (chưa ai làm việc) đã đòi đủ **8h logtime** cho hôm nay → báo *"thiếu 8h"* SAI.
  Nay HÔM NAY **chỉ tính** vào "ngày làm việc đã HOÀN THÀNH" **khi đã qua giờ tan làm** (mặc định **17:00**, đổi qua
  env `KORA_WORKDAY_END_HOUR`). Trước giờ đó → kỳ vọng = số ngày **đã hết** × 8h (không gồm hôm nay) → hết báo thiếu oan.
  Đầu kỳ chưa hết ngày làm việc nào → KHÔNG flag thiếu/OT. Báo cáo ghi rõ *"hôm nay CHƯA tính (chưa qua 17h)"*.
- **📎 CALLOUT nổi bật mở dashboard:** thêm hộp **cam** ngay dưới lời chào — "Mở FILE ĐÍNH KÈM để xem DASHBOARD CHI
  TIẾT" (lọc project/người, biểu đồ, drill-down). Làm rõ email là bản tóm tắt, chi tiết ở file đính kèm.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.8.7 "Kora-1" — 2026-06-22

- **🎯 Giới hạn PHẠM VI báo cáo cho DỰ ÁN LỚN (không lấy hết).** `/kora-daily-report` & `/kora-send-mail` nay hỏi
  **[Sprint đang chạy] / [N ngày gần đây — mặc định 30] / [Toàn bộ]**. `build_report.py` thêm **`--scope sprint|recent|all`
  + `--recent-days N`**: `sprint` = chỉ issue trong **sprint đang chạy** (fallback N ngày nếu không có sprint active);
  `recent` = issue `updated` trong N ngày; `all` = toàn bộ (mặc định). Báo cáo hiện **nhãn phạm vi** trên chip header.
- **⚡ Scan NHẸ theo phạm vi:** scope≠all → mỗi `--jql` bound `... AND updated >= -Nd` (chỉ kéo phần cần — dự án ngàn
  issue không pull hết). Áp cả nhánh API (`import_jira`) lẫn MCP (`searchJiraIssuesUsingJql`).
- **📅 Lịch nền nhớ phạm vi:** `schedule.py register --report-scope/--report-recent-days` → lưu `report.scope`/`recent_days`
  vào `schedules.json`; `orchestrator` tự bound scan + truyền `--scope` cho build_report mỗi lượt. (kora-schedule/WF08 hỏi & lưu.)
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.8.6 "Kora-1" — 2026-06-22

- **🖼️ Banner email HẾT bị Outlook chặn (nhúng CID inline + nhẹ).** Banner header nay **embed inline** (`cid:kora-banner`)
  bền bỉ → Outlook/Gmail hiện NGAY, không cần "trust sender" để load ảnh remote. Ảnh tối ưu **1.8MB → 547KB** (1000px,
  tránh bị Exchange/Outlook *strip*). `send_report.py` resolve banner path bền (`--banner` → `KORA_BANNER` →
  `assets/` cạnh CORE → `$PWD/assets/`) + **log `ℹ️ Banner: nhúng CID …`**; regex khớp cả png/jpg. Skill (`/kora-send-mail`,
  WF14) + lịch nền (`orchestrator`) truyền `--banner` tường minh → CID luôn áp, không phụ thuộc cwd.
- **📋 Thân email = BÁO CÁO ĐẦY ĐỦ (đọc ngay, không cần mở file).** `render_email_body` thêm **bảng "Theo người phụ
  trách"** (Người · Issue · Done · Đang làm · Đã log giờ/ngày-công · % năng suất — tô màu cột) + **Sprint đang chạy**
  (tên · % · hạn). Đầy đủ như dashboard, email-safe (table+bgcolor). Vẫn **kèm file dashboard tương tác** (lọc project/người) cho ai cần.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.8.5 "Kora-1" — 2026-06-22

- **🔄 Lịch nền (report/mail) PULL dữ liệu server từ MỌI nguồn Jira TRƯỚC khi build.** Trước đây orchestrator full-scan
  project báo cáo chỉ từ nguồn Jira **ĐẦU TIÊN** (`break`) — với đa nguồn/đa domain (v2.8.4) các nguồn còn lại không
  được làm mới đầy đủ. Nay **loop TẤT CẢ nguồn Jira API** trong scan-list: mỗi nguồn `import_jira --list-projects` →
  giao với `report.projects` → chỉ `--jql "project in (<giao>)"` (tránh JQL lỗi vì key lạ), **best-effort** (lỗi 1
  nguồn ghi ticket, không chặn nguồn khác) → reindex → build_report trên union.
- **📌 Caveat MCP nền:** nguồn **chỉ-MCP** (vd Atlassian Rovo) **không quét nền được** (launchd/cron không có MCP). Muốn
  report nền có dữ liệu Jira đó → **kết nối Jira đó qua API** (token) + thêm vào scan-list. Ghi rõ ở `/kora-schedule` + WF08.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.8.4 "Kora-1" — 2026-06-22

- **🐞 FIX: báo cáo Jira chỉ quét được Jira API dù đã connect cả Jira MCP.** Root cause: (1) Jira qua **Atlassian Rovo**
  lưu dưới `source_type: atlassian` → luồng report không coi là nguồn Jira; (2) bước scan hardcode `import_jira.py` (API,
  1 cấu hình `JIRA_*` mặc định) → chọn nguồn nào cũng quét self-host → `LỖI: Không có note Jira cho project [...]`.
- **✅ Quét ĐA NGUỒN + ĐA DOMAIN, rẽ nhánh theo nguồn user chọn** (`/kora-daily-report`, `/kora-send-mail`, WF14 Bước 0.5):
  liệt kê mọi nguồn `source_type ∈ {jira_server, jira_cloud, **atlassian**}` (Rovo = có Jira) → **multi-select** (cả API + MCP,
  nhiều domain) → **vòng lặp quét mỗi nguồn bằng route riêng**: `method: api` → `import_jira.py` với `JIRA_BASE_URL`/cred
  của instance đó; `method: mcp` → `getVisibleJiraProjects` + `searchJiraIssuesUsingJql` → `import_jira.py --from-mcp`.
  Tích lũy cùng vault → build_report trên **union project**. (Cảnh báo trùng mã project giữa các domain.)
- **🔎 Thông báo lỗi "thiếu note project" gợi ý hữu ích:** "project có thể thuộc nguồn MCP/Cloud/domain khác chưa quét →
  chọn đúng nguồn & quét lại — không phải mất dữ liệu". **`check_connection.py --list`** thêm cột **SOURCE_TYPE + BASE_URL**.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.8.3 "Kora-1" — 2026-06-22

- **🐞 FIX: gửi mail báo "thiếu SMTP_USER/SMTP_PASS" dù đã điền `.env.local`.** Root cause: `send_report.py` chỉ đọc
  `.env.local` **cạnh chính nó** (`HERE/.env.local`); bản CÀI chạy script ở `~/.claude/kora-framework/tools/report-mailer/`
  nên không thấy file user điền trong **project** → mismatch đường dẫn (KHÔNG phải lỗi "source").
- **✅ Cách fix — truyền path qua BIẾN MÔI TRƯỜNG `KORA_MAILER_ENV`** (giống pattern `JIRA_ENV_FILE`):
  `send_report.py` resolve `.env.local` theo `--env` → `KORA_MAILER_ENV` → `HERE/.env.local`. Skill (`/kora-send-mail`,
  `/kora-daily-report`, `/kora-connect` verify, `/kora-schedule`, `/kora-alert-mail`, WF08/WF14) + `orchestrator` (lịch nền)
  tự đặt `KORA_MAILER_ENV="$PWD/tools/report-mailer/.env.local"`.
- **🔎 `--check` minh bạch hơn:** in `ℹ️ Đọc cấu hình mail từ: <file>` và phân biệt lỗi *không thấy file* / *placeholder
  `PASTE_…` chưa thay* / *thiếu SMTP_USER|SMTP_PASS*. Thông báo nhắc rõ **KHÔNG cần `source`** (đọc file trực tiếp).
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.8.2 "Kora-1" — 2026-06-22

- **✉️ Tên người gửi HIỂN THỊ tuỳ biến (`MAIL_FROM_NAME`):** mặc định **"Kora AI Daily Report"** → người nhận thấy
  **`Kora AI Daily Report <tài-khoản-gửi>`** thay vì email trơ. Trước đây tên cố định trong code (`FROM_NAME`), nay
  đọc từ `.env.local` (`send_report.py`: `cfg("MAIL_FROM_NAME") or DEFAULT_FROM_NAME`).
- **🙅 Bỏ AUTO-điền email cá nhân ở `/kora-connect` Gmail SMTP:** skill nay **HỎI tài khoản gửi CHUYÊN DỤNG**
  (vd `ftel.medicare@gmail.com`) — **TUYỆT ĐỐI không** tự nhồi email cá nhân / email đăng nhập của user vào `.env.local`.
- **🧩 `.env.local.example` chuẩn hơn:** tài khoản gửi chuyên dụng + `SMTP_USER`=`MAIL_FROM`=`<tài khoản gửi>` +
  `MAIL_FROM_NAME=Kora AI Daily Report`. `/kora-send-mail` lần đầu cũng hỏi tài khoản chuyên dụng + ghi `MAIL_FROM_NAME`.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.8.1 "Kora-1" — 2026-06-22

- **🎨 Khối phân tích AI trong email = CARD MÀU theo mục (bỏ chip inline):** mỗi mục một card có viền + nền + tiêu đề
  màu riêng, dễ quan sát — 🔴 Rủi ro cao (đỏ) · 🟡 Rủi ro vừa (vàng) · 🟢 Tích cực (xanh lá) · 👥 Theo thành viên (xanh
  dương) · 📅 Dự đoán sprint (tím) · 🎯 Hành động (teal) · 📌 Tóm tắt (slate).
- **📊 Bảng theo thành viên tô màu cột trạng thái:** `| Thành viên | Tổng | Done | In Review | In Progress | Ghi chú |`
  với header cột Done=xanh lá · In Review=xanh dương · In Progress=cam · Test=tím · Chưa làm=xám (email-safe, render mọi client).
- **🧠 Phân tích CHI TIẾT hơn:** prompt AI yêu cầu 7 mục cố định, mỗi rủi ro kèm **mã issue · người · tác động · đề xuất
  từng bước**; bảng thành viên + dự đoán trượt theo NGÀY LÀM VIỆC; hành động ưu tiên đánh số.
- **🔗 Renderer DÙNG CHUNG (build_report.py `--inject-ai`):** cả lịch nền (`orchestrator`) và gửi mail tay
  (`/kora-send-mail`, WF14) đều ghi phân tích ra markdown rồi `build_report.py --inject-ai` render card → đồng nhất,
  hết cảnh tự viết HTML tay. Sửa: `/kora-send-mail` [Gửi ngay] nay BẮT BUỘC chèn AI trước khi gửi.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.8.0 "Kora-1" — 2026-06-22

- **🤖 Lịch nền TỰ ĐỘNG trọn vẹn (auto-bypass):** `orchestrator._ai_analysis` thêm `--dangerously-skip-permissions`
  cho `claude -p` → headless/cron **KHÔNG kẹt prompt quyền** (tắt được qua `scheduler.ai_risk_analysis.skip_permissions`).
  Prompt AI nay theo **cấu trúc**: Rủi ro (🔴/🟡/🟢 + số) · Dự đoán trượt timeline · Hướng giải quyết · Tổng kết.
- **✉️ SỬA BUG: phân tích AI nay được CHÈN vào email:** trước đây AI ghi ra `ai-analysis-*.md` nhưng **không** nhét vào
  khối `<!--KR-AI-START/END-->` → mail lịch thiếu phần AI. Thêm `_inject_ai_email()` (markdown→HTML, chip rủi ro màu)
  chạy **trước khi gửi** (cả lịch nền).
- **🔄 Báo cáo FULL-SCAN — status + comment MỚI NHẤT, GHI ĐÈ:** WF14 / `/kora-daily-report` / `/kora-send-mail` + lịch nền
  quét FULL `import_jira.py --jql "project in (<KEYS>)"` (KHÔNG `--since`, tránh sót comment-only) → `_purge_stale` + ghi
  đè (mode `w`) ⇒ **1 file/issue, không nhân bản**, task đã Done/đổi trạng thái trên server luôn đúng ở local.
- **📧 Gmail SMTP (App Password) trong `/kora-connect`:** thêm kênh **TỰ ĐỘNG GỬI** (`source_type: gmail_smtp`, method `smtp`)
  → điền `tools/report-mailer/.env.local` → verify `send_report.py --check`. Phân biệt rõ **Gmail MCP = nháp/draft** vs
  **Gmail SMTP = auto-send** (mail tự động ưu tiên SMTP).
- **📅 Logic NGÀY-CÔNG chuẩn hơn:** capacity so log với **số NGÀY LÀM VIỆC ĐÃ TRÔI QUA** (T2–6, bỏ cuối tuần) thay vì cả
  tháng → log đủ **8h/ngày = 100%**, hết "OT nhầm"/"thiếu nhiều"; phơi `working_days_elapsed`, `expected_so_far`,
  `logged_working_days`. Thêm helper `working_days_between` → **duedate TRONG NGÀY** (start 15 / due 16 = **1 ngày** làm việc,
  không tính trượt). Prompt AI nhận quy ước này.
- **🌗 Email chống DARK MODE:** `<meta color-scheme: light only>` + `bgcolor`/màu chữ **tường minh** mọi container +
  `@media prefers-color-scheme:dark` ép nền trắng/chữ đậm → **chữ không biến mất** trên Gmail/Chrome/điện thoại nền tối.
- **📊 BIỂU ĐỒ trong email (email-safe):** thanh **trạng thái xếp tầng** + **bar theo người / theo dự án** dựng bằng
  **table + `bgcolor`** (KHÔNG SVG/JS) → render đúng trên mọi mail client. Khối AI nổi bật giữa email.
- Thuần **CORE**, KHÔNG migration DATA. Máy đã cài: gõ **"cập nhật phiên bản"**.

## v2.7.0 "Kora-1" — 2026-06-21

- **✉️ Email báo cáo chuyên nghiệp hơn:** LUÔN có **banner header** (mặc định ảnh GitHub `main/assets/banner-daily-report.png`
  khi `banner_url` rỗng) → hết email "trơ". Giữ 3 card số liệu + progress bar + "⚠️ Lưu ý quan trọng" + block AI + **responsive**.
- **📈 Dashboard thêm BIỂU ĐỒ + filter luôn hiện:** `build_report.py` thêm **donut trạng thái** + **bar theo người / theo dự án**
  (SVG inline, mở offline được); **filter project/assignee/status/loại LUÔN hiển thị** (sticky đầu trang — trước đây filter
  project ẩn khi chỉ 1 dự án); bảng **zebra + hover**.
- **📧 Gmail App Password ƯU TIÊN TỰ ĐỘNG GỬI:** `/kora-send-mail` [Gửi ngay] mặc định **auto-send qua SMTP**
  (`send_report.py`, Gmail dùng App Password) — KHÔNG tạo nháp thủ công. Chưa có app-password → hướng dẫn tạo rồi gửi thẳng.
  **Tạo nháp (MCP) = FALLBACK**. Config `reports.email.method/provider` mặc định SMTP auto.

> **Cập nhật:** thuần CORE — KHÔNG migration DATA. (Banner ~1.8MB — cân nhắc xuất bản nhẹ hơn nếu cần.)

## v2.6.0 "Kora-1" — 2026-06-21

- **🆕 Skill `/kora-ops-password` — đặt mật khẩu admin 1 lần:** lưu `KORA_OPS_PW` vào `~/.config/kora/ops-pw.env`
  (chmod 600; mật khẩu nhập qua terminal/file, **KHÔNG qua chat/card**). Mở cổng cho `/kora-sync`, `/kora-send-mail`,
  `/kora-daily-report` và lịch nền — không phải export lại mỗi phiên.
- **🐞 Tối ưu "env chưa nhận ngay":** `verify_ops_password.py` nay đọc **env HOẶC file** `~/.config/kora/ops-pw.env`
  (+ `~/.kora/...`) lúc chạy → đặt mật khẩu là **CÓ HIỆU LỰC NGAY** trong session đang chạy, không cần `source ~/.zshrc`.
  Cùng nguồn sự thật với scheduler nền.
- **Landing:** thêm bước **1b · Đặt mật khẩu admin (tùy chọn)** giữa init và connect; README + bảng lệnh cập nhật.
- **🆕 `/kora-daily-report` chọn chi tiết NGUỒN → PROJECT:** chọn nguồn từ `connections:` trước, rồi project trong
  nguồn đó (Jira `--list-projects`, multi-select). `build_report.py` thêm **`--projects KEY1,KEY2`** → báo cáo scope đúng project.
- **🐞 BUỘC scan-first trước report/mail:** `/kora-daily-report` + `/kora-send-mail` + **lịch nền** nay quét nguồn của
  project đã chọn (lấy data MỚI NHẤT) → reindex → rồi mới build report (scope `--projects`) → gửi mail. `orchestrator.py`
  tự truyền `--projects` từ `report.projects`; WF08 Mục B yêu cầu `--scan` chứa nguồn của report-projects.

> **Cập nhật:** thuần CORE — KHÔNG migration DATA.

## v2.5.5 "Kora-1" — 2026-06-21

- **🐞 `/kora-connect` đọc nhầm config (lỗi `unrecognized arguments: --config`):** `check_connection.py` đặt
  config theo vị trí TOOL → chạy từ CORE (`~/.claude/kora-framework/tools`) thì đọc **CORE config** (không có
  `connections:` của user) thay vì **PROJECT config**. Nay thêm **`--config <path>`** + `resolve_config` mặc định
  đọc `config/factory-config.yaml` của **thư mục hiện tại** (PROJECT), fallback CORE. `kora-connect.md` + `kora-scan.md`
  truyền `--config "$PWD/config/factory-config.yaml"`.
- **🐞 MCP Microsoft 365 verify xong "không làm gì":** connector GỘP nhiều dịch vụ nay **HỎI sub-service** —
  Microsoft 365 → **[SharePoint] / [Outlook] / [Cả hai]** (Atlassian Rovo → Jira/Confluence). Verify **từng dịch vụ**
  bằng đúng tool (`sharepoint_folder_search` / `outlook_email_search` / …), ghi **entry riêng** mỗi dịch vụ, và sau
  verify **DẪN sang quét ngay** (SharePoint: search thư mục/path → get data về vault; Outlook: search email → get)
  thay vì dừng im. `kora-scan.md` làm rõ nhánh SharePoint folder-path + thêm Outlook.

> **Cập nhật:** thuần CORE (skill + tool) — KHÔNG migration DATA.

## v2.5.4 "Kora-1" — 2026-06-21

- **🐞 Fix `/kora-version` + `/kora-update` không nhận ra bản mới:** cả hai đọc `version.json` qua **branch-raw**
  (`raw.githubusercontent.com/<repo>/release/version.json`) — **CDN GitHub (Fastly) cache theo path, BỎ QUA query
  `?t=`** → đọc trúng bản CŨ → báo "đang ở bản mới nhất" dù đã có bản cao hơn. Nay đọc theo **SHA commit**
  (`api.github.com/.../commits/release` → `raw/<SHA>/version.json`, immutable — luôn tươi) như installer/updater
  v2.3.4; fallback branch-raw nếu API rate-limit. `workflows/10-update.md` đọc CHANGELOG cùng `$SHA`.
- **Landing:** mục Connect thêm callout — nguồn **MCP** phải **kết nối/authorize ở Claude web/Desktop** (Settings →
  Connectors hoặc `/mcp`) **TRƯỚC** thì mới **hiện & gọi được ở CLI** (`/kora-connect`, scan); API/token thì kết nối thẳng CLI.

> **Cập nhật:** CORE + landing — KHÔNG migration DATA. (Bản ≤2.5.2 vẫn cần re-install 1 lần theo ghi chú v2.5.3.)

## v2.5.3 "Kora-1" — 2026-06-21  ⚠️ QUAN TRỌNG (force)

- **🐞 Sửa BUG cập nhật — updater không refresh skill ở `~/.claude/commands/`:** `scripts/update.command`
  rsync CORE vào `REPO_ROOT` (bản cài managed = `~/.claude/kora-framework/`) nhưng **không đụng**
  `~/.claude/commands/` — nơi Claude THỰC SỰ nạp lệnh `/kora-*`. Hệ quả: mọi fix skill (vd `/kora-connect`)
  **không tới user** dù version CORE đã tăng. Nay `update.command` + `update.bat` thêm bước **refresh
  `/kora-*` vào `~/.claude/commands/`** (và `<Downloads>/Knowledge-Base/Skill/` nếu có) sau khi cập nhật CORE,
  loại `kora-release.md` (maintainer-only). `kora-update.md` ghi rõ.
- **⚠️ MIGRATION (bản ≤2.5.2):** vì updater cũ chưa có bước này, **CHẠY LẠI lệnh cài 1 dòng MỘT LẦN**
  (`curl … install.command` / `.bat`) để nhận updater mới + toàn bộ skill mới (fix `/kora-connect` API phân
  trang + Jira Server/Cloud + path tool, MCP `/mcp`, quét Jira idempotent…). Từ đó về sau "cập nhật phiên bản"
  sẽ tự refresh skill.

> **Cập nhật:** CORE — đánh dấu **force** (quan trọng) vì sửa chính cơ chế cập nhật. KHÔNG migration DATA.

## v2.5.2 "Kora-1" — 2026-06-21

- **🐞 Quét lại Jira → Obsidian IDEMPOTENT (hết file rác trùng):** `import_jira.py` ghi note theo
  `{KEY}_{slug}.md` + thư mục theo loại; trước nay đổi **tiêu đề** (đổi slug) hoặc **đổi loại** (đổi thư mục)
  → file cũ ở lại = trùng cho cùng 1 issue. Nay thêm `_purge_stale(base, key, keep)`: trước khi ghi, **xoá
  mọi file `{KEY}_*.md` cũ cùng key** (mọi thư mục type) ≠ file đích → **mỗi issue đúng 1 file**. Dấu `_` +
  `glob.escape` chống khớp nhầm key tiền tố (PROJ-1 vs PROJ-12); không đụng `_Index/_system`. (Issue XOÁ trên
  Jira vẫn không tự mất — quét full định kỳ nếu cần.)
- **`/kora-connect` nhánh MCP nhắc gọi `/mcp` TRƯỚC:** Bước 3 MCP nay hướng dẫn **`/mcp`** (Claude Code/Desktop)
  để liệt kê + kết nối + authorize MCP server (Atlassian/Microsoft 365/Gmail) trước khi verify; **Cowork (web)**
  thì Settings → Connectors. Bước 2 MCP ghi chú thêm `/mcp`.

> **Cập nhật:** thuần CORE — KHÔNG migration DATA.

## v2.5.1 "Kora-1" — 2026-06-21

- **🐞 Fix `/kora-connect` chọn [API] báo "Invalid tool parameters":** danh sách nguồn API có 5 mục (sau khi thêm
  SharePoint ở v2.4.0) vượt **giới hạn 4 option** của AskUserQuestion. Nay **PHÂN TRANG** (Thẻ 1: Jira Cloud /
  Jira Server / GitHub / [Khác — xem thêm] → Thẻ 2: GitLab / SharePoint) + ghi chú "tối đa 4 option/thẻ".
- **🐞 Fix chọn "Jira Server / self-host" lại chạy Jira Cloud:** Bước 3/4 nay tách rõ — **Server** dùng PAT/Bearer,
  `JIRA_AUTH_MODE=server`, **KHÔNG set `JIRA_EMAIL`**, URL self-host (không atlassian.net); **Cloud** mới dùng
  email/OAuth + atlassian.net. (Khớp `import_jira._is_cloud()` — có EMAIL hoặc atlassian.net mới là Cloud.)
- **🐞 Fix tool không tìm thấy ở BẢN CÀI + fallback YAML lỗi:** thêm rule CORE (`CLAUDE.md` §1.13) — gọi
  `tools/<...>` tự **resolve sang `~/.claude/kora-framework/tools/`** khi project không có; **cấm** tự viết Python
  parse YAML (không có `pyyaml`). `kora-connect.md` Bước 0/4 dùng snippet resolve cho `check_connection.py`.

> **Cập nhật:** thuần CORE (chỉ sửa skill/CLAUDE.md) — KHÔNG migration DATA.

## v2.5.0 "Kora-1" — 2026-06-21

- **🆕 `/kora-init` chọn NHIỀU / TẤT CẢ domain** (trước chỉ chọn 1). Bước 1 dùng AskUserQuestion `multiSelect`
  (có **[Tất cả domain]** + **[Khác — xem thêm]** để vượt giới hạn 4 option, gộp lựa chọn qua nhiều lượt).
- **Rule GỘP từ tất cả domain đã chọn** → `config/domain-rules.md` (header liệt kê domain + mỗi preset 1 mục
  `## <Tên domain>` nguyên văn). Cơ chế ở `workflows/00-setup.md` **§Gộp rule đa-domain**. `domain.preset` nay là
  **chuỗi nối phẩy** (vd `healthcare, telecom`) — parser config scalar-safe.
- **Thêm 8 preset domain** (`config/domain-presets/`): Telecom, Banking, Insurance, Logistics, Government, HR, SaaS,
  Real-estate → **tổng 15** (tự xuất hiện ở danh sách động).
- **Bước "đổi domain / rule"** (`workflows/00-setup.md` Mục B) cũng đa-chọn → gộp lại + reindex.
- Đồng bộ wording `kora-init` + README + landing ("một / nhiều / tất cả domain").

> **Cập nhật:** thuần CORE — KHÔNG migration DATA (config cũ 1 domain vẫn chạy; `domain.preset` đọc như chuỗi).

## v2.4.0 "Kora-1" — 2026-06-21

- **🆕 SharePoint thành ĐÍCH/NGUỒN KB** — tool mới `tools/sharepoint-sync/sync_sharepoint.py` (Microsoft Graph,
  chỉ thư viện chuẩn Python, tái dùng helper `sync_confluence`). Lệnh `--check / --login / --push [--dry-run] / --pull`.
  - **Auth TỰ NHẬN DIỆN cả hai:** `client-credentials` (app-only, **chạy NỀN** — cần `SHAREPOINT_TENANT_ID/CLIENT_ID/CLIENT_SECRET`
    + admin consent `Sites.ReadWrite.All`) **hoặc** `device-flow` (`--login`, tương tác, cache `.oauth-token.json` + refresh).
  - **Idempotent:** map `<vault>/_system/sharepoint/sharepoint-map-<host>-<site>.json` (so `content_hash`, lưu `item_id`+`etag`);
    đẩy raw `.md`, chỉ ghi file đổi nội dung, xóa file rời plan. Token KHÔNG vào chat/git/config.
- **`/kora-sync` thêm target [SharePoint]** (multi-select cùng Confluence/GitHub) — `workflows/16-sync.md` thêm
  "Requirement C — Microsoft Graph"; `config` thêm khối `sharepoint:` + `sync.targets: [confluence, github, sharepoint]`.
- **`/kora-connect` thêm API → [SharePoint (Microsoft Graph)]** (`source_type: sharepoint`, method `api`);
  `tools/connections/check_connection.py` probe SharePoint qua `sync_sharepoint.py --check`.
- **Lịch nền (`/kora-schedule` + `orchestrator.py`) thêm nguồn KÉO `github:<owner/repo>`** (máy USER tự kéo KB host từ
  GitHub private — `sync_github.py --pull` đã có sẵn, nay nối vào SCAN) **và `sharepoint:<site>`**; sync-target thêm `sharepoint`.
- **`sync_github.py --pull` nay CHUYỂN HÓA dữ liệu GitHub thành document chuẩn wiki** (không còn copy thô): mỗi `.md` được thêm
  **frontmatter metadata** (`source: github`, `github_repo/branch/path/url/commit`, `title`, `imported_at`, giữ key gốc của repo) +
  **dòng link nguồn** (blob URL) đầu bài, lưu theo namespace `<vault>/GitHub/<owner>-<name>/<cây repo>`, và dựng lại trang hub
  **`_GitHub-Index.md`** liên kết tất cả (idempotent — file xoá trên repo cũng biến mất). Indexer tự nhặt vào KB.
- **Landing/README:** mô tả tính năng SharePoint (bảng nguồn, bước 7 Sync, sơ đồ) + **callout rủi ro** (app Azure AD /
  admin consent / verify ở máy thật vì sandbox chặn API); thêm **note dùng skill `/kora-*` trong Cowork** (folder `Skill/`
  → kéo vào / Customize → Custom Skills) ở README + landing.
- **`/kora-archive` ship thêm token READ-ONLY GitHub** (tùy chọn) — để gói USER **pull** KB từ repo **private** của host.
  Truyền `KORA_GITHUB_READ_TOKEN` → script đóng gói thành `github.env`, import đặt vào `tools/github-sync/.env.local` (chỉ pull).
  Áp cho cả 4 script archive/import (`.command` + `.bat`). Khuyến nghị Fine-grained PAT 1-repo Contents:Read-only + expiry.

> **Cập nhật:** thuần CORE — KHÔNG migration DATA (config cũ thiếu khối `sharepoint:` vẫn chạy; tool đọc `cfg.get` an toàn).
> SharePoint chỉ hoạt động sau khi đăng ký app Azure AD + cấp quyền; verify/đẩy chạy ở **máy thật** (sandbox Cowork chặn API).

## v2.3.4 "Kora-1" — 2026-06-21

- **🐞 SỬA LỖI QUAN TRỌNG — installer/updater kéo về BẢN CŨ** dù đã phát hành nhiều bản mới. Nguyên nhân:
  tải `archive/refs/heads/release.(tar.gz|zip)` — archive **theo NHÁNH** bị CDN của GitHub **cache rất dai**.
  - **Cách sửa:** hỏi GitHub API `commits/<ref>` (header `Accept: application/vnd.github.sha`) lấy **SHA commit
    mới nhất**, rồi tải `archive/<SHA>.(tar.gz|zip)` — immutable, **không bao giờ cache cũ**; fallback về archive
    nhánh nếu API bị giới hạn. Áp cho **cả 4 script**: `install.command` · `install.bat` · `scripts/update.command`
    · `scripts/update.bat`. Giải nén lấy thư mục con đầu tiên (không phụ thuộc tên `*-release`).
  - ⚠️ **Đang kẹt bản cũ?** Chạy LẠI lệnh cài 1 dòng (`curl … install.command`) để lấy bản mới nhất.
- **Skill mới `/kora-version`** — xem **phiên bản đang cài** (đọc `~/.claude/kora-framework/version.json`,
  fallback `./version.json`) + so với bản mới nhất trên GitHub (gợi ý `/kora-update` nếu cũ). Chỉ ĐỌC.
- **Installer nay copy `version.json` + `CHANGELOG.md`** vào `~/.claude/kora-framework/` để `/kora-version` và
  `/kora-update` đọc được bản đang cài; in **version đã cài** ở cuối installer.
- **Landing/README:** mô tả `/kora-version` (bảng lệnh + mục bảo trì + mục Cập nhật); mục **Cập nhật & Gỡ** nay
  nêu **cách khuyến nghị** là gõ `/kora-update` / `/kora-uninstall` trong Claude (CLI là cách thủ công).

> **Cập nhật:** thuần CORE — không migration DATA. Bản này đánh dấu **quan trọng** (`force`).

## v2.3.3 "Kora-1" — 2026-06-21

- **Cổng vai trò/domain/template hỏi theo TÍNH NĂNG, không "1 lần/phiên".** `workflows/03-request.md` Bước 0
  + `CLAUDE.md` §0.1: mỗi khi user nêu **yêu cầu/tính năng MỚI** → hỏi vai trò (BA/PO/SA/QA) + domain + template;
  nhớ cho follow-up **cùng** tính năng, sang tính năng/yêu cầu mới → **hỏi lại**. Áp đúng "lăng kính" vai trò
  cho từng feature thay vì khóa 1 vai trò cả phiên.
- **README:** sửa link **"📖 Hướng dẫn đầy đủ"** trỏ về trang GitHub Pages chính thức
  `https://isc-fkit.github.io/Kora-Framework/#home` (trước trỏ nhầm site khác) + đồng bộ **badge version**.
- **Landing:** bảng **20 prompt theo thứ tự `_index`** trình bày dễ đọc hơn — bỏ ô gộp (`rowspan`), lặp tên
  nhóm mỗi hàng; đồng bộ wording cổng vai trò ("mỗi yêu cầu/tính năng mới") ở các mục liên quan.

> **Cập nhật:** thuần CORE (đổi nhịp hỏi vai trò) + landing/README — không cần migration DATA.

## v2.3.2 "Kora-1" — 2026-06-21

- **Windows TOÀN DIỆN như macOS/Linux** — viết lại `scripts/import-kb.bat` ngang `import-kb.command`:
  nhận diện **gói archive** (`kora-archive/`), đặt key READ → `confluence-sync\.env.local`, cred báo lỗi
  SMTP → `report-mailer\.env.local`, tạo marker `.kora-user`, tìm cả `kora-archive-*.zip`, reindex bằng `py`.
  (Trước đây gói USER import trên Windows sẽ lỗi.)
- **Luồng phân tích ép ĐÚNG THỨ TỰ prompt** — `workflows/03-request.md` nay bám chuỗi prompt **01→20** theo
  `templates/prompts/_index.md` (lọc theo vai trò; bước sau dựa bước trước, thiếu đầu vào → `[CẦN XÁC NHẬN]`,
  không nhảy cóc).
- **Trang giới thiệu (landing) bổ sung — adapt từ BA Claude Guide:** Responsible AI & bảo mật dữ liệu (3 nhóm
  🟢🟡🔴 + checklist ẩn danh 2 phút) · Quality Gate 3 tầng + review checklist · kỹ thuật prompt (6) + daily
  checklist · giới hạn & hallucination · **4 cổng tuân thủ phân tích** (domain → workflow → template → thứ tự
  prompt) · thêm ví dụ output Tốt/Chưa tốt (Business Rule, NFR, API) · **card mã nguồn** + mục **tiêu chuẩn
  ngành** (Make a README · SemVer · Keep a Changelog · Conventional Commits · 12-factor…).
- **`/kora-daily-report` gắn đúng cổng mật khẩu** 🔒 (Admin permission) ở danh sách chức năng + bảng lệnh
  (kéo dữ liệu live → `KORA_OPS_PW`).
- **Skill `/kora-release` + `workflows/12-release.md`** đồng bộ thực tế: phát hành đẩy **cả 5 nhánh env**
  (`dev/qc/uat/release/main`) cùng 1 commit + ff-merge an toàn.

> **Cập nhật:** thuần CORE, không cần migration DATA.

## v2.3.1 "Kora-1" — 2026-06-21

- **Lịch nền chạy LOCAL — gọi API/gửi mail được (Cowork sandbox chặn).** Khẳng định lịch HĐH
  (launchd/cron/schtasks) chạy như tiến trình local (đúng mạng/VPN, tới Jira nội bộ). Mọi lịch có
  scan/report/mail/sync → bắt buộc dùng Máy (OS), không Cowork.
- **SỬA lỗi orchestrator không nạp `KORA_OPS_PW`.** launchd/cron không có shell env → cổng luôn fail →
  trước đây bỏ cả lượt. Nay `orchestrator.py` **tự nạp** `~/.config/kora/ops-pw.env`
  (Windows `%USERPROFILE%\.kora\ops-pw.env`); `schedule.py register` nhắc tạo file nếu thiếu.
- **Cổng mật khẩu CHỈ gác outward — SCAN không gác.** scan/get + reindex LUÔN chạy (kéo tri thức về);
  chỉ **post/report/mail/sync** cần `KORA_OPS_PW`. Thiếu mật khẩu → vẫn scan, bỏ outward (không fail cứng).
- **`/kora-schedule` hỏi mật khẩu để RẼ LUỒNG (Bước 1.5):** sai/không có → chỉ tạo lịch **SCAN-ONLY**;
  đúng → luồng **ĐẦY ĐỦ**: scan → chọn **Jira→project** tạo report → **người nhận mail** → **thời gian/tần
  suất** → **email ticket sự cố** → (tùy chọn) sync.
- **Email ticket sự cố áp dụng sẵn cho ARCHIVE.** `scheduler.error_recipients` (người phụ trách) +
  `ticket_issue` đi theo gói; ship thêm **cred SMTP no-reply** (`KORA_NOTIFY_SMTP_*` → `notify-smtp.env`) để
  **gói USER khi lỗi tự email người phụ trách**. Thiếu cred → USER chỉ log cục bộ.
- **Quản lý ĐẦY ĐỦ task Cowork (RAM+disk) ở `/kora-schedule`:** bật/tắt/sửa giờ/sửa prompt qua
  `update_scheduled_task`; xóa hẳn = sửa registry `scheduled-tasks.json` + restart (MCP không có delete).
- **Import/scan áp CHUẨN phân tích:** WF02 + `/kora-scan` nay đọc `domain-rules.md` + áp cổng vai
  trò/domain/template + ghi theo **ĐỊNH DẠNG CHUẨN** `ba-prompt-library.md` + `templates/` — chung chuẩn đầu ra
  với workflow 03.
- **Thống nhất `reports.email.to`** (bỏ `recipients` sai) trong kora-schedule/send-mail/alert-mail.

> **Cập nhật:** thuần CORE, không cần migration DATA. Lịch nền có report/mail → tạo
> `~/.config/kora/ops-pw.env` (chmod 600) để cổng qua được.

## v2.3.0 "Kora-1" — 2026-06-21

- **SỬA lịch HĐH: nhiều mốc giờ + Thứ 2–6 nay chạy ĐÚNG trên mọi OS.**
  - **macOS (launchd):** `cron_to_launchd` cũ chỉ lấy mốc giờ ĐẦU (vd `0 8,12,17 * * 1-5` chỉ chạy 8:00).
    Nay sinh MỘT `StartCalendarInterval` cho MỖI tổ hợp (phút × giờ × thứ × ngày × tháng) → chạy đủ mọi mốc.
  - **Windows (schtasks):** `1-5` từng bị `replace('-',',')` thành `MON,FRI` (mất T3/T4/T5) — nay expand range
    đầy đủ `MON,TUE,WED,THU,FRI`; nhiều mốc giờ → tạo nhiều task (`Kora\<id>`, `Kora\<id>__HHMM`), `remove`/
    `disable` gỡ sạch tất cả.
- **Đặt lịch THÂN THIỆN (không cần gõ cron):** `schedule.py` thêm `--times "08:00,14:00" --days every|mon-fri|<csv>`
  (dựng cron qua `build_cron`). Skill `/kora-schedule`, `/kora-send-mail` và workflow 08 hỏi bằng thẻ: chọn
  **mốc giờ (nhiều mốc)** + **[Mỗi ngày]/[Thứ 2–6]/[Ngày tùy chọn]**.
- **Fallback khi cài HĐH lỗi:** `install_*` trả `(artifact, ok)`; thất bại → lịch lưu `enabled=false` +
  `install_error`, `list` hiện `⚠️CHƯA-CÀI-HĐH`, gợi ý `enable` lại hoặc dùng cơ chế **Cowork** (hết báo ✅ giả).
- **`cron_fields` soát khoảng giá trị** (chặn cron rác kiểu `99 99 * * *`).
- **Workflow 08 Mục B** ưu tiên lịch HĐH (`--report-projects`/`--email`, quản lý ở `/kora-schedule`), Cowork
  là cách thay thế "chỉ khi app mở".
- **Bảo mật/dọn dẹp:** vá `archive-kb.bat` strip MỌI `.env*` (gom `.env.jira`/`.env.github`, giữ `.env.example`);
  ngưng theo dõi `config/factory-config.yaml` + `config/domain-rules.md` (DATA, giữ bản local); thêm `assets/`
  (banner/flow được tham chiếu); regenerate `install/uninstall.command.zip`; gỡ file tạm/test
  (`__pycache__`, `.DS_Store`, log gatetest, lịch test cũ `com.kora.daily-report`).

> **Cập nhật:** thuần CORE, **không cần migration DATA**. Lịch đã tạo từ bản cũ giữ nguyên; tạo lại (hoặc
> `edit --times/--days`) để hưởng bản vá nhiều-mốc-giờ/Thứ-2–6.

## v2.2.0 "Kora-1" — 2026-06-19

- **KB ĐÁM MÂY CHUNG (Confluence get & post).** Tool mới `tools/confluence-sync/sync_confluence.py`
  (REST, thư viện chuẩn): `--check`/`--login` (OAuth 2.0 3LO, tự refresh; fallback API token cho cron)
  /`--push` (upsert idempotent: map theo `kb_id`, nhận trang theo title tránh trùng, bỏ qua trang không
  đổi theo hash, tôn trọng trang bị sửa tay) /`--pull` (kéo về vault) /`--check-fresh`. Lỗi từng trang
  được gom, không dừng cả lượt. `permission: read_only` chặn `--push`. Cấu hình ở `confluence:` / `cloud_kb:`.
- **Lịch cấp HỆ ĐIỀU HÀNH** (`tools/kora-scheduler/`): `schedule.py register|list|edit|remove` cài
  launchd (macOS) / crontab (Linux) / schtasks (Windows) → chạy đúng giờ **kể cả khi đóng app**.
  `orchestrator.py` chạy nền: scan nguồn (lỗi thì skip + ghi log) → reindex → ĐẨY Confluence → report →
  mail (chỉ HOST) → **lỗi tự tạo TICKET ISSUE (Confluence/Jira) + email**. Idempotent theo ngày + `.lock`.
  Phân tích rủi ro AI headless qua `claude -p` (best-effort). Wrapper `scripts/schedule.{command,bat}`.
- **Archive bàn giao có MẬT KHẨU + phân quyền.** `scripts/archive-kb.{command,bat}` + `/kora-archive` +
  `workflows/15-archive.md`: cổng mật khẩu `isc-fkit-kora` (hash salted trên repo `config/archive-pw.sha256`,
  chủ repo đổi từ xa) qua `tools/archive-gate/verify_password.py`; gói `kora-archive-*.zip` = `{manifest,
  data/, .env.local (CHỈ key READ), markers/}`; chọn HOST/USER + read-only/read-write. Gói USER: import tạo
  marker `.kora-user` → tắt report/mail, đặt key READ, tự lên lịch get&post. **An toàn:** chỉ ship 1 `.env.local`
  read-only, loại mọi token write/mail/jira khỏi gói.
- **Connect mở rộng + sổ `connections:`.** Block `connections` thật trong config (id =
  `<source_type>__<method>` → **API vs MCP tính RIÊNG**). `/kora-connect` viết lại: OAuth 2.0 Device Flow
  ưu tiên cho API (GitHub/GitLab/Jira), PAT fallback cho cron; MCP cho Atlassian/Gmail/Microsoft 365;
  verify trước khi ghi; ESC quay lại/huỷ. Helper `tools/connections/check_connection.py` (`--list`/`--check`).
- **Migration:** thêm block `connections`/`confluence`/`cloud_kb`/`scheduler`/`package` vào
  `config/factory-config.yaml` (copy từ `.example`); bỏ block `design`. Token Confluence ở
  `tools/confluence-sync/.env.local`. Lịch Cowork cũ vẫn chạy; nên chuyển sang lịch HĐH cho tự động thật.
- **Bỏ HẲN Claude Design** (workflows 04/05, `/kora-design`, `projects/`, template design) — luồng host
  gọn: init → connect → scan → schedule (get & post) → report. Cổng duyệt còn 3 (tri thức / tài liệu·Confluence / code).

## v2.1.0 "Kora-1" — 2026-06-18

- **Cài bằng installer `.command`/`.bat`** (mô hình FKit Reporter): `install.command` / `install.bat`
  (+ 1 dòng `curl|bash`) cài skill vào `~/.claude` (managed, KHÔNG để lại folder source); chạy lại =
  cập nhật (tự thêm skill mới). Kèm `uninstall.command` / `.bat` + lệnh `/kora-uninstall`.
- **12 lệnh `/kora-*` đổi sang TÊN TIẾNG ANH** (kora-init, kora-scan, kora-scan-jira-task,
  kora-daily-report, kora-schedule, kora-update, kora-import-files, kora-evolve, kora-design,
  kora-export-docs, kora-export-knowledge-base, kora-uninstall) — tên + mô tả tiếng Anh.
- **`/kora-scan`** (gộp từ import-jira/import-task): chọn **API / MCP / All** → chọn nguồn
  (Jira Cloud/Server, SharePoint, Confluence…); cào hết field + comment. `/kora-scan-jira-task <KEY>` cho 1 issue.
- **Landing dạng guide nhiều TAB**: 2 tab chính (Cài đặt | Hướng dẫn sử dụng); tab Cài đặt có 2
  sub-tab (Claude CLI / Claude App–Desktop), giống trang FKit claude-reporter-guide.
- **Init gọn nhẹ**: tách bước chọn-domain và domain-rule riêng; bỏ hỏi token/lịch/nguồn khỏi init —
  nạp tri thức + kết nối nguồn (MCP/API) chuyển sang skill `/kora-import-*`, `/kora-schedule`, `/kora-daily-report`.
- **Jira cào HẾT field + comment**: `import_jira.py` ép `*all,comment` (vài Jira `*all` bỏ sót comment).
- **`/kora-init` tự dựng project**: chạy trong folder trống (sau khi cài bằng installer) → scaffold
  project GỌN (docs/01-08 + vault + config + `CLAUDE.md` 1 dòng `@~/.claude/kora-framework/CLAUDE.md`);
  CORE (workflows/tools/templates) dùng chung ở `~/.claude/kora-framework/`.
- **Connect API tự ghi key**: chọn API → ghi `export KORA_*_TOKEN` (+ base URL) vào `~/.zshrc`/`~/.bashrc`
  (không in ra chat); landing thêm mục **"Kết nối API & điền key"** (cách lấy token + mẫu `export` có Copy).
- **`/kora-daily-report` & `/kora-schedule`**: chọn **NHIỀU project** (checklist project đã scan / thêm mới)
  + filter theo thành viên; `/kora-schedule` thêm **Cancel schedule** + List.
- **Tự liên kết chéo project**: khi yêu cầu có quan hệ, phân tích (workflow 03) tự phát hiện + nối tri
  thức các project liên quan (backlink hai chiều → `relation-graph` nối cạnh chéo).
- **Đổi tên** `kora-backup` → **`kora-export-knowledge-base`** (rõ nghĩa: xuất toàn bộ KB).
- **Fix tải installer macOS:** phát hành kèm `install.command.zip` / `uninstall.command.zip` (giữ
  quyền chạy `+x`) → hết lỗi *"could not be executed… appropriate access privileges"* khi double-click;
  landing đổi nút tải sang `.zip` + hướng dẫn **Privacy & Security → Open Anyway**. Nút tải dùng link
  cùng origin (ép tải, không hiện chữ).
- **Installer đặt skill vào `~/Downloads/Kora-Skills/` (+ zip)** để upload TAY vào Claude Cowork (Cowork
  import skill thủ công); chạy lại = skill mới tự kéo về đó; uninstall gỡ luôn.
- **Dashboard báo cáo + Phân tích AI** (`/kora-daily-report`): thêm khối 🤖 (workflow 14 — Bước 1.5):
  phân loại health issue (🟢/🟡/🔴), **dự đoán trượt timeline mỗi sprint** (có lý do), đề xuất theo TỪNG
  thành viên, gợi ý giải quyết rủi ro, tổng kết điều hành; thêm **bar theo project** (`build_report.py`
  xuất `by_project`); báo cáo lọc theo project/thành viên/khoảng thời gian.
- **`/kora-connect` (MỚI)** — kết nối nguồn: chọn **MCP/API** → hiện nguồn HỖ TRỢ (API: Jira Server/Cloud;
  MCP-OAuth: Atlassian, SharePoint, GitHub, Confluence…); ghi vào `config > connections`.
- **`/kora-scan` revamp** — bỏ đoạn intro "quét Jira", hiện **checklist các nguồn ĐÃ kết nối** để chọn quét.
- **`/kora-release` (MỚI, maintainer)** — tự động đề xuất version + sinh CHANGELOG từ `git log` + bump/push.
  → tổng **14 lệnh `/kora-*`**.
- **Thêm domain preset phổ biến** (installer tự kéo về, init liệt kê ĐỘNG): **retail** (Bán hàng),
  **manufacturing** (Sản xuất–Điện tử), **education** (Giáo dục) — cạnh healthcare/fintech/ecommerce/generic = 7 preset.
- **Dashboard UI nâng cấp (PM/PO)** — `build_report.py`: thêm **filter bar tương tác** (lọc theo người +
  trạng thái, JS hide/show), **panel theo project** (khi nhiều dự án), và **container `#kr-ai`** để Claude
  ghi khối Phân tích AI (phân loại rủi ro theo mức · dự đoán trượt timeline mỗi sprint · giải pháp · đề
  xuất theo từng thành viên). Đầy đủ, trực quan, phục vụ quản lý nhiều dự án.
- **Jira quét SẠCH comment:** `import_jira.py` thêm `fetch_all_comments()` — **phân trang**
  `/rest/api/2/issue/{key}/comment` lấy **HẾT comment** khi Jira search giới hạn số lượng (issue nhiều
  comment không còn sót). Custom field vốn đã ghi đủ ở mục "Tất cả field (đầy đủ)".
- **Skill NẰM TRONG folder project:** `/kora-init` tạo `<project>/.claude/commands/` + copy skill →
  Cowork load theo path; `/kora-update` **refresh skill mới** vào 3 nơi (project · `~/.claude/commands` · `~/Downloads/Kora-Skills`).
- **Domain Healthcare/Y tế LUÔN hiện** ở nhóm mặc định khi `/kora-init` chọn domain (cạnh Retail, Manufacturing, [Khác]).
- **`/kora-scan` tự setup khi scan:** nếu chưa có nơi lưu trữ → hỏi ĐÚNG 1 câu (*lưu ở đâu*) rồi **TỰ
  dựng project** (vault + folder skill + domain/rule mặc định `generic`, KHÔNG hỏi từng bước); đã có
  project → scan thẳng. (`/kora-init` trực tiếp vẫn đi từng bước.)
- **Installer kéo domain + rule + xác nhận:** in *"$N skill + $NDOM domain preset (gồm Healthcare/Y tế…)"*;
  cảnh báo nếu nguồn cài cũ thiếu `healthcare.md`. Domain/rule LUÔN được kéo về khi cài `.command`/`.bat`/`curl|bash`.
- **Tối ưu thời gian setup:** `00-setup` chỉ HỎI 2 thứ BẮT BUỘC (domain + tên project), còn lại dùng MẶC
  ĐỊNH → xong ~2 câu hỏi. Phần **cào sâu nhiều bước, phân tích kỹ CHỈ dành cho `workflows/03-request.md`**.
- **`/kora-release` đầy đủ:** hỏi **Merge (`release`→`main`) hay Deploy (từ `release`)**; **tag KHỚP version**
  (`vX.Y.Z`, bỏ hậu tố `-genesis-1` cũ); tạo **GitHub Release + release note** từ CHANGELOG; **deploy web
  (Pages)**; kiểm **version khớp 5 nơi** (version.json · CHANGELOG · badge landing · tag · GitHub Release).
- **Installer TỰ chạy init:** `install.command`/`.bat`/`curl|bash` **tự dựng project** tại `~/Kora-Knowledge`
  (đổi qua biến `KORA_PROJECT`) — cấu trúc `docs/01-08` + vault `Kora_Brain/` + config + **7 domain preset**
  + **`.claude/commands/` chứa skill BÊN TRONG project** (Cowork load theo path) + `CLAUDE.md` 1-dòng. Skill
  cũng vào `~/.claude` (Claude Code). Chạy lại installer = **refresh skill** vào project (bản mới có skill mới).

## v2.0.0 "Kora-1" — 2026-06-17

- **Đổi thương hiệu → Kora-Framework** (từ "Adaptive Knowledge Base" / "Genesis-1") và **dời repo**
  sang `isc-fkit/Kora-Framework`. Cập nhật mọi URL tải / cập nhật / issue + raw version & CHANGELOG.
- **Landing mới (`index.html`)** dạng hướng dẫn từng bước (nền tối + indigo, timeline số, thẻ OS
  macOS/Windows, code-block có tab + nút Copy, callout) — bỏ cảnh 3D Three.js, nhẹ và nhanh hơn.
- **Lệnh tắt đổi sang tiền tố `/kora-*`** (vd `/kora-khoi-tao`, `/kora-bao-cao`) cho khỏi trùng;
  gõ `/kora` ra cả nhóm 11 lệnh.
- **Sao lưu/khôi phục an toàn UTF-8 cho tên tiếng Việt:** `import-kb.command` dùng `ditto` (macOS)
  thay `unzip` để không làm hỏng tên note tiếng Việt; gói export đổi prefix `genesis1-kb-` →
  `kora-kb-` (import vẫn nhận gói cũ). Đổi file CORE `scripts/0-ĐỌC-TRƯỚC.txt` →
  `scripts/0-READ-FIRST.txt` (tên ASCII, tránh lỗi giải nén/cross-platform).

## v1.2.2 "Genesis-1" — 2026-06-17

- **Script cài đặt double-click bớt phiền vì cảnh báo bảo mật.** Các `.command`/`.bat`
  (update / export-kb / import-kb) tự gỡ nhãn quarantine của macOS (`com.apple.quarantine`)
  và Mark-of-the-Web của Windows (`Unblock-File`) cho thư mục `scripts/` ngay khi chạy → sau
  khi vượt cảnh báo 1 lần đầu, các script còn lại double-click chạy thẳng, KHÔNG bị Gatekeeper /
  SmartScreen hỏi lại. Thêm `scripts/lib-paths.sh: self_dequarantine()` (dùng chung cho 3
  `.command`) và `scripts/0-ĐỌC-TRƯỚC.txt` hướng dẫn thao tác "Open Anyway" / "Run anyway"
  lần đầu. Lưu ý: chưa ký notarize nên lần mở ĐẦU TIÊN vẫn cần xác nhận thủ công 1 lần.

## v1.2.1 "Genesis-1" — 2026-06-15

- **Gộp custom "effort theo giờ" vào ước tính (est).** `import_jira.py` thêm `JIRA_EFFORT_FIELD`
  (config `jira.effort_field`, vd FMC `customfield_10867` "Effort Plan (h)"): khi issue thiếu
  time-tracking chuẩn, lấy field này (số giờ × 3600) làm ước tính → tổng est sát thực tế hơn
  (vd FMC: 396h → 621h, issue thiếu ước tính giảm). Workflow 14 tự đặt biến này từ config.

## v1.2.0 "Genesis-1" — 2026-06-15

- **Báo cáo tiến độ TỰ LÀM MỚI dữ liệu (Pha 2).** "báo cáo tiến độ" giờ làm mới trước khi báo:
  - **Jira Cloud** (`*.atlassian.net`, có MCP): tự kéo issue mới qua MCP → nạp vault (KHÔNG cần token,
    không nạp khối lớn vào ngữ cảnh — xử lý qua file) → reindex → report. `import_jira.py` thêm
    `--from-mcp` (tái dùng toàn bộ logic ghi note) + `run_from_issues`.
  - **Jira self-host** (token, nền không tới host nội bộ): KHÔNG tự kéo → `--check-fresh`; nếu CŨ → vẫn
    sinh report (banner "DỮ LIỆU ĐÃ CŨ") + in lệnh terminal để user tự kéo, kéo xong gõ lại "báo cáo tiến độ".
  - **Idempotent-per-day** (`--since`/`--from-mcp` bỏ qua nếu hôm nay đã sync; `--force` để ép).
  - `build_report.py`: nhóm trạng thái theo `statusCategory` (tin cậy với status tùy biến) + sprint từ
    fixVersions ("Sprint XX") + banner dữ liệu cũ. `import_jira.py` ghi `status_category` vào frontmatter.
- **"đặt lịch báo cáo"** (workflow 08 mục B): lịch 8:00 tự làm mới→report (chạy bù, idempotent, có nhánh "báo cũ").
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.1.0 "Genesis-1" — 2026-06-15

- **MỚI: Báo cáo tiến độ dự án (framework local, no-server).** Gõ **"báo cáo tiến độ"** →
  `tools/progress-report/build_report.py` đọc vault Jira → tính metrics (trạng thái + % hoàn thành,
  **sprint đang chạy**, **theo assignee**, **thời gian est/log/remaining**, rủi ro: quá hạn / thiếu
  assignee-ước-tính) → xuất `reports/progress-report-*.html` (dashboard standalone) + JSON. Workflow
  14 **hiện UI ngay trong Cowork** (widget visualize: thẻ metric + donut trạng thái + bar theo người)
  + báo file HTML. KHÔNG đẩy dữ liệu ra server (thay mô hình hook-60s).
- **`import_jira.py`:** thêm frontmatter máy-đọc (`time_estimate_s/spent_s/remaining_s`,
  `story_points`, `sprint_name/state/end`) để report cộng dồn chính xác — quét lại để có dữ liệu này.
- `reports/` là DATA (gitignore + giữ khi cập nhật). (Pha 2 — round sau: lịch 8:00 tự pull→report.)
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.9 "Genesis-1" — 2026-06-15

- **Render đẹp field tiến độ khi quét Jira:** `import_jira.py` thêm xử lý riêng cho **Sprint**
  (Cloud object + parse được chuỗi serialize của Jira Server → `Sprint 3 (active, ngày-bắt-đầu →
  ngày-kết-thúc)`), **time tracking** (Ước tính gốc / Còn lại / Đã log), và field thời-gian-giây
  (`timespent`, `timeoriginalestimate`, `timeestimate` → đổi sang `8h`, `2d`). Sprint + time +
  start/end/due đưa cả lên frontmatter cho dễ tra. Story points (số thường) không bị nhầm thành thời gian.

## v1.0.8 "Genesis-1" — 2026-06-15

- **Quét Jira CÀO HẾT mọi field:** `tools/jira-to-obsidian/import_jira.py` mặc định dùng
  `fields=*all` — mỗi note lấy TẤT CẢ field của issue (priority, labels, components, assignee,
  reporter, created/updated, resolution, sprint, story points và MỌI custom field) ở mục
  `## Tất cả field (đầy đủ)`, tên custom field hiển thị người-đọc (map từ `/rest/api/2/field`).
  Thêm flatten ADF (rich-text Cloud), enrich frontmatter, attachment kèm link. Tắt bằng
  `JIRA_FETCH_ALL_FIELDS=false` cho chế độ gọn.
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn. Quét lại để lấy đầy đủ field mới.)

## v1.0.7 "Genesis-1" — 2026-06-14

- **Obsidian là TÙY CHỌN:** setup (`workflows/00-setup.md` Bước 3) giờ HỎI "đã cài Obsidian chưa?"
  trước, gợi ý cài nếu cần, và nói rõ hệ thống chạy bình thường KHÔNG cần Obsidian (vault chỉ là
  thư mục `.md`; mở bằng editor markdown bất kỳ). Ghi rõ ở README + landing.
- **OS-dynamic toàn repo:** thêm nguyên tắc 12 trong `CLAUDE.md` (python3↔`py`, `mv`↔`Move-Item`,
  path `/`↔`\`, mở folder/file ẩn theo OS). Mọi lệnh `python3 build_index.py` nêu biến thể Windows
  `py`; Bước 3 đổi tên thư mục có lệnh PowerShell; `scripts/update.bat` sửa `python3`→`py`.
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.6 "Genesis-1" — 2026-06-14

- **Sau khi quét Jira → gợi ý nạp thêm nguồn:** `workflows/01-import-jira.md` Bước 5 giờ hỏi 4
  lựa chọn — Phân loại · **Quét thêm nguồn Jira khác** (domain nội bộ/Cloud) · **Nạp thêm tài liệu
  (PDF/DOCX/ảnh)** · Để raw. Thêm nguyên tắc §0.4: nạp xong một nguồn thì LUÔN mời nạp thêm nguồn khác.
- **Nhận ẢNH RỜI làm tri thức:** `workflows/02-import-files.md` thêm loại file PNG/JPG/JPEG/WEBP —
  Claude đọc bằng vision (sơ đồ/flow → flow/BR/AC; ảnh UI → design_note). Trigger ở CLAUDE.md nhận "ảnh".
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.5 "Genesis-1" — 2026-06-14

- **Setup nhập liệu bằng THẺ (gợi ý + ô trống), không bắt gõ chat:** Bước 2 (tên project) & Bước 3
  (đường dẫn vault, tên thư mục) giờ hiện AskUserQuestion với gợi ý + ô **"Other"** để bạn tự gõ.
  Sửa rule `CLAUDE.md` §1.8: AskUserQuestion CÓ nhận free text qua ô "Other" — "Failed" trước kia
  do thiếu option cố định, không phải bản chất. Token/secret vẫn chỉ nhập qua `.env.local`.
- **Bước 7 luôn được đánh dấu hoàn thành:** thêm bước đóng task tracker khi `setup_completed:true`
  — không còn để Bước 7 treo "chưa hoàn thành", kể cả khi chạy một mạch tới cuối.
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.4 "Genesis-1" — 2026-06-14

- **Setup luôn hiện THẺ CHỌN ở mọi bước:** vá nốt các sub-step còn bắt gõ tay — "thêm/bớt rule"
  và "đặt lịch sync" giờ mở bằng AskUserQuestion (Có/Không) trước, chỉ hỏi nhập tự do SAU khi user
  chọn nhánh cần nhập. Thêm nguyên tắc 🔑 "mở đầu MỌI quyết định bằng thẻ chọn" vào `workflows/00-setup.md`
  + `CLAUDE.md` §1.8 (bản v1.0.3 mới ép "mỗi bước dừng hỏi" nhưng chưa đổi sub-step free-text thành thẻ).
- **Đồng bộ nhãn version landing:** thêm bước BẮT BUỘC trong `workflows/12-release.md` + `RELEASING.md`
  để mỗi lần phát hành tự cập nhật nhãn version hiển thị trên `index.html` (model card + footer).
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.3 "Genesis-1" — 2026-06-14

- **Đổi tên lệnh → "cập nhật phiên bản":** bỏ hẳn tên cũ "cập nhật model" (chữ "model" gây nhiễu)
  ở mọi nơi. Tên chính giờ là **"cập nhật phiên bản"** + alias "cập nhật ứng dụng / app",
  "lên bản mới nhất", "có bản mới không", "kiểm tra phiên bản".
- **Setup BẮT BUỘC hỏi từng bước:** `workflows/00-setup.md` thêm rule cứng — mỗi bước DỪNG LẠI
  hỏi user (AskUserQuestion / câu thường) rồi mới sang bước kế; KHÔNG tự chọn mặc định, KHÔNG
  gộp bước, KHÔNG chạy lướt. Rule "tự chạy không hỏi" chỉ áp cho phân tích read-only.
- **Luôn hỏi trước khi THỰC THI:** `CLAUDE.md` Approval Gate viết lại rộng hơn — phân tích
  read-only vẫn tự chạy, nhưng mọi thao tác ghi/chạy/sửa/export đều phải hỏi xác nhận mới làm.
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.2 "Genesis-1" — 2026-06-14

- **Hiểu đúng lệnh "cập nhật phiên bản":** lệnh này = **nâng ỨNG DỤNG lên bản phát hành mới**.
  AI chạy thẳng `workflows/10-update.md`, KHÔNG còn hỏi nhầm "bạn muốn cập
  nhật cái gì". Thêm alias: "cập nhật ứng dụng / app", "có bản mới không".
- **Force update + nội dung giới thiệu:** `version.json` thêm 2 field `force` (bool) + `intro`
  (string). Khi phát hành, `workflows/12-release.md` hỏi force? + nội dung giới thiệu; user bản cũ
  lúc **kiểm tra cập nhật** sẽ thấy `intro` nổi bật + cách nâng cấp (force → đánh dấu "bản quan trọng").
- **Video hướng dẫn xem tốt hơn trên điện thoại:** thêm quyền `fullscreen`, link "⛶ Xem toàn màn
  hình" (mở trình phát Drive native — xoay ngang/dọc được), và tinh chỉnh khung video cho mobile.
- **Setup hiện thẻ chọn bấm được:** `workflows/00-setup.md` ghi rõ từng bước hữu hạn dùng
  AskUserQuestion (domain, ngôn ngữ, vault, có/không Jira/file, design); input tự do vẫn hỏi câu thường.
- **Quét Jira bằng lệnh Terminal (bỏ file double-click):** xóa `quet-jira.command`/`.bat` (hay bị
  macOS chặn "không đáng tin cậy"); chỉ dùng lệnh Terminal copy-paste, **điền sẵn đường dẫn tuyệt
  đối thật theo máy/OS, không cần `cd`, không hardcode**. Sửa tài liệu setup (bỏ `pip install` thừa).
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.1 "Genesis-1" — 2026-06-14

- **Base trung lập:** dọn mọi ví dụ dính dự án gốc (tên project, URL Jira, mã issue…) → placeholder
  chung (`MyApp`, `jira.company.vn`, `PROJ-102`…) để user mới setup không nhầm.
- **Tự tiến hóa hệ thống (meta):** thêm `workflows/13-evolve-system.md` — review đối kháng + cải tiến
  chính workflow/rule (maintainer-only), kèm `.kb/system-lessons.md` (bài học tầng quy trình, CORE).
- **Vá setup & quét Jira:** không dùng AskUserQuestion cho input tự do (hết lỗi "Failed"); "quét jira"
  thêm bước chọn nguồn/domain (Server nội bộ / Cloud Atlassian) qua `JIRA_ENV_FILE`.
- **Video hướng dẫn** chuyển sang link Google Drive (bỏ file mp4 nặng trong repo).
- **Kênh phát hành** chuyển sang branch `release` (download + update + Pages từ `release`).
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.0 "Genesis-1" — 2026-06-13

- Bản nền đầu tiên: AI Product Factory điều phối qua CLAUDE.md + workflows.
- Quét Jira đa nguồn (Server tự host + Cloud Atlassian), mỗi nguồn sync riêng, merge an toàn.
- Import Word/PDF, hiểu sơ đồ sequence bằng vision.
- Tự phân tích/đối chiếu xung đột, tự học (lessons), tự reindex.
- Lịch tự đồng bộ chạy-bù khi mở app, chỉ lấy issue mới (--since).
- Cơ chế update giữ tri thức + export/import dời máy.
