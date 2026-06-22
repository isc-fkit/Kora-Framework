---
description: Scan & import knowledge from your CONNECTED sources. Auto-sets up storage on first scan (only asks where to store); shows the connected sources to pick; scrapes all fields including comments.
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
   - 🎯 **"quét jira" / "quét dữ liệu mới jira" (chung, KHÔNG nêu nguồn) → ƯU TIÊN nguồn Jira qua MCP, KHÔNG HỎI "nguồn nào".**
     Nếu có ≥1 nguồn `jira_*` phương thức **MCP** (Atlassian Cloud/Rovo) → **tự chọn nó, quét THẲNG trong chat** (bỏ qua
     checklist + bàn giao). **Dù có Jira Server host (API) kết nối song song cũng KHÔNG hỏi** — báo nhẹ 1 dòng: *"Đang quét
     Jira qua MCP (Atlassian Cloud). Muốn quét cả Jira Server host nội bộ thì bảo mình (vd 'quét jira server')."* CHỈ hiện
     checklist chọn nguồn khi: (a) user nói **"quét tất cả nguồn"/"chọn nguồn"**; (b) user nêu RÕ nguồn server (**"quét jira
     server"**, "nguồn nội bộ/host", "quét cả 2 nguồn"); hoặc (c) **KHÔNG có** nguồn Jira MCP (chỉ có API/server → dùng luôn
     nguồn đó, vẫn KHÔNG hỏi vô ích — quét thẳng nếu có `run_command`, else bàn giao). *(Quy tắc này chỉ cho NGUỒN JIRA; "quét
     tất cả nguồn" hay nguồn khác (GitHub/SharePoint…) vẫn theo checklist bên dưới.)*
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
   - **Chọn 1 nguồn cụ thể** (không phải "tất cả") → kết nối rồi **trả về danh sách project/folder** để
     chọn (Jira: `python3 tools/jira-to-obsidian/import_jira.py --list-projects` → JSON `[{key,name}]`;
     SharePoint/GitHub: liệt kê folder/repo qua MCP). **MỌI cấp chọn đều có [Chọn tất cả].**
   - ⚠️ **Tránh quét trùng:** nếu user tích 2 entry CÙNG `source_type` (vd `jira_cloud__api` và `jira_cloud__mcp`)
     → cảnh báo có thể nạp trùng; nhắc chọn 1 (vault vẫn dedupe theo `jira_key` nhưng tốn công).
2. **Kéo dữ liệu** từng nguồn đã chọn vào vault:
   - **Jira (API/MCP)** → `workflows/01-import-jira.md`; cào **HẾT field, kể cả custom field & comment**.
   - **SharePoint (MCP)** → `sharepoint_folder_search` để **liệt kê THƯ MỤC / PATH** (mọi cấp có [Chọn tất cả])
     → user chọn folder → `sharepoint_search` (+ fetch) **get nội dung** tài liệu về vault.
   - **Outlook (MCP)** → `outlook_email_search` (+ `outlook_calendar_search`) → lấy email/lịch theo bộ lọc về vault.
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
   `python3 tools/kb-indexer/build_index.py --root .`; báo số note đã thêm + số trang wiki.
4. **(Tùy chọn) Đào sâu → `docs/`:** AskUserQuestion **[Phân loại sâu thành feature/BR/AC]** / **[Để vậy]**.
   Chọn đào sâu → Claude đọc hạng mục công việc thô (kể cả AC/BR raw) → đề xuất phân loại vào `docs/03-features/F-xxx/…`,
   BR/AC (ID nối tiếp max trong `.kb/index.json`) → **✋ Approval Gate (Tầng B)** → ghi + reindex.
   - 📐 **Tuân thủ chuẩn phân tích:** đọc `config/domain-rules.md` (phân loại theo domain) + áp cổng
     **vai trò/domain/template** (`workflows/03-request.md` Bước 0) nếu phiên chưa chốt; ghi artifact theo
     **ĐỊNH DẠNG CHUẨN** `templates/prompts/ba-prompt-library.md` + cấu trúc `templates/` (như WF02 Bước 6 /
     WF03 "ĐẦU RA CHUẨN TỰ ĐỘNG"). Tức **import/scan và phân tích dùng CHUNG một chuẩn đầu ra**.

Giữ bảo mật token (env var) + Approval Gate trước khi ghi vào `docs/` / vault.
