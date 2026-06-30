---
description: Hiện phiên bản Kora-Framework ĐANG CÀI (đọc version.json) + so với bản mới nhất trên GitHub. Chỉ ĐỌC — không cập nhật, không ghi gì. Triggers (vi): «đang cài bản nào», «phiên bản hiện tại», «xem version Kora» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-version` — chỉ **hiển thị phiên bản đang cài** (KHÔNG cập nhật, KHÔNG ghi gì).

1. **Đọc version ĐANG CÀI** — lấy file `version.json` ĐẦU TIÊN tồn tại theo thứ tự:
   - `~/.claude/kora-framework/version.json` (bản cài skill — phổ biến nhất; do installer copy về).
   - `./version.json` (bản project/clone ở thư mục hiện tại).
   Lấy `version` · `codename` · `released`. KHÔNG thấy file nào → báo *"chưa xác định được bản đang cài"*
   (có thể bản cũ trước khi installer copy `version.json` — mời chạy lại installer / `/claude-knowledge-update`).

2. **So với bản mới nhất trên GitHub** (read-only, best-effort — không lấy được thì vẫn hiện bản local):
   - 🖥️ **CHẠY QUA `run_command` (MCP local-terminal) nếu có** — nó chạy trên MÁY THẬT (vượt **sandbox Cowork chặn
     mạng**) + source `~/.zshrc`. Không có `run_command` (web) → thử trực tiếp; chặn thì in lệnh cho user chạy ở Terminal.
   - **FETCH CÓ FALLBACK PROXY** — mạng công ty (FPT) hay **chặn GitHub trực tiếp**, và biến `https_proxy` thường
     **TRỐNG** (vì `proxy_on` chỉ là HÀM trong `~/.zshrc`, chưa gọi thì env chưa set; còn *system proxy* thì chỉ
     **app GUI** như Claude Desktop dùng, `curl` CLI KHÔNG tự dùng). Nên thử lần lượt **direct → `$https_proxy` →
     `proxy.hcm.fpt.vn:80`**, mỗi lần có `--connect-timeout/--max-time` để KHÔNG treo. **TAG `releases/latest` CHÍNH
     LÀ version mới nhất** → KHÔNG cần đọc `version.json` (đỡ 1 lần gọi mạng, tránh CDN cache):
     ```
     REPO=<repo từ version.json>
     fetch_tag(){ local P U seen="|"; for P in "" "${https_proxy:-}" "${HTTPS_PROXY:-}" "http://proxy.hcm.fpt.vn:80"; do
       case "$seen" in *"|$P|"*) continue;; esac; seen="$seen$P|"   # dedup: KHÔNG thử direct nhiều lần khi env trống
       if [ -z "$P" ]; then U=$(curl -fsSLI --connect-timeout 8 --max-time 18 -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest" 2>/dev/null);
       else U=$(curl -fsSLI --connect-timeout 8 --max-time 18 -x "$P" -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest" 2>/dev/null); fi
       case "$U" in */tag/*) printf '%s' "${U##*/tag/}"; return 0;; esac; done; return 1; }
     TAG=$(fetch_tag); REMOTE=${TAG#v}
     ```
   - So sánh **SEMVER xác định** (KHÔNG nhìn bằng mắt): `newest=$(printf '%s\n%s\n' "$REMOTE" "$LOCAL" | sort -V | tail -1)`.
     **bằng** → "đang ở bản mới nhất ✅"; **`newest`==REMOTE** → "có bản mới **vX.Y.Z** — gõ `/claude-knowledge-update`
     để cập nhật (giữ nguyên tri thức)"; **`newest`==LOCAL** → "bản local mới hơn (dev/chưa phát hành)".
   - **Không lấy được TAG** (mọi proxy fail / không có `run_command`): **ĐỪNG báo cụt "mạng bị chặn"**. Giải thích
     ĐÚNG bản chất + vẫn hiện bản local: *"Chưa tự kiểm tra được bản mới nhất từ máy này — sandbox Cowork chặn mạng,
     hoặc CLI chưa có biến `https_proxy` (proxy_on chỉ set khi gọi trong shell đó; system proxy chỉ app GUI dùng).
     Bản đang cài **vX.Y.Z**. Để kiểm/cập nhật chắc chắn: chạy `bash ~/.claude/kora-framework/scripts/update.command`
     ở Terminal (đã có sẵn fallback proxy), hoặc gọi `proxy_on` rồi gõ lại lệnh này."*

3. **Trình bày NGẮN GỌN** (tiếng Việt), ví dụ:
   > 📦 **Kora-Framework v2.3.x · "Kora-1"** — phát hành 2026-06-21
   > Trạng thái: <đang ở bản mới nhất ✅ / có bản mới vA.B.C → `/claude-knowledge-update`>

Chỉ ĐỌC + hiển thị. Muốn nâng cấp → `/claude-knowledge-update`; xem chi tiết thay đổi → CHANGELOG / Release Note.
