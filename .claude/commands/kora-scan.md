---
description: Scan & import knowledge from your CONNECTED sources. Shows the list of connected sources to pick from; scrapes all fields including comments.
---

The user invoked `/kora-scan` — scan & import knowledge.

1. **Đọc nguồn ĐÃ KẾT NỐI** từ `config/factory-config.yaml > connections`. **KHÔNG hiện đoạn giới
   thiệu "quét Jira" nữa.**
   - **Chưa có nguồn nào** → nói gọn *"Chưa kết nối nguồn nào"* → mời chạy **`/kora-connect`**.
   - **Có rồi** → hiện danh sách **checklist (multi-select)** các nguồn đã kết nối — vd
     *"Jira Cloud (MCP)", "SharePoint (MCP)", "Jira self-host (API)", "GitHub (MCP)"* → user tích nguồn
     muốn quét. Kèm lựa chọn **[+ Kết nối nguồn mới]** → `/kora-connect`.
2. **Kéo dữ liệu** từng nguồn đã chọn vào vault:
   - **Jira (API/MCP)** → `workflows/01-import-jira.md`; cào **HẾT field, kể cả comment**.
   - **SharePoint (MCP)** → `sharepoint_search` / `sharepoint_folder_search`.
   - **GitHub (MCP)** → các MCP tool của GitHub (repo/issues/PR/wiki).
   - **Confluence (MCP)** → MCP tool của Confluence.
3. Sau khi nạp → reindex; báo số note đã thêm.

Giữ bảo mật token (env var) + Approval Gate trước khi ghi vào `docs/` / vault.
