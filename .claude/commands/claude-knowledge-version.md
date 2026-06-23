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
   - Lấy repo từ `version.json > repo` (mặc định `isc-fkit/Kora-Framework`), nhánh `release`.
   - **Fetch theo SHA commit** (raw.githubusercontent **BỎ QUA** `?t=` → cache CDN theo path; phải đọc theo
     SHA immutable mới luôn tươi — như installer/updater v2.3.4):
     ```
     SHA=$(curl -fsSL -H 'Accept: application/vnd.github.sha' "https://api.github.com/repos/<repo>/commits/release" 2>/dev/null)
     echo "$SHA" | grep -qiE '^[0-9a-f]{40}$' \
       && curl -fsSL "https://raw.githubusercontent.com/<repo>/$SHA/version.json" \
       || curl -fsSL "https://raw.githubusercontent.com/<repo>/release/version.json?t=$(date +%s)"   # fallback nếu API rate-limit
     ```
     Đọc `version` của bản mới nhất.
   - So sánh **semantic** (x.y.z): **bằng** → "đang ở bản mới nhất ✅"; **local thấp hơn** → "có bản mới
     **vX.Y.Z** — gõ `/claude-knowledge-update` để cập nhật (giữ nguyên tri thức)"; **local cao hơn** → "bản local mới hơn
     (bản dev/chưa phát hành)".

3. **Trình bày NGẮN GỌN** (tiếng Việt), ví dụ:
   > 📦 **Kora-Framework v2.3.x · "Kora-1"** — phát hành 2026-06-21
   > Trạng thái: <đang ở bản mới nhất ✅ / có bản mới vA.B.C → `/claude-knowledge-update`>

Chỉ ĐỌC + hiển thị. Muốn nâng cấp → `/claude-knowledge-update`; xem chi tiết thay đổi → CHANGELOG / Release Note.
