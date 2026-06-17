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

1. **Đọc nguồn ĐÃ KẾT NỐI** từ `config/factory-config.yaml > connections`. **KHÔNG hiện đoạn giới
   thiệu "quét Jira".**
   - **Chưa kết nối nguồn nào** → mời chạy **`/kora-connect`**.
   - **Có rồi** → hiện **checklist (multi-select)** các nguồn đã kết nối (vd *"Jira Cloud (MCP)",
     "SharePoint (MCP)", "Jira self-host (API)", "GitHub (MCP)"*) → user tích nguồn muốn quét. Kèm
     **[+ Kết nối nguồn mới]** → `/kora-connect`.
2. **Kéo dữ liệu** từng nguồn đã chọn vào vault:
   - **Jira (API/MCP)** → `workflows/01-import-jira.md`; cào **HẾT field, kể cả custom field & comment**.
   - **SharePoint (MCP)** → `sharepoint_search` / `sharepoint_folder_search`.
   - **GitHub (MCP)** → MCP tool của GitHub (repo/issues/PR/wiki).
   - **Confluence (MCP)** → MCP tool của Confluence.
3. Sau khi nạp → reindex; báo số note đã thêm.

Giữ bảo mật token (env var) + Approval Gate trước khi ghi vào `docs/` / vault.
