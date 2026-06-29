---
description: Scan & import knowledge from your CONNECTED sources. Auto-sets up storage on first scan (only asks where to store); shows the connected sources to pick; scrapes all fields including comments. Triggers (vi): «quét jira», «lấy dữ liệu mới từ jira», «cập nhật dữ liệu mới từ jira», «quét dữ liệu», «import nguồn» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-scan` — scan & import knowledge.

0. **Đảm bảo có NƠI LƯU TRỮ — TỰ ĐỘNG, chỉ HỎI khi chưa có:**
   - Nếu folder hiện tại CHƯA phải project Kora (thiếu `config/factory-config.yaml` hoặc vault) →
     **HỎI ĐÚNG 1 CÂU:** *"Lưu tri thức ở đâu?"* (gợi ý: folder hiện tại · `~/KoraProjects/<tên>` ·
     đường dẫn khác). Đây là câu hỏi DUY NHẤT.
   - Sau khi có nơi lưu → **TỰ ĐỘNG dựng project** (chạy `workflows/00-setup.md` **Bước 0** ở chế độ
     auto): tạo vault + **`.claude/commands/` (folder skill)** + config + **domain/rule MẶC ĐỊNH** (generic;
     đổi sau bằng *"đổi domain"* / `/claude-knowledge-init`). **KHÔNG hỏi từng bước domain/rule** — tất cả tự động.
   - Nếu ĐÃ có project → bỏ qua, sang bước 1.

1. **Đọc nguồn ĐÃ KẾT NỐI:** path tool tự resolve (bản cài ở CORE), đọc **PROJECT config** qua `--config`:
   `T=tools; [ -e "$T/connections/check_connection.py" ] || T="$HOME/.claude/kora-framework/tools"; python3 "$T/connections/check_connection.py" --list --config "$PWD/config/factory-config.yaml"`
   (Windows: `py`) để lấy danh sách từ `connections`. **KHÔNG hiện đoạn giới thiệu "quét Jira".**
   - **Chưa kết nối nguồn nào** (registry rỗng) → mời chạy **`/claude-knowledge-connect`**.
   - 🎯 **"quét jira" / "quét dữ liệu mới jira" / "cập nhật dữ liệu (mới) (từ) jira" (chung) → HỎI NGUỒN khi có ≥2 nguồn Jira:**
     Đếm nguồn `jira_*` đã kết nối (MCP Cloud, API/Server host…):
     - **≥2 nguồn Jira** → **AskUserQuestion cho user CHỌN nguồn** (dễ chọn): mỗi nguồn = 1 lựa chọn kèm phương thức
       (vd *"Atlassian Cloud (MCP) ✓"*, *"Jira Server host — jira.cong-ty.vn (API) ✓"*) + **"[Cả 2 nguồn]"**. Header ≤12 ký tự,
       2–4 option, có description. (Đây chính là "hỏi từ nguồn nào cho user dễ chọn".)
     - **đúng 1 nguồn Jira** → dùng LUÔN, không hỏi vô ích (báo nhẹ "đang quét từ `<nguồn>`").
     - **user đã nêu rõ nguồn** trong câu ("quét jira server" / "nguồn nội bộ" / "cả 2") → theo đó, khỏi hỏi.
     Sau khi xác định nguồn: **MCP** → quét thẳng trong chat; **API/Server** → `run_command` (nếu có) gửi thẳng, else bàn giao.
     *(Chỉ cho NGUỒN JIRA; "quét tất cả nguồn" / nguồn khác (GitHub/SharePoint…) vẫn theo checklist bên dưới.)*
   - **Có rồi** (các trường hợp còn lại) → hiện **checklist (multi-select)** với item đầu **[✓ Quét tất cả nguồn]** (lấy HẾT),
     rồi từng nguồn kèm trạng thái: `display_name + ✓ connected · checked <thời gian tương đối>`
     (vd *"Jira Cloud (MCP) ✓ · 2h trước", "GitHub (API) ✓ · hôm qua"*). Nguồn `last_checked` quá cũ
     (>24h) / `status≠connected` → `⟳ chưa kiểm tra gần đây`, **kiểm tra lại** (`--check <id>`) trước khi quét.
     Kèm **[+ Kết nối nguồn mới]** → `/claude-knowledge-connect`.
   - 🏷️ **Mỗi nguồn HIỆN RÕ phương thức `(MCP)` hay `(API)`.** 🖥️ **Trong Cowork (sandbox CHẶN mạng):** nguồn
     **MCP** (Atlassian Rovo / Microsoft 365) quét **THẲNG trong chat**; nguồn **API** (Jira Server, GitHub/GitLab API)
     bị chặn mạng → mình **tạo sẵn 1 lệnh ở `reports/claude-knowledge-scan.command`** để bạn chạy ở **Terminal** (KHÔNG bắt gõ lại
     lệnh) — xem Bước 2. **Terminal CLI** (không sandbox): quét thẳng mọi nguồn. Gợi ý: trong Cowork, ưu tiên tích các
     nguồn **(MCP)** để quét ngay không cần Terminal.
   - **Chọn 1 nguồn cụ thể** (không phải "tất cả") → **liệt kê ĐẦY ĐỦ TỪNG project + PREFIX NGUỒN** để chọn:
     - Lấy danh sách project: **Jira API** → `python3 tools/jira-to-obsidian/import_jira.py --list-projects` → JSON
       `[{key,name}]`; **Jira MCP** → `getVisibleJiraProjects` (**phân trang lấy HẾT**, đừng dừng trang đầu);
       SharePoint/GitHub → liệt kê folder/repo qua MCP.
     - 🏷️ **HIỆN TỪNG project, KHÔNG rút gọn / KHÔNG bỏ sót** — mỗi project 1 dòng `KEY — Tên`, **gắn PREFIX nguồn**
       (tên + phương thức) để phân biệt: vd `[Cloud·MCP] FA — FMC App`, `[Server·API] IA — Insurance`. Đa nguồn/“cả 2” →
       prefix giúp tránh nhầm project trùng KEY khác nguồn.
     - 📑 **AskUserQuestion tối đa 4 option/thẻ → >4 project thì PHÂN TRANG** (3 project + **[Khác — xem thêm]** sang lượt
       kế) theo rule #8; luôn kèm **[✓ Chọn tất cả project]**. **TUYỆT ĐỐI không** nhồi >4 option, **không** im lặng cắt
       danh sách (mất project là lỗi). **MỌI cấp chọn đều có [Chọn tất cả].**
   - ⚠️ **Tránh quét trùng:** nếu user tích 2 entry CÙNG `source_type` (vd `jira_cloud__api` và `jira_cloud__mcp`)
     → cảnh báo có thể nạp trùng; nhắc chọn 1 (vault vẫn dedupe theo `jira_key` nhưng tốn công).
2. **Kéo dữ liệu** từng nguồn đã chọn vào vault:
   - **Jira (API)** → `workflows/01-import-jira.md`; cào **HẾT field, kể cả custom field & comment**.
   - **Jira (MCP — Atlassian Cloud/Rovo) → BẮT BUỘC GHI VÀO VAULT qua `--from-mcp` (KHÔNG chỉ đọc rồi bỏ — đây là
     lỗi "quét MCP không lưu tri thức"):**
     1. Chọn project (xem mục "liệt kê project" ở Bước 1) → có (các) `<KEY>`.
     2. `searchJiraIssuesUsingJql` (`project = <KEY>` [+ `AND updated >= "<since>"` nếu incremental], `fields:["*all"]`,
        **phân trang LẤY HẾT** — đừng dừng ở trang đầu). MCP trả file → dùng path đó; inline nhỏ → tự ghi ra
        `reports/_mcp-pull-<PROJECT>.json` (đặt tên **theo từng project** để tránh đè khi nhiều project). **KHÔNG** nạp cả khối vào ngữ cảnh.
     3. Map tên field 1 lần: `getJiraIssue` 1 hạng mục `expand=names` → ghi `{id:name}` ra `reports/_mcp-names.json`.
     4. ⚠️ **GHI VAULT (bước trước nay BỊ THIẾU):** `python3 tools/jira-to-obsidian/import_jira.py --from-mcp <file>
        --names reports/_mcp-names.json` → tái dùng TOÀN BỘ logic ghi note (mọi field/comment + phân loại theo loại +
        backlink quan hệ). Nhiều project → lặp/gộp file. (Không cần token cho `--from-mcp`.)
     5. Reindex (Bước 3) + báo cáo **theo loại** như mọi nguồn. **Chỉ coi là "đã quét" khi đã chạy xong bước 4 này.**
   - **SharePoint (MCP)** → `sharepoint_folder_search` để **liệt kê THƯ MỤC / PATH** (mọi cấp có [Chọn tất cả])
     → user chọn folder → `sharepoint_search` (+ fetch) **get nội dung** tài liệu về vault.
   - **Outlook (MCP)** → **AskUserQuestion hỏi BỘ LỌC trước** (khoảng thời gian · người gửi · chủ đề/keyword — KHÔNG tự lấy hết hộp thư) → `outlook_email_search` (+ `outlook_calendar_search`) theo bộ lọc → về vault.
   - **GitHub (MCP)** → MCP tool của GitHub (repo/issues/PR/wiki).
   - **GitHub (API)** → `python3 tools/github-sync/sync_github.py --pull` → kéo `.md` từ repo → `<vault>/GitHub/` (frontmatter + link nguồn + `_GitHub-Index.md`).
   - **GitLab (API)** → `python3 tools/gitlab-sync/sync_gitlab.py --pull` → kéo `.md` từ repo → `<vault>/GitLab/` (frontmatter + link nguồn + `_GitLab-Index.md`). Token `KORA_GITLAB_SYNC_TOKEN` ở `tools/gitlab-sync/.env.local`.
   - **Confluence (MCP)** → MCP tool của Confluence.
   - ⚡ **ƯU TIÊN: có MCP `local-terminal` (`run_command`) → CHẠY THẲNG, KHÔNG bàn giao.** Khi nguồn API in
     **`NETWORK_UNREACHABLE`**, TRƯỚC khi tạo file lệnh: kiểm tra có tool **`run_command`** (MCP `local-terminal`,
     thường là Claude Desktop) không. **CÓ** → gọi `run_command(command="<lệnh quét lấy từ `--emit-command`: JIRA_ENV_FILE=<abs> python3 \"<abs import_jira.py>\" --jql/--since…>", cwd="<PROJECT tuyệt đối>")`
     → chạy trên máy thật (ngoài sandbox, đúng VPN), lấy stdout về → reindex + tổng hợp THẲNG trong chat, **không cần
     `.command`/Terminal**. (Nhiều nguồn API → gọi `run_command` lần lượt.) Chỉ khi **KHÔNG có** `run_command` → mới bàn giao file lệnh dưới đây.
   - 🖥️ **BÀN GIAO TERMINAL khi Cowork chặn mạng nguồn API + KHÔNG có `run_command` (KHÔNG dead-end):** nếu tool quét nguồn **API** in marker
     **`NETWORK_UNREACHABLE`** ở stderr (sandbox Cowork chặn) → **KHÔNG retry vô ích**, KHÔNG kết luận "nguồn hỏng".
     Thay vào đó **tạo file lệnh** để user chạy ở Terminal local (đúng mạng/VPN):
     1. Lấy lệnh quét đã resolve abs-path: `python3 <import_jira.py> --emit-command <đúng args định quét: --jql/--since/--keys/--per-project>` (Jira). Nguồn pull khác cũng API → thêm dòng `python3 <abs>/github-sync/sync_github.py --pull` / `.../gitlab-sync/sync_gitlab.py --pull`.
     2. **Ghi `reports/claude-knowledge-scan.command`** (`mkdir -p reports` trước): dòng đầu `#!/bin/bash`, rồi `cd "<PROJECT tuyệt đối>"`, rồi (các) lệnh ở (1) — **gộp NHIỀU nguồn API vào 1 file**; `chmod +x`. Windows: ghi `reports\claude-knowledge-scan.bat` (bỏ shebang, `cd /d "<project>"`, dùng `py`).
     3. Báo user 1 câu: *"Cowork bị chặn mạng nên không quét nguồn API từ đây. Mở **Terminal** chạy: `bash \"reports/claude-knowledge-scan.command\"` — quét xong gõ **'đã quét xong'** để mình reindex + tổng hợp + (tùy chọn) báo cáo."* Token KHÔNG nằm trong file (chỉ trỏ `JIRA_ENV_FILE`).
     - **Nguồn MCP KHÔNG cần bàn giao** — gọi MCP tool quét thẳng trong Cowork. **Terminal CLI** cũng quét thẳng, bỏ qua bàn giao.
3. **Tổng hợp NHẸ (tự động, ngay sau khi nạp):** `python3 tools/kb-synth/synthesize.py --root .` → dựng
   trang `_wiki/<Project>-Wiki.md` liên kết cho mỗi project (index theo loại + mục "Quan hệ"). Rồi reindex
   `python3 tools/kb-indexer/build_index.py --root .`.
   - 📊 **BÁO CÁO KẾT QUẢ — BẮT BUỘC theo LOẠI, KHÔNG gộp chung "issue":** lấy dòng `phân loại: Epic: X · User Story: Y ·
     Task: Z · Bug: W · Sub-task: …` mà `import_jira.py` in ra (mỗi project + tổng) → trình bày bảng/list **theo từng loại
     cho từng project**. Nêu rõ **đã PHÂN vào thư mục theo loại** (`02_Epics/03_UserStories/04_Tasks/05_Bugs/06_SubTasks`) +
     **đã tạo LIÊN KẾT quan hệ** (parent/issue-link → backlink `[[…]]` + relation-graph). **TUYỆT ĐỐI KHÔNG** báo gộp kiểu
     "đã nạp N issue" — phải tách Epic/US/Task/Bug. + số trang wiki.
4. **(Tùy chọn) Đào sâu → `docs/`:** AskUserQuestion **[Phân loại sâu thành feature/BR/AC]** / **[Để vậy]**.
   Chọn đào sâu → Claude đọc hạng mục công việc thô (kể cả AC/BR raw) → đề xuất phân loại vào `docs/03-features/F-xxx/…`,
   BR/AC (ID nối tiếp max trong `.kb/index.json`) → **✋ Approval Gate (Tầng B)** → ghi + reindex.
   - 📐 **Tuân thủ chuẩn phân tích:** đọc `config/domain-rules.md` (phân loại theo domain) + áp cổng
     **vai trò/domain/template** (`workflows/03-request.md` Bước 0) nếu phiên chưa chốt; ghi artifact theo
     **ĐỊNH DẠNG CHUẨN** `templates/prompts/ba-prompt-library.md` + cấu trúc `templates/` (như WF02 Bước 6 /
     WF03 "ĐẦU RA CHUẨN TỰ ĐỘNG"). Tức **import/scan và phân tích dùng CHUNG một chuẩn đầu ra**.
5. **LUÔN ĐỀ XUẤT BƯỚC KẾ — gồm hỏi "Tạo lịch?"** (AskUserQuestion, schema rule #8, header ≤12 ký tự "Bước kế"):
   **[Tạo lịch tự động] · [Quét thêm nguồn khác] · [Sinh báo cáo] · [Dừng]**.
   - **[Tạo lịch tự động]** → `/claude-knowledge-schedule` (`workflows/08-schedule-sync.md`): lịch định kỳ get→reindex→(report/mail/sync).
   - **[Quét thêm nguồn khác]** → quay lại chọn nguồn (Jira domain khác / SharePoint / file / ảnh hoá đơn).
   - Đừng dead-end: luôn cho user chọn bước tiếp, KHÔNG bắt nhớ lệnh.

Giữ bảo mật token (env var) + Approval Gate trước khi ghi vào `docs/` / vault.
