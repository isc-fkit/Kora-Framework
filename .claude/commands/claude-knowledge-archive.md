---
description: Package the knowledge base into a permissioned, password-gated archive to hand over to other users (read-only or read-write), with read keys bundled and report/mail stripped for user packages. Triggers (vi): «đóng gói bàn giao», «archive», «handover cho user khác» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-archive` — đóng gói KB có phân quyền + mật khẩu để bàn giao. Theo
`workflows/15-archive.md`. Khác `/claude-knowledge-export-knowledge-base` (sao lưu thuần, không cổng/không phân quyền).

**Luồng (mục A — HOST tạo gói):**
1. **Cổng mật khẩu:** đặt mật khẩu vào biến môi trường `KORA_ARCHIVE_PW` (KHÔNG hỏi qua card; KHÔNG in).
   `scripts/archive-kb.command` tự kiểm qua `tools/archive-gate/verify_password.py` (hash trên repo —
   chủ repo đổi được). Sai → dừng.
2. **AskUserQuestion:** loại gói **[USER]/[HOST]** + quyền **[read-only]/[read-write]**.
3. Gói USER: thu thập **key READ-ONLY** cloud-KB chung qua env (`KORA_CLOUD_READ_BASE_URL/_USER/_TOKEN`,
   `KORA_CLOUD_SPACE`) — KHÔNG dùng token write của host, KHÔNG đưa vào chat.
4. ✋ Confirm → chạy `scripts/archive-kb.command` (Windows: `scripts\archive-kb.bat`) với các biến môi trường.
   Ra `kora-archive-<project>-<date>.zip`. Báo đường dẫn + cách gửi.

**Người nhận:** dùng `/claude-knowledge-export-knowledge-base`? Không — dùng `scripts/import-kb.command` (đã hỗ trợ
gói archive: đặt key READ, tạo `.claude-knowledge-user`, tắt report/mail, gợi ý lên lịch get&post). Xem WF15 mục B.

⚠️ Đây là lệnh cho người có nhiệm vụ bàn giao. Quyền thực thi bằng CAPABILITY (có/không token write),
marker chỉ là UX. **Mật khẩu chỉ gác việc TẠO gói** (host), KHÔNG hỏi lại khi user cài/import, không bảo
vệ dữ liệu bên trong.

**Bàn giao + đồng bộ tự động (host đẩy cloud → user kéo về local):**
1. **HOST:** trước/khi archive, `/claude-knowledge-sync` đẩy KB lên **GitHub private** và/hoặc **Confluence chung**
   (cổng `KORA_OPS_PW`). Gói archive USER ship **key READ** + `.claude-knowledge-user` (tắt report/mail).
2. **USER** (máy base sạch): mở **Claude Desktop** → tạo project → **import source host đã export**
   (`import-kb.command` / kéo `kora-archive-*.zip` vào chat) → connect **MCP** tới GitHub-private /
   Confluence của host → mở **/claude-knowledge-schedule** (hoặc lịch Cowork) tạo lịch **kéo (pull) đồng bộ** → đúng
   giờ tự kéo tri thức mới về **local knowledge**. read-only → 1 chiều get; read-write → get & post.
3. Project user import LUÔN **hỏi để nắm tri thức** trước khi trả lời (tránh lạc đề) — xem CLAUDE.md §6.
