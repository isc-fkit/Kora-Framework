---
description: Generate a progress report. Choose one or more projects (multi-select), filter by members, pull data for a chosen time range from the sources, then build the dashboard. Password-gated (operations password) since it pulls live data. Triggers (vi): «báo cáo tiến độ», «report tiến độ», «tiến độ dự án», «cập nhật tiến độ», «sinh dashboard» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork. Hỗ trợ ĐA LOẠI report: tiến độ (Jira/đa nguồn) · chi phí–hoá đơn (OCR ảnh) · custom template.
---

The user invoked `/claude-knowledge-daily-report` — build a progress report.

> 🛑🛑 **GIAO THỨC BẮT BUỘC — KHÔNG NHẢY BƯỚC, KHÔNG TỰ ĐỘNG QUÉT/BUILD.** Khi mở skill này, hành động HỢP LỆ DUY NHẤT,
> ĐÚNG THỨ TỰ: **(1)** cổng mật khẩu `verify_ops_password.py`; **(2)** **AskUserQuestion chọn LOẠI REPORT**
> (**5 loại** — Bước 1b: Tiến độ · Cuộc họp · Tiến độ+Meeting+Roadmap/OKR · Báo cáo tài chính · Custom); **(3)** nếu LOẠI = **Tiến độ** →
> **AskUserQuestion chọn NGUỒN — LIỆT KÊ ĐỘNG ĐẦY ĐỦ mọi nguồn ĐANG kết nối** (Jira mỗi instance · SharePoint · Google Sheet
> (Composio) · Local Excel — dựng từ `check_connection.py --list` + dò MCP; **>4 → phân trang**; multiSelect); nếu = **Hoá đơn/Custom**
> → nguồn là note `source: invoice` (nạp ảnh hoá đơn nếu chưa có, Bước 1b), KHÔNG hỏi nguồn. **🛑 SAU mỗi câu → DỪNG, CHỜ user.**
> ⛔ **TUYỆT ĐỐI KHÔNG SCAN/IMPORT/BUILD trước khi user trả lời câu chọn nguồn** — CẤM ĐÍCH DANH:
> `sharepoint_search`, `sharepoint_folder_search`, `getVisibleJiraProjects`, `searchJiraIssuesUsingJql`, `import_jira.py`,
> `import_excel.py`, `GOOGLESHEETS_BATCH_GET`, `build_report.py`, `read_resource`. **CHỈ ĐƯỢC** `check_connection.py --list --json`
> + `COMPOSIO_SEARCH_TOOLS` (dò `googlesheets` active) để **DỰNG CARD nguồn** — KHÔNG dùng để quét dữ liệu.
> ❌ Nếu bạn nghĩ "đã đủ dữ liệu, tạo báo cáo HTML ngay" mà **CHƯA hề gọi AskUserQuestion chọn nguồn** trong phiên này →
> **ĐÓ LÀ LỖI NGHIÊM TRỌNG**, dừng lại và quay về (2). 🔒 Backstop: `build_report.py` **TỪ CHỐI build** nếu vault có
> >1 nguồn mà thiếu `--source-ids` → bạn KHÔNG thể ra report khi chưa hỏi nguồn.
> 🧭 **TIẾP THEO trong giao thức (cũng KHÔNG nhảy bước):** **(4)** nếu nguồn = **SharePoint** → **BẮT BUỘC AskUserQuestion
> chọn FOLDER** (`sharepoint_folder_search`) **TRƯỚC khi quét** — Bước 2 nhánh [SharePoint], CẤM tự lấy "file mới nhất";
> **(5)** phân tích AI → **BẮT BUỘC SPAWN sub-agent chuyên biệt** (Bước 1.5: 3 con `operations:*` cho tiến độ · agent kế
> toán `data:analyze` cho tài chính · thư ký cho họp), KHÔNG tự viết khi có Agent tool; **(6)** gửi mail → tiêu đề **ĐỘNG
> theo LOẠI báo cáo** (vd "Báo cáo tiến độ — FMC — {date}" · "Báo cáo tài chính — …"), **KHÔNG `[Kora]`/"Claude AI"**
> (build_report ghi `reports/_subject-latest.txt`, send_report tự đọc khi bỏ `--subject`; header/footer mail dùng `reports.company`) + role qua cổng `--roles-confirmed`.

> 🚫 **Guard gói USER:** nếu có file `.claude-knowledge-user` ở gốc project (hoặc `package.type: user` trong config)
> → đây là máy NGƯỜI DÙNG, KHÔNG có báo cáo/gửi mail (chỉ HOST mới có). Báo nhẹ: *"Báo cáo & gửi mail
> chỉ chạy ở máy HOST. Máy này chỉ đồng bộ KB chung (get & post)."* rồi DỪNG, KHÔNG sinh report.

**Chọn NGUỒN → PROJECT (chi tiết, AskUserQuestion).** Resolve path tool (bản cài ở CORE):
`T=tools; [ -e "$T/connections/check_connection.py" ] || T="$HOME/.claude/kora-framework/tools"`.
1. 🔒 **CỔNG MẬT KHẨU vận hành (`KORA_OPS_PW`)** TRƯỚC — báo cáo kéo dữ liệu live nên PHẢI qua cổng:
   `python3 "$T/archive-gate/verify_ops_password.py"` (đọc env **HOẶC** `~/.config/claude-knowledge/ops-pw.env` — đặt 1 lần bằng
   `/claude-knowledge-ops-password`; **KHÔNG hỏi qua card, KHÔNG in**). Exit ≠ 0 → **DỪNG**, không kéo, không sinh report.
1b. **LUÔN HỎI — CHỌN LOẠI BÁO CÁO ngay sau cổng mật khẩu, TRƯỚC chọn nguồn** (AskUserQuestion BẮT BUỘC, header "Loại BC",
   single-select; **5 loại → PHÂN TRANG** rule #8: thẻ 1 = 3 mục + **[Khác — xem thêm]** → thẻ 2 phần còn lại). Mỗi loại = template + phân tích AI ĐÚNG chuyên ngành:
   **[Tiến độ (daily-report)] · [Cuộc họp (meeting)] · [Tiến độ + Meeting + Roadmap/OKR] · [Báo cáo tài chính (hoá đơn)] · [Custom template]**.
   > 🤖 **BẮT BUỘC — MỖI LOẠI BÁO CÁO SPAWN 1 SUB-AGENT CHUYÊN BIỆT phân tích KỸ, RÕ, đúng chuyên ngành** (Agent tool;
   >   không spawn được → Claude TỰ đóng đúng vai viết phân tích thật vào ĐÚNG file, KHÔNG bỏ phân tích, KHÔNG sinh báo cáo "chay").
   >   🎛️ **MODEL sub-agent (tối ưu thông minh × tốc độ) — truyền tham số `model` khi spawn:** **`sonnet`** cho agent
   >   ops (3 con tiến độ, song song) · kế toán · thư ký họp · bám-template (dữ liệu đã cấu trúc → cần NHANH, Sonnet đủ sâu);
   >   **`opus`** cho agent CHIẾN LƯỢC/PM (OKR-roadmap, Bước 5c) — suy luận sâu nhất. Môi trường KHÔNG hỗ trợ tham số
   >   `model` → bỏ qua, kế thừa model phiên (KHÔNG fail, KHÔNG dừng vì thiếu model).
   >   🔒 **CODE-GATE (không chỉ prose):** `build_report.py` **TỪ CHỐI build** khi thiếu phân tích: **invoice/custom** → die nếu
   >   thiếu `--ai <file>` (cổng `_ai_ok`); **meeting** → die nếu thiếu `_meeting-report.json`; **tiến độ** → `send_report` chặn gửi
   >   nếu khối AI còn placeholder. → LUÔN spawn agent → ghi file phân tích → build **với `--ai <file>`**. (`--ai-confirmed` CHỈ cho lịch nền.)
   >   • **Tiến độ** → 3 agent SONG SONG (model `sonnet`): ĐIỀU HÀNH (`operations:status-report`) · RỦI RO (`operations:risk-assessment`) · NĂNG LỰC (`operations:capacity-plan`) → gộp `reports/ai-analysis-latest.md`.
   >   • **Tài chính/hoá đơn** → agent KẾ TOÁN (model `sonnet`; báo cáo quý/bảng kê lớn → `opus`) (`data:analyze` + VAT/MST/khấu trừ/dòng tiền VN) → `reports/ai-invoice-latest.md`.
   >   • **Cuộc họp** → agent THƯ KÝ + PHÂN TÍCH HỌP (model `sonnet`) → `reports/_meeting-report.json` (10 mục — xem nhánh [Cuộc họp]).
   >   • **Tiến độ + Meeting + Roadmap/OKR** → agent CHIẾN LƯỢC/PM (model `opus`) (đọc `_okr-latest.txt` + `progress-data-latest.json`) → trường `analysis_md` / khối OKR.
   >   • **Custom template** → agent BÁM TEMPLATE (model `sonnet`) (`data:analyze`, đúng mục tiêu template) → `reports/ai-custom-latest.md`.
   >   Code-gate cưỡng chế: **meeting** đòi `_meeting-report.json` (build_report die nếu thiếu); **tiến độ** chặn gửi nếu khối AI còn placeholder (send_report). Mỗi loại = template + phân tích ĐÚNG chuyên ngành.
   - **[Tiến độ (daily-report)]** → tiếp Bước 2 (chọn 3 nhóm nguồn) như cũ; build mặc định `--report-type progress`.
   - **[Tiến độ + Meeting + Roadmap/OKR]** → báo cáo TIẾN ĐỘ (Bước 2) **+ mục Roadmap/OKR (5c)** + đọc file họp → gộp;
     build progress với roadmap=Có + `reports/_okr-blocks.json` (và/hoặc meeting-roadmap). Dành cho review điều phối PM tổng thể.
   - **[Báo cáo tài chính (hoá đơn)]** → **BỎ QUA Bước 2 (3 nhóm)**. Nguồn = note `source: invoice`. Nếu vault CHƯA có (kiểm thư mục `Invoices/`),
     lấy ảnh hoá đơn — **HỎI TỪNG BƯỚC qua AskUserQuestion, DỪNG chờ trả lời, KHÔNG TỰ ĐOÁN / KHÔNG tự lấy "file mới nhất":**
     **① Nguồn ảnh** (AskUserQuestion): **(a) kéo ẢNH vào chat** · **(b) folder LOCAL** (hỏi đường dẫn) · **(c) folder SHAREPOINT**.
     **② Nếu chọn SharePoint → HỎI 2 BƯỚC (như Bước 2a, TUYỆT ĐỐI không tự quét):** **(2a) HỎI FOLDER** — `sharepoint_folder_search`
     → AskUserQuestion liệt kê folder → user chọn FOLDER (ô "Other" = gõ keyword → `sharepoint_search query=`); **(2b) HỎI FILE** —
     `sharepoint_search folderName=<folder> fileType=png/jpg/pdf` → AskUserQuestion chọn (các) ảnh → `read_resource`/tải. >4 mục → phân trang (rule #8).
     → Claude **ĐỌC ảnh (OCR vision)** → xuất rows `reports/_invoice-rows.json` (cột: vendor, date, category, currency, subtotal, vat, vat_rate, total)
     → `python3 "$T/invoice-report/import_invoice.py" --from-rows reports/_invoice-rows.json --source-id invoice__<batch>` → reindex `build_index.py --root .`.
     **Rồi: (1)** NHÁNH TEMPLATE; **(2) AI phân tích — BẮT BUỘC SPAWN con agent KẾ TOÁN/TÀI CHÍNH** —
     `Agent(subagent dùng skill **data:analyze**, model `sonnet` — quý/bảng kê lớn → `opus`)`, prompt: *"Đóng vai CHUYÊN VIÊN KẾ TOÁN/TÀI CHÍNH (kiến thức kế toán VN:
     VAT·MST·khấu trừ thuế đầu vào·dòng tiền), dùng skill `data:analyze`. Đọc `reports/_invoice-rows.json`
     (vendor·date·category·subtotal·vat·vat_rate·total). Viết MARKDOWN các mục DƯỚI — trích SỐ cụ thể (đồng·%·tháng·NCC),
     CẤM chung chung — ghi ra `reports/ai-invoice-latest.md`."* (**fallback:** không có Agent tool → Claude tự viết):
     `## 📌 Tóm tắt điều hành` · `## 📊 Cơ cấu chi theo khoản mục` · `## 🧾 Thuế GTGT & khấu trừ đầu vào` (đối chiếu theo thuế suất) ·
     `## 🔴 Rủi ro` (tập trung nhà cung cấp, dòng tiền theo tháng, hoá đơn hợp lệ/đủ MST, thuế suất bất thường) · `## 🎯 Đề xuất`
     → build kèm `--ai reports/ai-invoice-latest.md`. **Report tài chính tự có:** KPI (tiền hàng chưa VAT · thuế GTGT · tổng thanh toán) ·
     **bảng TỔNG HỢP THUẾ GTGT theo thuế suất** · bảng theo khoản mục · tổng hợp theo NCC · biểu đồ cơ cấu & theo tháng · bảng kê chi tiết — chuẩn kế toán.
   - **[Cuộc họp (meeting)]** → nguồn = BIÊN BẢN HỌP. Nếu chưa có: user kéo file họp (.pptx/.docx/ảnh/text), HOẶC chọn từ
     SharePoint (`sharepoint_search` → `read_resource`), HOẶC **Outlook** (`outlook_calendar_search` lịch họp / `outlook_email_search`
     email họp) → Claude ĐỌC + TÓM TẮT (AI) thành `reports/_meeting-rows.json`
     (list: `title/date/attendees/summary/decisions[]/action_items[]/risks[]`) → `python3 "$T/meeting-report/import_meeting.py"
     --from-rows reports/_meeting-rows.json --source-id meeting__<batch>` (lưu vault `type: meeting`) + reindex.
     **BẮT BUỘC SPAWN con Agent THƯ KÝ + PHÂN TÍCH HỌP** (Agent tool, model `sonnet` — vai thư ký cuộc họp + phân tích chiến lược: đọc
     `reports/_meeting-rows.json` + đối chiếu **task Jira/OKR** trong vault + **so biên bản CŨ** nếu có) → con agent GHI
     **`reports/_meeting-report.json`** — 1 OBJECT JSON **ĐẦY ĐỦ 10 MỤC** (đừng bỏ mục nào có dữ liệu):
     `title` · `subtitle` · `period` · `source_label` · `scope` · `report_date` · `executive_summary` (prose, dùng `**đậm**` được) ·
     `kpis[{n,l}]` · `decision_callout` · `decisions[]` · `action_items[{task,pic,deadline,status}]` ·
     `progress_by_team[{team,items[]}]` · `risks[{id,title,impact,mitigation}]` · `okr_alignment[{okr,link,level}]` ·
     `history_comparison` (prose) · `priorities_by_day[{date,items}]` · `sources[]`.
     (Không spawn được Agent → Claude **tự đóng vai agent này**, viết ĐỦ 10 mục — KHÔNG bỏ mục.) Build báo cáo CHI TIẾT:
     `python3 "$T/progress-report/build_report.py" --report-type meeting-roadmap --meeting-report reports/_meeting-report.json`
     → ra `reports/meeting-roadmap-latest.html` (10 mục: tóm tắt điều hành+KPI+callout · quyết định · action items BẢNG (PIC/deadline/chip) ·
     tiến độ theo tổ · rủi ro (tác động/giảm thiểu) · OKR/roadmap BẢNG · đối chiếu lịch sử · ưu tiên theo ngày · nguồn — **email-safe inline**).
     > 🔒 **Backstop (code-gate):** thiếu `_meeting-report.json` **VÀ** `_meeting-rows.json` → `build_report` **TỪ CHỐI (die)** đòi spawn agent trước → KHÔNG build báo cáo rỗng. (`_meeting-rows.json` là fallback GỌN nếu chưa có agent chi tiết.)
   > 📧 Gửi report Cuộc họp: report Meeting ĐÃ **inline-styled (email-safe, GIỐNG báo cáo tài chính)** → gửi THẲNG làm BODY (giữ nguyên card/KPI ở Gmail/Outlook):
   >   `send_report.py --html-file reports/meeting-roadmap-latest.html --attach reports/meeting-roadmap-latest.html --transport auto` (qua cổng `KORA_OPS_PW`).
   >   **ƯU TIÊN `run_command` (local terminal)**: `--transport auto` thử **SMTP trước → fail mạng (proxy FPT chặn) thì TỰ fallback Gmail API/OAuth2 HTTPS 443 qua proxy**. Tiêu đề tự đọc `reports/_subject-latest.txt` (`Báo cáo cuộc họp — …`). **KHÔNG** dùng `email-body-latest.html` (đó là body report TIẾN ĐỘ).
   - **[Custom template]** → BẮT BUỘC chọn/tạo template (nhánh dưới) → build `--report-type custom --template <name>`.
   **NHÁNH TEMPLATE (cho Hoá đơn/Custom) — AskUserQuestion header "Template":** liệt kê template có sẵn đọc từ
   `templates/reports/_index.json` (mỗi `name`+`title` = 1 option) + **[Mặc định]** (chỉ Hoá đơn) + **[Tạo mới]** (rule #8: >4 → phân trang).
   - **[Tạo mới] = full workflow chuyên nghiệp:** Claude DỰNG file template HTML dùng placeholder
     `{{TITLE}} {{PERIOD}} {{N}} {{KPIS}} {{CHART_CATEGORY}} {{CHART_MONTH}} {{TABLE_VENDORS}} {{TABLE_INVOICES}} {{TOTAL}} {{SUBTOTAL}} {{VAT}}`
     → **PREVIEW cho user (visualize) → CHỜ user CHỐT** (sửa tới khi ưng) → lưu `templates/reports/<name>.html`
     + thêm entry `_index.json` (`name`/`base: invoice`/`file`/`title`). **CHƯA chốt → KHÔNG build.**
   - **(Custom) AI phân tích — SPAWN con agent PHÂN TÍCH bám TEMPLATE** (Agent tool, model `sonnet` + skill `data:analyze`: đọc dữ liệu nguồn
     `reports/_invoice-rows.json` / note `source: invoice`, bám đúng loại dữ liệu & mục tiêu của template đã chọn) → viết
     `reports/ai-custom-latest.md` (`## 📌 Tóm tắt` · `## 📊 Phát hiện chính` · `## 🔴 Rủi ro` · `## 🎯 Đề xuất`; không spawn được Agent → Claude tự viết).
   - Build Hoá đơn/Custom: `python3 "$T/progress-report/build_report.py" --report-type <invoice|custom> [--template <name>]
     --source-ids "invoice__<batch>" --ai reports/ai-<invoice|custom>-latest.md` → ra `reports/invoice-report-latest.html`.
   > 🔒 Backstop: `--report-type custom` TỪ CHỐI nếu thiếu `--template`; template lạ → lỗi liệt kê tên có sẵn.
   > 📧 Gửi report Hoá đơn/Custom: report ĐÃ **inline-styled (email-safe)** → gửi THẲNG làm BODY (giữ nguyên định dạng ở Gmail/Outlook):
   > `send_report.py --html-file reports/invoice-report-latest.html --attach reports/invoice-report-latest.html` (qua cổng `KORA_OPS_PW`).
   > **KHÔNG** dùng `email-body-latest.html` ở đây (đó là body của report TIẾN ĐỘ, không phải tài chính).
2. **(CHỈ khi LOẠI report = Tiến độ) — HỎI NGUỒN, LIỆT KÊ ĐỘNG ĐẦY ĐỦ mọi nguồn ĐANG kết nối, multiSelect=true.**
   **① DỰNG DANH SÁCH nguồn (chỉ ĐỌC, KHÔNG scan/import):**
   - `check_connection.py --list --json` → MỖI entry Jira (`jira_*`/`atlassian`) = 1 mục, nhãn rõ instance:
     `[Jira·API] jira.fptmedicare.vn` / `[Jira·MCP] foxproject`. (2 Jira = 2 mục riêng, KHÔNG gộp.)
   - **SharePoint** → mục `[SharePoint]` nếu **M365 MCP khả dụng** (có tool `sharepoint_search`/`sharepoint_folder_search`) —
     connector M365 KHÔNG nằm trong `connections:`, đừng vì "không thấy trong sổ" mà bỏ.
   - **Google Sheet (Composio)** → mục `[Google Sheet (Composio)]` nếu `COMPOSIO_SEARCH_TOOLS` báo toolkit `googlesheets` ACTIVE.
   - **Local Excel** → mục `[Local Excel]` (entry `excel__local` hoặc luôn cho phép nhập đường dẫn .xlsx).
   **② AskUserQuestion multiSelect** liệt kê **ĐÚNG các nguồn tìm được** (mỗi nguồn 1 option, kèm nhãn method) + **[Tất cả]**.
   - **>4 nguồn → PHÂN TRANG** (3 mục + `[Khác — xem thêm]` → lượt kế), **KHÔNG nhồi >4 option/thẻ** (rule #8).
   - ⛔ Chỉ ĐỌC registry/COMPOSIO_SEARCH để DỰNG card — **KHÔNG** getVisibleJiraProjects / sharepoint_search folder /
     import_* / BATCH_GET / build_report TRƯỚC khi user chọn. **KHÔNG** để single-select. **KHÔNG** tự chọn rồi chạy.
   - Đây là câu ĐẦU TIÊN sau cổng mật khẩu. (Chỉ bỏ hỏi khi có ĐÚNG 1 nguồn khả dụng.)
2a. **Với MỖI NGUỒN đã chọn ở Bước 2 → DRILL chi tiết** (project / folder+file / tab):
   - **[Jira·API|MCP] `<instance>`** → chọn **PROJECT** trong đúng instance đó: API → `import_jira.py --list-projects` (env instance) ·
     MCP → `getVisibleJiraProjects` → AskUserQuestion multi-select project (+ **[Chọn tất cả]**).
   - **[SharePoint] — BẮT BUỘC HỎI 2 BƯỚC, TUYỆT ĐỐI KHÔNG tự quét "file mới nhất":**
     **① HỎI FOLDER**: `sharepoint_folder_search` → AskUserQuestion liệt kê các folder → user chọn **(các) FOLDER** (multi-select; >4 → phân trang).
       - 🔎 **Ô "Other" = TÌM THEO KEYWORD/TÊN.** Nếu user gõ chữ vào ô "Other" (vd `standing meeting`, `report Q2`) →
         coi là **từ khóa tìm** → chạy `sharepoint_search query="<keyword>"` (tìm theo TÊN trên toàn site, không cần folder) →
         AskUserQuestion liệt kê **kết quả khớp** → user chọn file. Dùng khi user biết tên/keyword (nhanh hơn duyệt folder).
     **② HỎI FILE trong folder đó**: `sharepoint_search folderName=<folder>` liệt kê file → AskUserQuestion cho user chọn **(các) file**.
       - 🔎 **Ô "Other" ở đây cũng = keyword/tên file** → `sharepoint_search query="<keyword>" folderName=<folder>` (hoặc bỏ folderName để tìm toàn site) → liệt kê khớp → chọn.
     1 folder có thể có **file REPORT (task data → import thành note)** và/hoặc **file MEETING/Standing-Meeting/OKR (.pptx/.docx — đọc làm BỐI CẢNH roadmap, KHÔNG import task)** — **để user chọn loại nào / cả 2**. KHÔNG tự đoán, KHÔNG tự lấy bản mới nhất.
   - **[Local Excel]** → entry `excel__local` (hoặc hỏi đường dẫn .xlsx qua ô "Other") → chọn file.
   - **[Google Sheet (Composio)]** → hỏi **spreadsheet** (AskUserQuestion: dán **URL/ID** vào ô "Other", hoặc gõ **TÊN** →
     `GOOGLESHEETS_SEARCH_SPREADSHEETS` liệt kê chọn); nhiều tab → `GOOGLESHEETS_GET_SHEET_NAMES` → hỏi chọn **tab**. Token nguồn
     = `gsheet_<tên>`. ⚠️ Composio = **TƯƠNG TÁC** (MCP) — **KHÔNG dùng cho lịch nền** (nền headless dùng Jira/SharePoint-Graph/Local). Import ở nhánh `source_type: gsheet`.
   > **>4 mục → phân trang** (rule #8). Xong nhóm này mới sang nhóm kế.
   > 🏷️ **GHI NHỚ TOKEN NGUỒN của mỗi lựa chọn** (để báo cáo CHỈ gồm nguồn đã chọn — user xác nhận "Chỉ nguồn đã chọn"):
   > **[Jira]** → token `jira`; **mỗi file SharePoint/Local** → import với `--source-id` RÕ RÀNG, nhất quán (vd
   > `sp_<folder>`, `local_<tên-file>`) → token = đúng id đó. Gom thành `SRC_IDS` (phẩy) → truyền `--source-ids "<SRC_IDS>"` ở Bước 6.
   > ⚖️ **CHỈ GỘP khi chọn ≥2 nhóm.** Chọn **1 nhóm** → báo cáo **CHỈ nhóm đó** (vd chỉ SharePoint → KHÔNG tự kéo
   > thêm Jira, KHÔNG nói "kết hợp Jira + SharePoint"). Chọn ≥2 → gộp ĐÚNG các nhóm đã chọn (qua `--source-ids`).
2b. **Chọn PHẠM VI báo cáo (quan trọng với DỰ ÁN LỚN — không lấy hết)** — AskUserQuestion:
   **[Sprint đang chạy] (khuyến nghị) / [N ngày gần đây — mặc định 30, ô "Other" tự nhập] / [Toàn bộ]**.
   → đặt `SCOPE` ∈ `sprint|recent|all`, `NDAYS` (mặc định 30). `SCOPE≠all` → **bound scan** (nhẹ) + lọc report.
3–4. **VỚI MỖI nguồn đã chọn → quét bằng ROUTE RIÊNG (vòng lặp), tích lũy vào CÙNG vault** (đọc `method`/`source_type`/
   `base_url`/`creds` từ `--json`):
   - **`method: api`** (jira_server/jira_cloud): đặt env CHO ĐÚNG instance ở đầu lệnh — `JIRA_BASE_URL=<entry.base_url>`
     (+ `JIRA_AUTH_MODE=server` nếu `jira_server`; token: `creds.kind=dotenv` → `JIRA_ENV_FILE=<dotenv_path>`, `kind=env`
     → token đã ở shell env). Liệt kê: `import_jira.py --list-projects` → multi-select project (hoặc [Tất cả]). FULL-scan:
     `import_jira.py --jql "project in (<KEYS>)<+ AND updated >= -<NDAYS>d nếu SCOPE≠all>"` (KHÔNG `--since` → hết status/comment, ghi đè, không nhân bản).
   - **`method: mcp`** (`atlassian`/`jira_cloud`): **DÙNG MCP TOOL, KHÔNG import_jira API** — `getVisibleJiraProjects`
     (liệt kê project → multi-select) → `searchJiraIssuesUsingJql` `project in (<KEYS>)<+ AND updated >= -<NDAYS>d nếu SCOPE≠all>` `fields:["*all"]` (kết quả lớn MCP
     tự lưu file → dùng path đó) + `getJiraIssue expand=names` (map field) → `import_jira.py --from-mcp <file> --names <names>`.
   - ⚠️ Chọn nguồn **MCP** thì **BẮT BUỘC** đi nhánh MCP — đừng im lặng chạy import_jira API (sẽ trúng nguồn/domain khác → thiếu project, lỗi "không có note").
   - **`source_type: excel` (method `local_file`)** → `python3 "$T/excel-to-obsidian/import_excel.py" --file <entry.file_path> [--sheet <entry.sheet_name>] --source-id <entry.id> [--project <KEY>] [--map '<json nếu cột lạ>']`. Tự nhận cột Việt/Anh; ghi note `source: excel` vào `07_Imported/<id>/` (idempotent).
   - **`source_type: sheet`/`excel` (method `mcp`) — SharePoint 365, 2 cách:**
     **① MCP + CSV (không cần Graph token):** file để dạng **.csv** → `sharepoint_search fileType="csv"` → `read_resource` (trả **text CSV nguyên vẹn**) → Claude ghi `reports/_sheet-<id>.csv` → `python3 "$T/excel-to-obsidian/import_excel.py" --from-rows reports/_sheet-<id>.csv --map … --source-id <id>`. (read_resource đọc CSV CHUẨN; chỉ .xlsx mới lệch cột.)
     **② Graph cho .xlsx:** `sharepoint_search fileType="xlsx"` → URI `file:///{driveId}/{itemId}` → `import_excel.py --graph-item "<driveId>/<itemId>"` (Graph token creds `SHAREPOINT_*` app **Sites.Read.All** → `/content` → parse ô chuẩn). App-only Sites.Read.All chạy được cả nền.
     ⚠️ KHÔNG dùng read_resource lấy ô của .xlsx (text lệch cột). **Google Sheet (cách cũ, không cần Composio)**: Publish-CSV → `--from-url`.
   - **`source_type: gsheet` (method `composio`) — Google Sheet qua Composio (TƯƠNG TÁC, KHÔNG cần Publish-CSV):**
     `COMPOSIO_SEARCH_TOOLS` (use_case "read google sheet") kiểm toolkit `googlesheets` ACTIVE (chưa → `COMPOSIO_MANAGE_CONNECTIONS`
     add googlesheets) → `GOOGLESHEETS_BATCH_GET` `{spreadsheet_id:"<ID/URL>", ranges:["<Tab>!A1:Z10000"], valueRenderOption:"UNFORMATTED_VALUE"}`
     → **chuẩn hoá ragged rows** (hàng đầu = header; pad mỗi hàng theo độ dài header — pitfall Composio: hàng trống/thiếu cột) →
     Claude ghi `reports/_sheet-<id>.csv` → `python3 "$T/excel-to-obsidian/import_excel.py" --from-rows reports/_sheet-<id>.csv
     --map '<json nếu cột lạ>' --source-id gsheet_<id> [--project <KEY>]` → note `source: excel` (idempotent). Sheet lớn → đọc **theo
     khối 10000 dòng** (grid-limit + rate 60 reads/phút). Token nguồn = `gsheet_<id>` (gom vào `SRC_IDS`).
   Quét xong HẾT các nguồn → reindex **1 lần** `build_index.py --root .`. **Report trên UNION (Jira + Excel) vừa kéo** (task đã Done/đổi trạng thái sẽ đúng).
   > ⚠️ Nhiều domain **trùng mã project/issue** → vault đè nhau (giới hạn đã biết). Khác mã thì gộp thoải mái.
5. **THÀNH VIÊN của (các) project — LUÔN HỎI** (nhiều dự án, mỗi người gắn 1 dự án → KHÔNG tự dùng / KHÔNG tự đoán):
   AskUserQuestion (header "Thành viên"): **[Dùng danh sách đã lưu cho project này] / [Điều chỉnh lại]**.
   - **[Dùng list cũ]** → đọc `reports.project_members.<KEY>` (list thành viên đã lưu ĐÚNG project đó) → lọc/ngữ cảnh report theo đó.
   - **[Điều chỉnh lại]** → AskUserQuestion **multi-select** (assignee lấy từ data quét + ô **"Other"** gõ tên) → chọn thành viên đưa vào báo cáo
     → **LƯU LẠI `reports.project_members.<KEY>`** cho lần sau (mỗi project 1 list riêng). >4 → phân trang; có **[Chọn tất cả]**.
   - **VAI TRÒ hỏi ở Bước 5b (BẮT BUỘC)** — Bước 5 này chỉ chọn THÀNH VIÊN. Rồi hỏi **khoảng thời gian** (nếu cần).
5b. **VAI TRÒ thành viên — BẮT BUỘC HỎI/XÁC NHẬN TRƯỚC KHI BUILD (workflow 14 Bước 0.6).** Vai trò quyết định cách chấm
   (Dev đo giờ-công; **PM/PO & QC KHÔNG đo giờ** → bỏ qua sẽ bị chấm "thiếu giờ" SAI). **KHÔNG được bỏ qua / KHÔNG auto im lặng:**
   - **Config `reports.pm_members`/`qc_members` ĐÃ CÓ** → **vẫn HIỆN ra + AskUserQuestion [Dùng đúng vậy] / [Điều chỉnh]**
     (xác nhận nhanh, KHÔNG hỏi lại từ đầu). [Điều chỉnh] → hỏi như nhánh dưới.
   - **Config TRỐNG** → **BẮT BUỘC AskUserQuestion** (multi-select + ô **"Other"** gõ tên): **"Ai là PM/PO?"** (chỉ điều
     phối, tạo Epic/Request/US, KHÔNG log task → `reports.pm_members`) · **"Ai là QC?"** (tạo Bug → `reports.qc_members`); còn lại **Dev**.
   - Gán xong → **GHI inline list** vào `config/factory-config.yaml` mục `reports:` (`pm_members: ["A","B"]` / `qc_members: ["C"]`) → build lại (lần sau chỉ xác nhận).
   - **NẾU user xác nhận tất cả là Dev** (không PM/QC) → truyền **`--roles-confirmed`** cho `build_report.py` (build_report vẫn tự nhận diện PM/QC theo dấu hiệu).
   - 🔒 **CODE-GATE:** `build_report.py` **TỪ CHỐI build** report tiến độ (>1 người) khi CHƯA khai role trong config **VÀ** thiếu `--roles-confirmed` → KHÔNG thể lỡ bỏ qua câu hỏi này.
   ⚠️ **PM/QC KHÔNG đo bằng giờ-công, KHÔNG cảnh báo "chưa log giờ", loại khỏi capacity team** — chỉ đánh giá theo điều phối/chất lượng.
   > 👤 **HỎI RÕ "Ai là PM dự án?"** (1 người) — để AI phân tích theo góc PM + roadmap điều phối, query đúng người. Ghi `reports.pm_members` (đứng đầu).
5c. **HỎI: "Có phân tích ROADMAP không?"** — AskUserQuestion [Có / Không].
   - **Có** → báo cáo thêm mục **🗺️ Roadmap & điều phối sprint** (build_report đã sinh section roadmap: backlog/current/next + SP).
   - Nếu nhóm SharePoint/Local có chọn **file MEETING/Standing Meeting/OKR/chiến lược** (kể cả **.pptx/.docx** như
     `Standing Meeting - RD - 06.2026 - W4.pptx`) → ĐỌC nội dung (SharePoint: `read_resource` trả text trích xuất —
     đủ dùng cho .pptx/.docx; hoặc `--from-url`; local: đọc trực tiếp/`workflow 02`). **File meeting/OKR = ĐỌC LÀM
     CONTEXT, KHÔNG import thành task/note** (khác file REPORT task data). Sau đó:
     - 📋 **LẬP `reports/_okr-blocks.json`** (Claude cấu trúc từ nội dung file) → build_report render **section RIÊNG**
       (grid chia nhóm + khối AI phân tích riêng) ở **CẢ dashboard LẪN email**. Schema:
       `{"title": "...", "source": "SharePoint", "groups": [{"icon":"🔬","label":"RD / Solution","items":[{"name":"Insulin Tool","chips":["Log insulin 18-25/06",{"text":"Câu hỏi BS/BN","tone":"warn"}]}]}], "analysis_md": "## 🔴 Rủi ro\\n...\\n## 📌 Tóm tắt\\n..."}`.
       `tone` ∈ `ok|warn|risk|info` (màu chip) — bỏ trống = trung tính. `analysis_md` = phân tích AI RIÊNG cho OKR/chiến lược.
       **SPAWN con agent CHIẾN LƯỢC/PM** (Agent tool, model `opus` — suy luận sâu nhất: đóng vai PM/chiến lược; đọc `reports/_okr-latest.txt` BỐI CẢNH +
       `reports/progress-data-latest.json` tiến độ) → viết phân tích (insight · 🔴 rủi ro lộ trình · ĐỐI CHIẾU OKR ↔ tiến độ
       sprint · bốc task vào sprint kế · phụ thuộc), theo góc **PM đã hỏi** → Claude đưa nội dung agent vào trường
       `analysis_md` (không spawn được Agent → Claude tự viết). **Mỗi nhóm/đầu việc chia rõ cho dễ nhìn.**
     - Cũng lưu `reports/_okr-latest.txt` (text thô) làm **BỐI CẢNH** cho mục 🗺️ Roadmap của AI chính (Bước 1.5).
6. **BẮT BUỘC dựng báo cáo QUA `build_report.py` — TUYỆT ĐỐI KHÔNG tự viết file HTML báo cáo bằng tay.**
   `python3 "$T/progress-report/build_report.py" --source-ids "<SRC_IDS>" --projects "<KEYS>" --scope <SCOPE> --recent-days <NDAYS> [--members "<MEMBERS Bước 5>"] [--roles Dev,QC] [--roles-confirmed]`
   - **`--members "<list>"`** (tên, csv) / **`--roles Dev,PM,QC`**: lọc phần **"theo thành viên"** chỉ hiện người/vai trò đã chọn ở Bước 5 (tổng project GIỮ NGUYÊN). Bỏ qua = hiện tất cả.
   - **`--roles-confirmed`**: BẮT BUỘC kèm khi Bước 5b user xác nhận **tất cả là Dev** (config chưa có pm/qc) — nếu không, build_report TỪ CHỐI (code-gate vai trò). Đã gán role vào config thì KHÔNG cần cờ này.
   (per `workflows/14-progress-report.md`) → ra dashboard CHUẨN (có **banner**, đủ section: trạng thái · theo người ·
   complexity · **🗺️ Roadmap/Sprint** · capacity · rủi ro) + `email-body-latest.html` + `email-preview-latest.html`.
   - **`--source-ids "<SRC_IDS>"` BẮT BUỘC khi user chọn nguồn cụ thể** → báo cáo **CHỈ gồm nguồn đã chọn** (vault có thể
     còn note Jira cũ + import khác; không lọc thì mail ra **dữ liệu cũ/lẫn nguồn**). `jira` = mọi note Jira; `<source_id>` = đúng lần import đó.
   - MỌI nguồn (Jira/SharePoint/Excel) phải **import vào vault rồi build_report** — kể cả khi GỘP nhiều nguồn (đừng ghép HTML tay → mất banner + sai layout).
   > 🖥️ **PREVIEW CẢ HAI trong Cowork** (workflow 14 Bước 2): hiện **dashboard** (`progress-report-latest.html`, tương tác)
   > **VÀ** **email** (`email-preview-latest.html` — banner nhúng base64 nên XEM ĐƯỢC tại chỗ) để user duyệt mail trước khi gửi.
   > Đừng chỉ preview dashboard. (File GỬI vẫn là `email-body-latest.html` — banner→CID lúc send.)
   > 📧 **Banner mail**: gửi qua `send_report.py` (tự nhúng `cid:kora-banner` từ `assets/banner-daily-report.jpg`) → Outlook hiện banner. Đừng bỏ qua send_report.
- Dashboard + email PHẢI có khối **🤖 AI analysis** (workflow 14 — Bước 1.5) — **PHÂN TÍCH SÂU, CHI TIẾT, đủ BẢNG số
  liệu** (chuẩn = bằng/hơn mẫu báo cáo đầy đủ). BẮT BUỘC, mỗi mục **trích DỮ LIỆU cụ thể (mã hạng mục · giờ · % · ngày), CẤM nói chung chung**:
  - 🤖 **BẮT BUỘC SPAWN 3 CON AGENT QUẢN LÝ (Agent tool — spawn SONG SONG cùng 1 lượt, mỗi con model `sonnet` (song song → tổng thời gian = 1 con, Sonnet đủ sâu cho dữ liệu đã cấu trúc), mỗi con 1 góc; đều đọc `reports/progress-data-latest.json`):**
    **Agent Điều hành/Status** (skill `operations:status-report`) → 📌 tóm tắt điều hành + 🎯 hành động ưu tiên + KPI ·
    **Agent Rủi ro** (skill `operations:risk-assessment`) → 🔴/🟡 rủi ro (số · mức độ · dự đoán bằng số · giảm thiểu) ·
    **Agent Năng lực** (skill `operations:capacity-plan`) → 👥 cân bằng tải Dev + 📅 dự đoán sprint (PM/QC theo VAI TRÒ, không đo giờ).
    → **TỔNG HỢP** output các con agent thành `reports/ai-analysis-latest.md` (đủ mục dưới). (Không có Agent tool → Claude tự viết như cũ.)
  - **🔴/🟡 Rủi ro**: đánh SỐ + **Mức độ** + **Dự đoán & lý do BẰNG SỐ** (giờ remaining, %done, ngày trễ, est/spent) + **Tác động** + **Phương án + AI(ai) + KHI NÀO** (mốc ngày).
  - **👥 Theo thành viên**: BẢNG `| Thành viên | Vai trò | Tổng | Done | %Done | Giờ log | %Capacity | Bug | Ghi chú |` + nhận xét cân bằng tải.
    🎚️ **PHÂN TÍCH THEO VAI TRÒ — TUYỆT ĐỐI KHÔNG áp rule Dev cho PM/QC** (PM/QC `%Capacity` = "—", đừng phạt):
    · **Dev** → đo **giờ-công · %capacity · %done · cân bằng tải** (cảnh báo nếu thiếu/quá tải/chưa log giờ).
    · **PM/PO** → KHÔNG đo giờ/capacity/%done, KHÔNG cảnh báo "chưa log giờ"; đánh giá theo **ĐIỀU PHỐI** (số Epic/Request/US tạo · roadmap · sắp sprint · gỡ blocker · chất lượng phân rã yêu cầu).
    · **QC** → KHÔNG đo giờ/capacity như Dev; đánh giá theo **CHẤT LƯỢNG** (số Bug tìm/tạo · bug nghiêm trọng · re-open · độ phủ test) — KHÔNG phạt vì "ít giờ log / %capacity thấp".
  - **🧩 Complexity**: 3 việc khó nhất (mã·người·trạng thái) + phân bố điểm + ai đang ôm cụm khó.
  - **📅 Sprint/timeline**: dự đoán từng sprint kèm số (quỹ giờ, carry-over) **+ (nếu roadmap) 🗺️ Roadmap & điều phối**: backlog/current/next, **bốc task nào vào sprint kế** + sắp xếp sprint hiện tại, gắn OKR/chiến lược (`reports/_okr-latest.txt`), theo góc **PM đã hỏi**.
  - **🎯 Hành động ưu tiên** (theo ngày) + **📌 Tóm tắt điều hành**.
  Viết từ DỮ LIỆU, không bịa → ghi `reports/ai-analysis-latest.md` → `build_report.py --inject-ai reports/ai-analysis-latest.md`
  (đưa vào CẢ email-body, email-preview LẪN dashboard).
> 📧 **THÂN MAIL (BẮT BUỘC) = `reports/email-body-latest.html`** (bản tóm tắt CÓ BANNER + đủ section, do build_report sinh).
> **TUYỆT ĐỐI KHÔNG lấy `progress-report-latest.html` (dashboard/"processing") làm thân mail** — đó CHỈ là **file ĐÍNH KÈM**.
> Lấy nhầm dashboard làm thân mail = **mất banner + sai UI** (đúng lỗi đang gặp). Luôn: `--html-file reports/email-body-latest.html
> --attach reports/progress-report-latest.html`. Và **KHÔNG tự dán/chế nội dung mail** — chỉ gửi đúng file email-body qua `send_report.py`.
- **Sau khi sinh report → đề xuất GỬI MAIL (AskUserQuestion, header ≤12 ký tự vd "Gửi mail"): [Gửi mail ngay] / [Dừng].**
  - **[Gửi mail ngay]** → luồng GỬI của `/claude-knowledge-send-mail` ([Gửi ngay]): cổng `KORA_OPS_PW` →
    **NGƯỜI NHẬN + TIÊU ĐỀ — LUÔN HỎI** (per-project): AskUserQuestion **[Dùng list email đã lưu cho project này] / [Điều chỉnh lại]**.
    **[Dùng cũ]** → `reports.project_email.<KEY>` (fallback `reports.email.to`). **[Điều chỉnh]** → nhập **NHIỀU email cách nhau dấu phẩy**
    (AskUserQuestion gợi ý + ô "Other") → **LƯU `reports.project_email.<KEY>`**. **Tiêu đề:** gợi ý động `reports/_subject-latest.txt` + ô "Other".
    → `send_report.py --to "a@x,b@y,…"` (mỗi To = 1 người, không thấy nhau) → **Gmail SMTP→API auto** (hoặc Composio nếu user chọn ở Bước 4.b) → gửi.
    **Cowork chặn SMTP → ưu tiên MCP `run_command` GỬI THẲNG; không có → BÀN GIAO bash** (KHÔNG dead-end).
  - **🔁 NGAY SAU KHI GỬI XONG (BẮT BUỘC — KHÔNG bỏ qua) → HỎI ĐẶT LỊCH TỰ ĐỘNG:** AskUserQuestion header "Đặt lịch"
    **[Đặt lịch tự động hằng ngày] / [Thôi]**.
    - **[Đặt lịch tự động hằng ngày]** → (hỏi nhanh **giờ** gợi ý `08:00` + ô "Other", **tần suất** [Mỗi ngày]/[T2–T6]) →
      `python3 "$T/kora-scheduler/schedule.py" register --id <slug> --times "<HH:MM>" --days <every|mon-fri> --scan <jira-id>
      --report-projects "<KEYS>" --report-scope <SCOPE> --report-recent-days <NDAYS> --mail-provider smtp --email "<đúng list vừa gửi>"`
      → VERIFY `schedule.py list` (xác nhận id xuất hiện) → báo "đã lưu lịch nền, tự kéo dữ liệu → report → gửi mail mỗi ngày".
      *(Nguồn MCP-only/Composio KHÔNG chạy nền được → lịch nền dùng nguồn API/SMTP; báo user nếu nguồn đã chọn là MCP.)*
    - **[Thôi]** → kết thúc. (Đây là bước ĐÓNG VÒNG tự động hóa — luôn hỏi sau khi gửi.)
