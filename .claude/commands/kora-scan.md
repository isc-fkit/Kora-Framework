---
description: Scan & import knowledge from your CONNECTED sources. Auto-sets up storage on first scan (only asks where to store); shows the connected sources to pick; scrapes all fields including comments.
---

The user invoked `/kora-scan` — scan & import knowledge.

0. **Đảm bảo có NƠI LƯU TRỮ — TỰ ĐỘNG, chỉ HỎI khi chưa có:**
   - Nếu folder hiện tại CHƯA phải project Kora (thiếu `config/factory-config.yaml` hoặc vault) →
     **HỎI ĐÚNG 1 CÂU:** *"Lưu tri thức ở đâu?"* (gợi ý: folder hiện tại · `~/KoraProjects/<tên>` ·
     đường dẫn khác). Đây là câu hỏi DUY NHẤT.
   - Sau khi có nơi lưu → **TỰ ĐỘNG dựng project** (chạy `workflows/00-setup.md` **Bước 0** ở chế độ
     auto): tạo vault + **`.claude/commands/` (folder skill)** + config + **domain/rule MẶC ĐỊNH** (generic;
     đổi sau bằng *"đổi domain"* / `/kora-init`). **KHÔNG hỏi từng bước domain/rule** — tất cả tự động.
   - Nếu ĐÃ có project → bỏ qua, sang bước 1.

1. **Đọc nguồn ĐÃ KẾT NỐI:** path tool tự resolve (bản cài ở CORE), đọc **PROJECT config** qua `--config`:
   `T=tools; [ -e "$T/connections/check_connection.py" ] || T="$HOME/.claude/kora-framework/tools"; python3 "$T/connections/check_connection.py" --list --config "$PWD/config/factory-config.yaml"`
   (Windows: `py`) để lấy danh sách từ `connections`. **KHÔNG hiện đoạn giới thiệu "quét Jira".**
   - **Chưa kết nối nguồn nào** (registry rỗng) → mời chạy **`/kora-connect`**.
   - **Có rồi** → hiện **checklist (multi-select)** với item đầu **[✓ Quét tất cả nguồn]** (lấy HẾT),
     rồi từng nguồn kèm trạng thái: `display_name + ✓ connected · checked <thời gian tương đối>`
     (vd *"Jira Cloud (MCP) ✓ · 2h trước", "GitHub (API) ✓ · hôm qua"*). Nguồn `last_checked` quá cũ
     (>24h) / `status≠connected` → `⟳ chưa kiểm tra gần đây`, **kiểm tra lại** (`--check <id>`) trước khi quét.
     Kèm **[+ Kết nối nguồn mới]** → `/kora-connect`.
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
   - **Confluence (MCP)** → MCP tool của Confluence.
3. **Tổng hợp NHẸ (tự động, ngay sau khi nạp):** `python3 tools/kb-synth/synthesize.py --root .` → dựng
   trang `_wiki/<Project>-Wiki.md` liên kết cho mỗi project (index theo loại + mục "Quan hệ"). Rồi reindex
   `python3 tools/kb-indexer/build_index.py --root .`; báo số note đã thêm + số trang wiki.
4. **(Tùy chọn) Đào sâu → `docs/`:** AskUserQuestion **[Phân loại sâu thành feature/BR/AC]** / **[Để vậy]**.
   Chọn đào sâu → Claude đọc issue thô (kể cả AC/BR raw) → đề xuất phân loại vào `docs/03-features/F-xxx/…`,
   BR/AC (ID nối tiếp max trong `.kb/index.json`) → **✋ Approval Gate (Tầng B)** → ghi + reindex.
   - 📐 **Tuân thủ chuẩn phân tích:** đọc `config/domain-rules.md` (phân loại theo domain) + áp cổng
     **vai trò/domain/template** (`workflows/03-request.md` Bước 0) nếu phiên chưa chốt; ghi artifact theo
     **ĐỊNH DẠNG CHUẨN** `templates/prompts/ba-prompt-library.md` + cấu trúc `templates/` (như WF02 Bước 6 /
     WF03 "ĐẦU RA CHUẨN TỰ ĐỘNG"). Tức **import/scan và phân tích dùng CHUNG một chuẩn đầu ra**.

Giữ bảo mật token (env var) + Approval Gate trước khi ghi vào `docs/` / vault.
