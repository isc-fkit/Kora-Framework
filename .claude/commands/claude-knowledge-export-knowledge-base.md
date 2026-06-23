---
description: Export the entire knowledge base to a zip — for backup, moving machines, or handover. Triggers (vi): «sao lưu KB», «xuất toàn bộ tri thức», «chuyển/dời máy», «backup KB zip» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-export-knowledge-base` — export all knowledge to a zip.

Read and execute `workflows/11-export-import.md` **section A (export)** following `CLAUDE.md`:

- Package DATA (`docs/`, vault `*_Brain/`, `inbox/`, `.kb/*` except CORE files, `config/*`, `.env.local`)
  into `kora-kb-*.zip`.
- ⚠️ Consider token security in `.env.local` when moving / handing over.
- Keep the Approval Gate.

> 🔓 **KHÔNG cổng mật khẩu — export thuần.** Luồng này TUYỆT ĐỐI không dùng `KORA_OPS_PW` /
> `verify_ops_password.py` và không có bước sync/gửi-mail nào. Cần phân quyền + mật khẩu để bàn giao →
> dùng `/claude-knowledge-archive` (riêng).
