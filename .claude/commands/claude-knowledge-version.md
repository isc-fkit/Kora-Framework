---
description: Hiện phiên bản Kora-Framework ĐANG CÀI (đọc version.json) + so với bản mới nhất trên GitHub. Chỉ ĐỌC — không cập nhật, không ghi gì. Triggers (vi): «đang cài bản nào», «phiên bản hiện tại», «xem version Kora» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-version` — chỉ **hiển thị phiên bản đang cài** (KHÔNG cập nhật, KHÔNG ghi gì).

1. **Đọc version ĐANG CÀI** — lấy file `version.json` ĐẦU TIÊN tồn tại theo thứ tự:
   - `~/.claude/kora-framework/version.json` (bản cài skill — phổ biến nhất; do installer copy về).
   - `./version.json` (bản project/clone ở thư mục hiện tại).
   Lấy `version` · `codename` · `released`. KHÔNG thấy file nào → báo *"chưa xác định được bản đang cài"*
   (có thể bản cũ trước khi installer copy `version.json` — mời chạy lại installer / `/claude-knowledge-update`).

2. **So với bản mới nhất trên GitHub** (read-only, best-effort — offline thì BỎ QUA, vẫn hiện bản local):
   - Lấy repo từ `version.json > repo` (mặc định `isc-fkit/Kora-Framework`).
   - **LẤY TAG QUA REDIRECT `releases/latest`** (no-auth, KHÔNG dính rate-limit `api.github.com` — hay 403 trên IP
     công ty, KHÔNG dính CDN cache của raw.githubusercontent; đọc version.json THEO TAG = immutable nên luôn tươi):
     ```
     REPO=<repo>
     TAG=$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest" 2>/dev/null | sed -E 's#.*/tag/##')
     [ -n "$TAG" ] || TAG=$(command -v gh >/dev/null 2>&1 && gh api "repos/$REPO/releases/latest" --jq .tag_name 2>/dev/null)
     curl -fsSL "https://raw.githubusercontent.com/$REPO/$TAG/version.json"   # đọc version remote (REMOTE=${TAG#v})
     ```
     > ⚠️ KHÔNG `curl release/version.json` thẳng (không tag): raw **CACHE theo path, BỎ QUA `?t=`** → trả bản CŨ.
   - So sánh **SEMVER xác định** (KHÔNG nhìn bằng mắt): `newest=$(printf '%s\n%s\n' "$REMOTE" "$LOCAL" | sort -V | tail -1)`.
     **bằng** → "đang ở bản mới nhất ✅"; **`newest`==REMOTE** → "có bản mới **vX.Y.Z** — gõ `/claude-knowledge-update`
     để cập nhật (giữ nguyên tri thức)"; **`newest`==LOCAL** → "bản local mới hơn (dev/chưa phát hành)".

3. **Trình bày NGẮN GỌN** (tiếng Việt), ví dụ:
   > 📦 **Kora-Framework v2.3.x · "Kora-1"** — phát hành 2026-06-21
   > Trạng thái: <đang ở bản mới nhất ✅ / có bản mới vA.B.C → `/claude-knowledge-update`>

Chỉ ĐỌC + hiển thị. Muốn nâng cấp → `/claude-knowledge-update`; xem chi tiết thay đổi → CHANGELOG / Release Note.
