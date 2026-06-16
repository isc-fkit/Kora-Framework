---
description: Sao lưu / xuất toàn bộ tri thức ra file zip để chuyển máy (workflows/11 mục A)
---

Người dùng vừa CHỦ ĐỘNG gõ `/kora-sao-luu` — đây là **lệnh rõ ràng** để sao lưu/xuất tri thức
(tương đương "sao lưu", "xuất tri thức", "chuyển/dời máy").

Đọc và thực thi `workflows/11-export-import.md` **mục A (export)** theo `CLAUDE.md`:

- Đóng gói DATA (`docs/`, vault `*_Brain/`, `inbox/`, `.kb/*` trừ file CORE, `config/*`,
  `.env.local`) ra `genesis1-kb-*.zip`.
- ⚠️ Cân nhắc bảo mật token trong `.env.local` khi chuyển máy.
- Giữ nguyên Approval Gate.
