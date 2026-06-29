---
description: Kiểm tra worklog/thời gian TẠO TASK trên Jira có đúng không. Quét 1 THÁNG → soát task Normal (Task/Sub-task có field Type=Normal): mỗi ngày tối đa 8h, dueTime phải đủ chứa estimate (bỏ T7/CN, biên loại trừ), năng lực tháng/người, xung đột tổng >8h/ngày → biểu đồ calendar timeline + bảng lỗi. Rồi GỢI Ý lịch tạo task mới (nhập tên+est → tự đề xuất start/due/est) + tùy chọn tạo thật trên Jira. Password-gated (operations password). Triggers (vi): «kiểm tra logwork», «soát task tạo có đúng không», «kiểm tra thời gian task tháng», «validate worklog», «task đủ giờ chưa», «gợi ý lịch tạo task» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-worklog-check` — kiểm tra tính hợp lệ thời gian (start/due/est) của task **Normal** đã tạo trên Jira theo THÁNG, vẽ biểu đồ calendar timeline, và gợi ý lịch tạo task mới. Chi tiết đầy đủ: `workflows/19-worklog-check.md`.

> 🛑🛑 **GIAO THỨC BẮT BUỘC — KHÔNG NHẢY BƯỚC, KHÔNG TỰ QUÉT/VALIDATE/TẠO TASK.** Khi mở skill này, thứ tự HỢP LỆ DUY NHẤT:
> **(1)** cổng mật khẩu `verify_ops_password.py`; **(2)** **AskUserQuestion HỎI THÁNG** (`YYYY-MM`); **(3)** **AskUserQuestion chọn NGUỒN Jira** (nếu ≥2) → **PROJECT** → (tùy chọn) **người**. **🛑 SAU mỗi câu → DỪNG, CHỜ user trả lời.**
> ⛔ **TUYỆT ĐỐI KHÔNG gọi tool nào khác trước khi user trả lời câu chọn tháng + nguồn** — CẤM ĐÍCH DANH:
> `check_connection.py`, `getVisibleJiraProjects`, `searchJiraIssuesUsingJql`, `import_jira.py`, `validate_worklog.py`, `build_index.py`, `createJiraIssue`.
> ❌ Nếu nghĩ "đã đủ dữ liệu, validate ngay" mà CHƯA hỏi tháng + nguồn trong phiên này → **ĐÓ LÀ LỖI**, quay về (2).

> 🚫 **Guard gói USER:** có `.claude-knowledge-user` ở gốc project (hoặc `package.type: user`) → máy NGƯỜI DÙNG, không có nguồn Jira riêng. Báo nhẹ *"Lệnh này cần nguồn Jira của HOST. Máy này chỉ đồng bộ KB chung."* rồi DỪNG.

Resolve path tool (bản cài ở CORE): `T=tools; [ -e "$T/worklog-validator/validate_worklog.py" ] || T="$HOME/.claude/kora-framework/tools"` (Windows `py`, `%USERPROFILE%\.claude\kora-framework\tools`).

1. 🔒 **CỔNG MẬT KHẨU vận hành (`KORA_OPS_PW`)** TRƯỚC — skill kéo dữ liệu live + có thể tạo task lên Jira:
   `python3 "$T/archive-gate/verify_ops_password.py"` (đọc env HOẶC `~/.config/claude-knowledge/ops-pw.env` — đặt 1 lần bằng `/claude-knowledge-ops-password`; **KHÔNG hỏi qua card, KHÔNG in**). Exit ≠ 0 → **DỪNG**.
2. **HỎI THÁNG** — AskUserQuestion (header "Tháng", single-select): tháng hiện tại + 2–3 tháng gần đây làm option + ô **"Other"** gõ `YYYY-MM`. Lưu `<MONTH>`.
3. **Chọn NGUỒN → PROJECT → (tùy chọn) NGƯỜI** — `check_connection.py --list --json` → entry `jira_*`/`atlassian`. ≥2 nguồn → AskUserQuestion (kèm MCP/API + domain); 1 nguồn → dùng luôn. Project: liệt kê ĐẦY ĐỦ + prefix nguồn (vd `[Cloud·MCP] FA — …`), >4 → phân trang + **[✓ Tất cả]**. Người: **[Tất cả]** / multi-select (ô "Other" gõ tên) → `<NAMES>`.
4. **QUÉT Jira THÁNG đó** (route theo nguồn — chi tiết WF19 Bước 3), **đặt env field TRƯỚC mọi `import_jira.py`** từ `config jira.*`:
   `JIRA_START_FIELD=<config jira.start_field>` · `JIRA_WORKTYPE_FIELD=<config jira.worktype_field>` · `JIRA_EFFORT_FIELD=<config jira.effort_field>` (rỗng = tool tự dò theo tên field).
   - **MCP** (`searchJiraIssuesUsingJql` `fields:["*all"]`, kết quả lớn MCP tự lưu file) → `import_jira.py --from-mcp <file>`; **API** → `import_jira.py --jql "project in (<KEYS>)"`. Cowork chặn mạng → ưu tiên MCP `run_command`; không có → bàn giao lệnh terminal. Reindex `build_index.py --root .`.
5. **VALIDATE + biểu đồ** — `python3 "$T/worklog-validator/validate_worklog.py" --validate --month <MONTH> --vault "<vault_path tuyệt đối>" [--project <KEYS>] [--assignee <NAMES>]` → JSON + `reports/worklog-check-latest.html` + `reports/worklog-timeline-<MONTH>.svg`.
   → Đọc SVG → `mcp__visualize__show_widget` render **biểu đồ calendar timeline** + tóm tắt tiếng Việt: N task lỗi, M người quá tải, bảng lỗi (key · người · start/due/est · loại lỗi · due gợi ý). Mã lỗi: **WINDOW_TOO_SMALL** (due quá sớm) · **INVALID_WINDOW** (due ≤ start) · **DAY_OVERLOAD** (tổng >8h/ngày) · **OVER_CAPACITY** (vượt năng lực tháng/người) · **MISSING_START/DUE/EST** · **WEEKEND_START** · **DUE_SUGGEST** (due rộng hơn tối thiểu). Task OT/Effort liệt kê riêng (ngoài cap 8h). Diễn giải + gợi ý cách sửa từng task.
6. **GỢI Ý TẠO TASK MỚI (tùy chọn)** — AskUserQuestion "Tạo thêm task?" [Có / Không]. Có → thu thập `[{name, est_h}]` (AskUserQuestion lặp, ô "Other" gõ tự do, có **[Xong]**) + assignee + anchor (ngày làm việc kế; ô "Other" gõ `YYYY-MM-DD`) → `validate_worklog.py --plan --month <MONTH> --vault "<vault>" --assignee "<NGƯỜI>" --anchor <YYYY-MM-DD> --new-tasks '<json>'` → bảng gợi ý start/due/est + timeline cập nhật (task gợi ý = thanh viền đứt).
   → AskUserQuestion **[Chỉ xem / để tôi tự tạo]** vs **[Tạo trên Jira ngay]**. Chọn tạo → (đã qua cổng) ✋ confirm danh sách → MCP `createJiraIssue` mỗi task (type Task, set Start date=`config jira.start_field`, `duedate`, estimate, Type=`config jira.worktype_field`=Normal) → báo key tạo. Lỗi field-id → báo + để user điền `config jira.*_field` rồi chạy lại.

**Guardrails:** không in token; validate là READ-ONLY (chỉ ghi `reports/`); chỉ nhánh [Tạo trên Jira] mới ghi ra ngoài → luôn ✋ confirm, KHÔNG tự tạo; thiếu mốc start/due/est → đánh dấu MISSING, KHÔNG bịa; dueTime LOẠI TRỪ, bỏ T7/CN (chưa trừ ngày lễ VN ở bản này).

**Bước kế (sau khi xong, AskUserQuestion header ≤12 ký tự):** [Kiểm tra tháng khác] · [Báo cáo tiến độ] · [Gửi mail kết quả cho PM] · [Dừng].
