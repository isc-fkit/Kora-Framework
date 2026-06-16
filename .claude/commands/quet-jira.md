---
description: Quét toàn bộ Jira về vault tri thức — chạy workflows/01-import-jira.md
---

Người dùng vừa CHỦ ĐỘNG gõ `/quet-jira` — đây là **lệnh rõ ràng** để quét toàn bộ Jira
(tương đương "quét jira"). KHÔNG hỏi lại "chạy hay chỉ hỏi thông tin".

Đọc và thực thi `workflows/01-import-jira.md` theo `CLAUDE.md`:

- **Bước 0:** cho user **chọn nguồn/domain** (Server nội bộ hay Atlassian Cloud) rồi mới quét.
- Giữ nguyên Approval Gate.
- Bảo mật token: chỉ nằm trong `tools/jira-to-obsidian/.env.local`, KHÔNG in ra chat/log,
  **xóa `.env.local` sau khi quét xong**.
