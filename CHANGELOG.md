# CHANGELOG — Lịch sử BẢN APP (AI Product Factory)

> File này ghi lịch sử **phiên bản của ứng dụng** (CORE: CLAUDE.md, workflows, templates,
> tools, scripts…) — tức là phần đi theo repo khi bạn tải/cập nhật.
>
> ⚠️ **Khác với `.kb/changelog.md`**: file đó ghi lịch sử **tri thức của user** (DATA:
> mỗi lần ghi/sửa tài liệu trong `docs/`, vault, ai duyệt, vì sao). Khi bạn cập nhật app
> (`scripts/update.command`), `CHANGELOG.md` này có thể đổi, còn `.kb/changelog.md` của
> bạn được GIỮ NGUYÊN.

---

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
