---
description: Set the operations/admin password (KORA_OPS_PW) ONCE so all gated flows (sync, send-mail, daily-report, scheduled post/report/mail/sync) work — saved to ~/.config/claude-knowledge/ops-pw.env so it takes effect IMMEDIATELY (no need to source ~/.zshrc). Password is entered by you locally, never via chat.
---

The user invoked `/claude-knowledge-ops-password` — đặt **mật khẩu vận hành** (`KORA_OPS_PW`) MỘT LẦN cho mọi cổng:
`/claude-knowledge-sync`, `/claude-knowledge-send-mail`, `/claude-knowledge-daily-report`, và bước **post/report/mail/sync** của `/claude-knowledge-schedule`.
Mật khẩu **do CHỦ REPO đặt** (hash trên framework) — bạn nhập đúng để mở cổng. **TUYỆT ĐỐI KHÔNG** nhận mật
khẩu qua chat/card, **KHÔNG in** ra. Lưu vào file `~/.config/claude-knowledge/ops-pw.env` → `verify_ops_password.py` đọc
**ngay lúc chạy** (không cần `source`/mở terminal mới); scheduler nền cũng dùng đúng file này.

**Resolve path tool** (bản cài để CORE ở `~/.claude/kora-framework/`):
`T=tools; [ -e "$T/archive-gate/verify_ops_password.py" ] || T="$HOME/.claude/kora-framework/tools"`
(Windows: `py` thay `python3`; file mật khẩu ở `%USERPROFILE%\.claude-knowledge\ops-pw.env`.)

### Bước 1 — Đặt mật khẩu vào file (password KHÔNG qua chat)
AskUserQuestion: **[Nhập qua terminal (read -s)]** / **[Tự sửa file]** (gợi ý cách nào hợp môi trường):
- **[Nhập qua terminal]** — đưa user **tự chạy trong terminal của họ** (mật khẩu gõ ở terminal, KHÔNG tới Claude/chat):
  ```
  umask 177; mkdir -p ~/.config/claude-knowledge; read -s -p "Mật khẩu vận hành: " p && printf 'KORA_OPS_PW=%s\n' "$p" > ~/.config/claude-knowledge/ops-pw.env && chmod 600 ~/.config/claude-knowledge/ops-pw.env && unset p && echo "đã lưu ~/.config/claude-knowledge/ops-pw.env"
  ```
- **[Tự sửa file]** — tạo sẵn file mẫu (chmod 600) rồi nhờ user mở thay `PASTE_HERE`:
  `umask 177; mkdir -p ~/.config/claude-knowledge; printf 'KORA_OPS_PW=PASTE_HERE\n' > ~/.config/claude-knowledge/ops-pw.env; chmod 600 ~/.config/claude-knowledge/ops-pw.env`
  → present đường dẫn `~/.config/claude-knowledge/ops-pw.env` + hướng dẫn mở (macOS Finder `Cmd+Shift+G`; file ẩn `Cmd+Shift+.`)
  để user thay `PASTE_HERE` bằng mật khẩu thật rồi lưu. **Claude KHÔNG đọc/in nội dung file.**

### Bước 2 — Verify (đọc file vừa đặt)
`python3 "$T/archive-gate/verify_ops_password.py"` → **exit 0 = đúng** ("✅ mật khẩu vận hành hợp lệ"); **exit ≠ 0**
= "❌ mật khẩu KHÔNG khớp (do chủ repo đặt) — đặt lại". KHÔNG in mật khẩu, KHÔNG đọc file ra chat.

### Bước 3 — (Tùy chọn) env cho ai thích
Có thể thêm `export KORA_OPS_PW=...` vào `~/.zshrc` (env ưu tiên hơn file), nhưng **file đã đủ và có hiệu lực ngay**
— không cần `source`. Báo xong: từ giờ `/claude-knowledge-sync` · `/claude-knowledge-send-mail` · `/claude-knowledge-daily-report` · lịch nền không hỏi lại mật khẩu.

> Bảo mật: file chmod 600; mật khẩu KHÔNG vào chat / git / config / log. Quên/đổi → chạy lại `/claude-knowledge-ops-password`.
