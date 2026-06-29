# Workflow 19 — Kiểm tra worklog/thời gian tạo task Jira (validate + gợi ý task mới)

> Trigger: "kiểm tra logwork", "soát task tạo có đúng không", "kiểm tra thời gian task tháng",
> "validate worklog", "task đủ giờ chưa", "gợi ý lịch tạo task" (confirm ý định trước khi chạy).
>
> Mục đích: soát các task ĐÃ TẠO trên Jira xem `startTime`/`dueTime`/`estimate` có hợp lệ để
> **logwork không bị chặn validation thời gian** không, rồi **gợi ý lịch tạo task mới**.
>
> 🔑 **Quy tắc nghiệp vụ (chốt với user):**
> - Áp cho issue type **Task / Sub-task** có field **Type = Normal** (OT/Effort KHÔNG bị cap → liệt kê riêng).
> - Mỗi NGÀY LÀM VIỆC (T2–T6) một người log tối đa **8h**; T7/CN không log. Chỉ log trong `[startTime, dueTime)` — **dueTime là biên LOẠI TRỪ**.
> - `dueTime` tối thiểu = ngày-làm-việc cuối (đủ chứa est ở 8h/ngày) **+ 1 ngày lịch**. Vd: start 01/06 est 8h → due 02/06; start 02/06 est 16h → due 04/06; xong T6 → due T7; tràn T6→T2 → due thứ Ba (T7/CN ở giữa bị bỏ qua).
> - Cho phép **chồng ngày** (chia giờ), chỉ báo lỗi khi **tổng giờ/người/ngày > 8h** (kiểm tra khả thi EDF water-fill).
>
> 🧰 **Đường dẫn tool (bản cài vs dev):** mỗi lệnh đặt biến trước:
> `T=tools; [ -e "$T/worklog-validator/validate_worklog.py" ] || T="$HOME/.claude/kora-framework/tools"`
> rồi gọi `python3 "$T/worklog-validator/validate_worklog.py" …` (Windows `py`, `%USERPROFILE%\.claude\kora-framework\tools`).

## Bước 0 — Kiểm tra dữ liệu & guard

- 🚫 **Guard gói USER:** có `.claude-knowledge-user` (hoặc `package.type: user`) → máy NGƯỜI DÙNG (không
  có nguồn Jira riêng) → báo nhẹ "máy này chỉ get&post KB chung" rồi DỪNG.
- Đọc `vault_path` từ `config/factory-config.yaml`. Vault chưa có note Jira (`source: jira`) → báo nhẹ +
  gợi ý **"quét jira"** trước (workflow 01). KHÔNG validate trên vault rỗng.
- Khuyến nghị: vault quét bằng bản CŨ (chưa có `startdate`/`work_type` trong frontmatter) → các task sẽ báo
  `MISSING_START`; **Bước 3 sẽ quét lại tháng đó** để bổ sung 2 field này nên không sao.

## Bước 0.4 — Cổng mật khẩu vận hành (KORA_OPS_PW)

> 🔒 Workflow này **kéo dữ liệu live** từ Jira và có thể **tạo task lên Jira** → PHẢI qua cổng vận hành TRƯỚC.
> Cùng cổng `/claude-knowledge-sync`, `/claude-knowledge-send-mail`, báo cáo — **KHÁC** mật khẩu archive.

`T2=tools; [ -e "$T2/archive-gate/verify_ops_password.py" ] || T2="$HOME/.claude/kora-framework/tools";
python3 "$T2/archive-gate/verify_ops_password.py"` (đọc env `KORA_OPS_PW` — **KHÔNG hỏi qua card, KHÔNG in**;
Windows `py`). **Exit ≠ 0 → DỪNG** (không quét, không validate, không tạo task).

## Bước 1 — HỎI THÁNG cần kiểm tra

**AskUserQuestion** (header ngắn "Tháng", single-select): liệt kê **tháng hiện tại + 2–3 tháng gần đây** làm
option (vd `2026-06`, `2026-05`, `2026-04`) + **ô "Other"** để gõ `YYYY-MM` bất kỳ. Lưu lại `<MONTH>`.

## Bước 2 — Chọn nguồn Jira → project → (tùy chọn) người

> 🛑 **HỎI TRƯỚC, cấm quét trước.** Chỉ quét sau khi đã qua cổng (Bước 0.4) VÀ user đã chọn nguồn + project.

1. **Nguồn Jira:** đọc `check_connection.py --list --json` → các entry `jira_*`/`atlassian`. **≥2 nguồn →
   AskUserQuestion** liệt kê từng nguồn (kèm MCP/API + domain) + **[Cả 2]**; **đúng 1 nguồn → dùng luôn**.
2. **Project:** lấy project của nguồn (API `import_jira.py --list-projects`; MCP `getVisibleJiraProjects`, phân
   trang lấy HẾT) → **AskUserQuestion liệt kê ĐẦY ĐỦ từng project + prefix nguồn** (vd `[Cloud·MCP] FA — …`),
   >4 project → **PHÂN TRANG** + **[✓ Tất cả]**. Lưu `<KEYS>`.
3. **Người (tùy chọn):** AskUserQuestion "Lọc theo người hay tất cả?" → **[Tất cả]** / liệt kê assignee (ô
   "Other" gõ tên). Lưu `<NAMES>` (rỗng = tất cả).

## Bước 3 — Quét Jira THÁNG đó (bổ sung startdate + work_type) rồi reindex

> 💡 **Đặt biến field TRƯỚC mọi lệnh `import_jira.py`** (từ `config > jira.*`; rỗng = tool tự dò theo tên field):
> `JIRA_START_FIELD=<config jira.start_field>` · `JIRA_WORKTYPE_FIELD=<config jira.worktype_field>` ·
> `JIRA_EFFORT_FIELD=<config jira.effort_field>`. Thiếu các field này thì validate sẽ báo MISSING_START / coi mọi task là Normal.

Phạm vi quét = các task **giao với tháng** `<MONTH>`. JQL gợi ý (đủ rộng để bắt task spanning):
`project in (<KEYS>) AND (due >= "<MONTH>-01" OR ("Start date" >= "<MONTH>-01" AND "Start date" <= "<MONTH>-31") OR updated >= "<MONTH>-01")`
(self-host không có field "Start date" theo tên → bỏ nhánh đó, để tool tự dò).

- **Nguồn MCP** (`searchJiraIssuesUsingJql`, `fields:["*all"]`) → lưu file → `getJiraIssue` 1 issue `expand=names`
  → `reports/_mcp-names.json` → **GHI VAULT**:
  `JIRA_START_FIELD=… JIRA_WORKTYPE_FIELD=… JIRA_EFFORT_FIELD=… python3 "$T/jira-to-obsidian/import_jira.py" --from-mcp <file> --names reports/_mcp-names.json`.
- **Nguồn API** (self-host/Cloud-API): `JIRA_BASE_URL=<base_url> [JIRA_AUTH_MODE=server] JIRA_START_FIELD=… JIRA_WORKTYPE_FIELD=… JIRA_EFFORT_FIELD=… python3 "$T/jira-to-obsidian/import_jira.py" --jql "project in (<KEYS>)"`.
- **Cowork sandbox chặn mạng:** (a) có MCP `run_command` → chạy lệnh THẲNG trên máy; (b) không → in lệnh
  copy-paste cho user chạy ở Terminal rồi quay lại.
- Reindex: `python3 "$T/kb-indexer/build_index.py" --root .`.

## Bước 4 — Validate + hiển thị dashboard (calendar timeline)

Chạy: `python3 "$T/worklog-validator/validate_worklog.py" --validate --month <MONTH> --vault "<vault_path tuyệt đối>"
[--project <KEYS>] [--assignee <NAMES>]` → JSON summary + ghi `reports/worklog-check-<MONTH>.json`,
`reports/worklog-check-latest.html`, `reports/worklog-timeline-<MONTH>.svg`.

**Hiển thị inline:** đọc `reports/worklog-timeline-<MONTH>.svg` → `mcp__visualize__show_widget` (widget_code = nội
dung SVG) để render **biểu đồ calendar timeline**. Kèm tóm tắt tiếng Việt từ JSON:
- Số task Normal, **N lỗi** cần sửa, **M người quá tải**.
- Bảng lỗi theo task: `key · người · start · due · est · loại lỗi · due gợi ý`. Các mã:
  **WINDOW_TOO_SMALL** (dueTime quá sớm — kèm due tối thiểu), **INVALID_WINDOW** (due ≤ start),
  **DAY_OVERLOAD** (tổng >8h/ngày — chồng task), **OVER_CAPACITY** (vượt năng lực tháng/người),
  **MISSING_START/DUE/EST**, **WEEKEND_START**, **DUE_SUGGEST** (due rộng hơn tối thiểu → có thể thu hẹp).
- Task OT/Effort liệt kê riêng (ngoài cap 8h).

Diễn giải bằng lời, gợi ý cách sửa từng task (đổi dueTime về mức tối thiểu / giãn window / dời người).

## Bước 5 — Gợi ý tạo task mới (tùy chọn)

**AskUserQuestion** "Tạo thêm task?": **[Có — gợi ý lịch]** / **[Không — dừng]**. Nếu Có:

1. **Thu thập task mới:** AskUserQuestion lặp — mỗi task hỏi **tên** (option gợi ý + ô "Other") rồi **est (giờ)**
   (option 4h/8h/16h/24h + ô "Other"); thêm option **[Xong — không thêm nữa]** để kết thúc. Gom `[{name, est_h}]`.
2. **Người + mốc bắt đầu:** hỏi **assignee** (mặc định người đang lọc) + **anchor** (mặc định ngày làm việc kế
   tiếp; ô "Other" gõ `YYYY-MM-DD`).
3. **Sinh gợi ý:** `python3 "$T/worklog-validator/validate_worklog.py" --plan --month <MONTH> --vault "<vault>"
   --assignee "<NGƯỜI>" --anchor <YYYY-MM-DD> --new-tasks '<json>'` → bảng `tên · est · start · due · số ngày`
   (đánh dấu "tràn tháng sau" nếu vượt năng lực) + **timeline cập nhật** (task gợi ý = thanh viền đứt tím) qua show_widget.
4. **AskUserQuestion** "Làm gì với gợi ý?": **[Chỉ xem / để tôi tự tạo]** vs **[Tạo trên Jira ngay]**.
   - **[Tạo trên Jira]** (đã qua cổng Bước 0.4 → ✋ confirm danh sách lần cuối): với mỗi task gọi MCP
     `createJiraIssue` — set `project=<KEY>`, `issueType=Task`, `summary=<tên>`, **Start date** (field `config
     jira.start_field`) = start, `duedate` = due, **estimate** (timetracking originalEstimate hoặc field
     `config jira.effort_field`) = est, **Type** (field `config jira.worktype_field`) = `Normal`. Báo lại key
     đã tạo. Lỗi field-id (Server tên field khác) → báo rõ + để user điền `config jira.*_field` rồi chạy lại.

## Guardrails

- **Không in token/secret.** Cổng `KORA_OPS_PW` đọc từ env, không qua chat.
- **Validate là READ-ONLY** (chỉ đọc vault + ghi `reports/`). Chỉ nhánh **[Tạo trên Jira]** mới ghi ra ngoài →
  luôn ✋ confirm danh sách trước khi tạo; KHÔNG tự tạo.
- **Idempotent đọc:** quét lại tháng ghi đè note (1 file/issue), không nhân bản.
- **Thiếu mốc:** task thiếu start/due/est → đánh dấu MISSING, KHÔNG tự bịa giá trị.
- **dueTime LOẠI TRỪ, bỏ T7/CN** — không trừ ngày lễ VN ở bản này (có thể thêm danh sách lễ ở config sau).

## Bước kế (đề xuất sau khi xong)

AskUserQuestion 1–4 lựa chọn: **[A] Kiểm tra tháng khác** · **[B] Báo cáo tiến độ dự án** (workflow 14) ·
**[C] Gửi mail kết quả cho PM** · **[D] Dừng**.
