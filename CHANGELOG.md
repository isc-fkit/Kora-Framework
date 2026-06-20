# CHANGELOG — Lịch sử BẢN APP (AI Product Factory)

> File này ghi lịch sử **phiên bản của ứng dụng** (CORE: CLAUDE.md, workflows, templates,
> tools, scripts…) — tức là phần đi theo repo khi bạn tải/cập nhật.
>
> ⚠️ **Khác với `.kb/changelog.md`**: file đó ghi lịch sử **tri thức của user** (DATA:
> mỗi lần ghi/sửa tài liệu trong `docs/`, vault, ai duyệt, vì sao). Khi bạn cập nhật app
> (`scripts/update.command`), `CHANGELOG.md` này có thể đổi, còn `.kb/changelog.md` của
> bạn được GIỮ NGUYÊN.

---

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
