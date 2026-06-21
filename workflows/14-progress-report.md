# Workflow 14 — Báo cáo tiến độ dự án (local, no-server)

> Trigger: "báo cáo tiến độ", "report tiến độ", "tiến độ dự án", "sinh báo cáo" (confirm ý định trước).
> Cũng được Pha 2 (lịch 8:00, `workflows/08-schedule-sync.md`) gọi TỰ ĐỘNG sau khi quét Jira thành công.
>
> Sinh report từ **dữ liệu vault đã quét** (không server, không đẩy đi đâu). Nhấn mạnh: **thời gian
> (ước tính/đã log/còn lại), sprint đang chạy (active), người phụ trách (assignee)**.

## Bước 0 — Kiểm tra dữ liệu

- 🚫 **Guard gói USER:** có `.kora-user` (hoặc `package.type: user`) → máy NGƯỜI DÙNG, KHÔNG báo cáo/gửi
  mail. Báo nhẹ "chỉ HOST mới có báo cáo; máy này chỉ get&post KB chung" rồi DỪNG.
- Đọc `vault_path` từ `config/factory-config.yaml`. Vault chưa có note Jira (`source: jira`) →
  báo nhẹ + gợi ý **`quét jira`** trước (workflow 01). KHÔNG sinh report rỗng.
- Khuyến nghị: nếu vault quét bằng bản < v1.1.0 (thiếu `time_*_s` / `sprint_state`) → nhắc **quét lại**
  để có đủ số liệu thời gian/sprint.

## Bước 0.4 — Cổng mật khẩu vận hành (KORA_OPS_PW)

> 🔒 Báo cáo kéo dữ liệu **live** từ nguồn → PHẢI qua cổng vận hành TRƯỚC khi làm mới/sinh report.
> Cùng cổng với `/kora-sync`, `/kora-send-mail`, lịch nền — **KHÁC** mật khẩu archive. `/kora-export*` KHÔNG dùng cổng này.

`python3 tools/archive-gate/verify_ops_password.py` (đọc env `KORA_OPS_PW` — **KHÔNG hỏi qua card, KHÔNG in**;
Windows `py`). **Exit ≠ 0 → DỪNG**: không làm mới, không sinh report.
- Khác nhánh "dữ liệu CŨ + banner" ở Bước 0.5: nhánh đó chỉ áp **SAU** khi đã qua cổng mà không kéo được
  (mạng/MCP nội bộ) — KHÔNG phải khi cổng hỏng.
- Chế độ TỰ ĐỘNG/lịch (Cowork-scheduled chạy workflow này): mật khẩu lấy từ env
  (`KORA_OPS_PW` / `~/.config/kora/ops-pw.env`); thiếu → cổng hỏng → bỏ lượt, KHÔNG sinh report.
- Gói `.kora-user` đã bị chặn ở Bước 0 nên không tới bước này.

## Bước 0.5 — LÀM MỚI dữ liệu trước khi report (Pha 2)

> 💡 Nếu `config > jira.effort_field` có giá trị (vd `customfield_10867`), **đặt biến
> `JIRA_EFFORT_FIELD=<id>` trước mọi lệnh `import_jira.py`** (token lẫn `--from-mcp`) để gộp field
> "ước tính theo giờ" vào est khi issue thiếu time-tracking chuẩn.

Kiểm tra độ mới: `python3 tools/jira-to-obsidian/import_jira.py --check-fresh` (Windows `py`) → JSON
`{last_import, is_stale, age_days, done_today}`. **`done_today:true` & `is_stale:false` → BỎ QUA làm mới**
(dữ liệu đủ mới), sang Bước 1. Ngược lại, làm mới theo LOẠI Jira (đọc `JIRA_BASE_URL`/config):

**A) Jira Cloud (`*.atlassian.net`, có MCP Atlassian):** tự kéo qua MCP → nạp vào vault → report:
1. `since` = `last_import` (chưa có → kéo full).
2. MCP `searchJiraIssuesUsingJql`: `project = <KEY> AND updated >= "<since>"` (hoặc `project=<KEY>` nếu
   full), `fields:["*all"]`. Kết quả lớn MCP **tự lưu ra file** → dùng path đó; nhỏ (inline) → ghi ra
   `reports/_mcp-pull.json`. (KHÔNG nạp cả khối vào ngữ cảnh — xử lý qua file.)
3. Lấy map tên field 1 lần: `getJiraIssue` 1 issue `expand=names` → ghi `{id:name}` ra `reports/_mcp-names.json`.
4. Nạp vào vault (tái dùng toàn bộ logic ghi note): `python3 tools/jira-to-obsidian/import_jira.py
   --from-mcp <file> --names reports/_mcp-names.json --since` (cờ `--since` để bật idempotent-per-day).
5. Reindex: `python3 tools/kb-indexer/build_index.py --root .`.
> 🔄 **Chắc chắn MỚI NHẤT (status + comment) → FULL-scan project báo cáo, GHI ĐÈ:** thay vì `--since` (có thể bỏ
> sót comment-only / task đã Done trên server), quét FULL `python3 tools/jira-to-obsidian/import_jira.py --jql
> "project in (<KEYS>)"` (KHÔNG `--since`). `_purge_stale` đảm bảo **1 file/issue, ghi đè, không nhân bản** — local
> luôn khớp server. (Lịch nền cũng làm bước này trước khi build — xem orchestrator.)
> Phiên scheduled nền **thiếu MCP** → coi như không kéo được → xử như nhánh "cũ" của B (báo cũ + nhắc mở Cowork gõ "báo cáo tiến độ").

**B) Jira self-host (token, MCP/nền KHÔNG tới host nội bộ):** KHÔNG tự kéo.
- `is_stale:false` → report bình thường (Bước 1).
- `is_stale:true` → **vẫn sinh report (dữ liệu CŨ, có banner)** ở Bước 1, RỒI in **lệnh terminal copy-paste**
  điền sẵn đường dẫn thật (OS-dynamic) để user tự kéo:
  `python3 "<TOOL_DIR>/import_jira.py" --since` (Windows `py "<TOOL_DIR>\import_jira.py" --since`).
  Nhắc: "Chạy lệnh trên để cập nhật, rồi gõ **'báo cáo tiến độ'** lại → báo cáo mới." User kéo xong → chạy lại workflow.

## Bước 1 — Sinh số liệu + dashboard

Chạy (Claude tự chạy trong sandbox; user chạy tay thì OS-dynamic — Windows `py`). **Scope đúng project đã chọn**
bằng `--projects` (báo cáo CHỈ gồm project đó; rỗng = tất cả) — dữ liệu đã được làm mới ở Bước 0.5:

```bash
python3 tools/progress-report/build_report.py --projects "<KEYS đã chọn>"
```

Tạo trong `reports/`:
- `progress-data-<ngày>.json` — số liệu thô (nguồn cho UI inline).
- `progress-report-<ngày>.html` + `progress-report-latest.html` — **dashboard standalone** (mở bằng
  trình duyệt, chia sẻ được; phong cách tối glass; **biểu đồ SVG** (donut trạng thái + bar theo người/dự án),
  **filter tương tác luôn hiện** (dự án · thành viên · trạng thái · loại), bảng zebra/hover + chỗ `#kr-ai`).
- `email-body-<ngày>.html` + `email-body-latest.html` — **thân email tĩnh, responsive cho điện thoại**
  (email-safe, KHÔNG JS; có khối AI giữa `<!--KR-AI-START-->`/`<!--KR-AI-END-->` để điền ở Bước 1.5).

## Bước 1.5 — PHÂN TÍCH AI (rủi ro · phân loại · đề xuất · dự đoán trượt timeline)

> Đọc `reports/progress-data-<ngày>.json` (đã có time est/log/remaining, active sprint + `sprint_end`,
> by-assignee, status, risks). Claude TỰ tính & viết phần này — đây là **"phân tích AI trong dashboard"**.
> KHÔNG bịa số: chỉ suy luận từ JSON; thiếu dữ liệu thì nói rõ.

Sinh khối **🤖 Phân tích AI — CỰC KỲ CHI TIẾT** dưới dạng **MARKDOWN**, rồi để TOOL render thành **CARD MÀU**
(KHÔNG tự viết HTML/chip tay — tool lo màu sắc & bảng):
1. **Ghi markdown** vào `reports/ai-analysis-latest.md`, MỖI MỤC mở đầu `## ` theo đúng thứ tự:
   `## 🔴 Rủi ro cao (blocker)` · `## 🟡 Rủi ro vừa / Cần theo dõi` · `## 🟢 Điểm tích cực` ·
   `## 👥 Phân tích theo thành viên` (KÈM BẢNG markdown `| Thành viên | Tổng | Done | Đang làm | Ghi chú |`) ·
   `## 📅 Dự đoán sprint / timeline` · `## 🎯 Hành động ưu tiên` · `## 📌 Tóm tắt điều hành`.
2. **Render + chèn vào email:** `python3 "$T/progress-report/build_report.py" --inject-ai reports/ai-analysis-latest.md`
   → tool tự thay khối `<!--KR-AI-->` trong `email-body-latest.html` bằng **CARD MÀU theo mục** + **bảng tô màu cột
   trạng thái** (Done=xanh lá · In Review=xanh dương · In Progress=cam · Test=tím · Chưa làm=xám). Mỗi mục một màu riêng dễ quan sát.
3. (a) in inline ở Bước 2 + (b) container `<section id="kr-ai">` của dashboard: dùng **CÙNG nội dung markdown** đó.
Mỗi rủi ro nêu đủ: **mức độ → khả năng/DỰ ĐOÁN + lý do bằng số liệu → tác động → PHƯƠNG ÁN ĐỀ XUẤT từng bước + ai làm + khi nào**. Nội dung mỗi mục:

0. **Đối chiếu theo CHUẨN (Cloud / industry best-practice) — nền cho mọi cảnh báo:** so số liệu với mốc
   chuẩn rồi gọi tên "vượt / đạt / dưới chuẩn" kèm con số (đọc `capacity`, `logged_by_type`, `work_no_log`
   trong JSON):
   - **Năng suất giờ công:** đã log so với **giờ công chuẩn** (ngày làm việc trong tháng × 8h × 5 ngày/tuần).
     `ot_seconds` > 0 → **cảnh báo OT** (nguy cơ burnout/ước tính thấp); đạt < ~80% chuẩn → **log thiếu**
     (nguy cơ under-report / dữ liệu nỗ lực không đủ). Nêu rõ % năng lực + OT/thiếu của nhóm VÀ từng thành viên.
   - **Phủ logtime theo loại:** chỉ Task/Sub-task/Bug log giờ — Epic/User Story/Request KHÔNG; nếu nhiều
     `work_no_log` (Task/Sub-task chưa làm xong mà chưa log) → **dữ liệu nỗ lực không tin cậy**, cảnh báo.
   - **Sprint health:** % done so với % thời gian sprint đã trôi; WIP (đang-làm) quá cao so với sức nhóm; quá hạn.
   - **Phân bổ:** lệch tải giữa thành viên; issue thiếu estimate/assignee.
1. **Phân loại tình trạng (health) theo issue/nhóm:** 🟢 đúng tiến độ · 🟡 cần chú ý · 🔴 rủi ro cao.
   Tiêu chí: quá hạn (duedate < hôm nay & chưa done), sprint active sắp hết hạn mà chưa xong, thiếu
   estimate/assignee, `remaining_s` cao so với thời gian còn lại, **lệch chuẩn năng suất (OT/thiếu)**.
2. **Dự đoán TRƯỢT TIMELINE (mỗi active sprint):** so `sprint_end` với hôm nay → `days_left`; cân khối
   còn lại (`remaining_s`, số issue chưa done) → **nguy cơ trượt: Thấp / Vừa / Cao** + lý do (vd "còn 2
   ngày, 6 issue chưa done, remaining 40h ≫ sức chứa → **Cao**"). Nêu issue kéo lùi tiến độ.
3. **Đề xuất theo TỪNG THÀNH VIÊN:** mỗi assignee 1 dòng — quá tải / đúng nhịp / rảnh / đang trễ →
   hành động gợi ý (giãn việc, hỗ trợ, ưu tiên issue X…) dựa trên total/đang-làm/remaining/done của họ.
4. **Gợi ý GIẢI QUYẾT rủi ro:** mỗi rủi ro 🔴 → 1–2 hành động cụ thể (giao lại, tách nhỏ, dời sprint,
   thêm người…).
5. **Tổng kết điều hành (1–2 câu):** sức khỏe chung + việc cần làm NGAY.

## Bước 2 — Hiển thị UI trong Cowork (inline)

Đọc `reports/progress-data-<ngày>.json` → **render dashboard NGAY trong chat** bằng `visualize`:
1. Gọi `mcp__visualize__read_me` (modules: `chart`) — nạp guideline 1 lần.
2. `mcp__visualize__show_widget` với một dashboard **TUÂN guideline visualize** (KHÔNG dùng nền tối/
   màu cứng của file standalone): nền trong suốt + biến CSS `--color-*`, icon Tabler (không emoji),
   số làm tròn. Gồm:
   - **Thẻ metric:** Tổng issue · % hoàn thành · Đã log/Ước tính · Còn lại · Sprint active.
   - **Donut trạng thái** (Done / Đang làm / Chưa làm) + legend HTML.
   - **Bar ngang theo assignee:** giờ Đã log vs Ước tính.
   - **Bar theo PROJECT** (khi báo cáo nhiều project): tổng issue / % done mỗi project.
   - (Bảng chi tiết issue sprint/assignee → in dạng **markdown trong câu trả lời**, KHÔNG nhồi vào widget.)
3. Kèm tóm tắt text **+ khối 🤖 Phân tích AI (Bước 1.5)**: phân loại health, dự đoán trượt timeline mỗi
   sprint, đề xuất theo TỪNG thành viên, gợi ý giải quyết rủi ro, tổng kết điều hành.
4. **Nêu rõ PHẠM VI đã lọc** ở đầu dashboard: project(s) + thành viên + khoảng thời gian user đã chọn ở
   `/kora-daily-report` (report sinh trên đúng tập đã lọc).

## Bước 2.7 — Gửi báo cáo qua email (nếu `reports.email.enabled: true`)

Đọc `reports.email` từ `config/factory-config.yaml`. `enabled: false` → **BỎ QUA** bước này.

- **`method: smtp`** (full-auto, hợp lịch nền) — chạy (Claude tự chạy trong sandbox; user chạy tay thì Windows `py`).
  Đặt `KORA_MAILER_ENV` trỏ ĐÚNG `.env.local` (script CORE ở `~/.claude/kora-framework/...` không tự thấy file project):
  ```bash
  KORA_MAILER_ENV="$PWD/tools/report-mailer/.env.local" \
  python3 tools/report-mailer/send_report.py \
    --to "<nối reports.email.to bằng dấu phẩy>" \
    --subject "<reports.email.subject, thay {date} bằng ngày hôm nay>" \
    --html-file reports/email-body-latest.html \
    --no-attach-html \
    --attach reports/progress-report-latest.html
  ```
  → thân thư = **email-body** (mobile, đã chèn AI ở Bước 1.5); đính kèm = **dashboard tương tác** (lọc trên máy tính).
  Mật khẩu/App Password ở `tools/report-mailer/.env.local` (gitignore). Thiếu `.env.local` → script tự
  báo lỗi rõ: nhắc user copy `.env.local.example` + tạo Google App Password. **TUYỆT ĐỐI không in mật khẩu.**
- **`method: gmail_draft`** (bán tự động) — gọi tool `create_draft` của Gmail connector: `to`=list,
  `subject`, `htmlBody`=nội dung `email-body-latest.html` (đã chèn AI). Báo user: mở Gmail → Drafts → **Gửi**.
- **Lần ĐẦU bật gửi:** ✋ gửi thử tới 1 địa chỉ của user trước, xác nhận nhận được rồi mới gửi cả `to`.
- **Phiên nền thiếu creds/connector → KHÔNG fail im:** vẫn giữ report ở `reports/`, báo user cách khắc phục.

## Bước 3 — Báo file + bước kế

- Báo đường dẫn `reports/progress-report-latest.html` (mở bằng trình duyệt / gửi cho sếp).
- **Đề xuất bước kế (AskUserQuestion):** `[A] Đặt lịch 8:00 tự động pull→report (workflows/08) ·
  [B] Quét Jira lấy dữ liệu mới (workflows/01) · [C] Phân loại issue thành tri thức (workflows/03) · [D] Dừng`.

## Guardrails
- Mặc định **local-only**. CHỈ gửi ra ngoài khi `reports.email.enabled: true` — và chỉ tới đúng `reports.email.to` user đã cấu hình (xác nhận lần đầu). KHÔNG ghi vào `docs/` KB chính — report là artifact ở `reports/`.
- `reports/` là DATA (gitignore + giữ khi update) — không commit báo cáo của user.
- Thiếu số liệu (issue thiếu time/sprint) → report vẫn chạy, nêu rõ "X issue thiếu dữ liệu", không bịa.
