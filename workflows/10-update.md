# Workflow 10 — Cập nhật phiên bản APP (GIỮ NGUYÊN tri thức)

> Trigger: "cập nhật phiên bản", "cập nhật ứng dụng / app", "lên bản mới nhất",
> "có bản mới không", "kiểm tra phiên bản".
> ⚠️ Đây là **cập nhật phiên bản CHƯƠNG TRÌNH (app)**. Khi user gõ các trigger trên →
> **chạy thẳng workflow này**, KHÔNG hỏi lại "bạn muốn cập nhật cái gì". WF tự confirm trước
> bước GHI/tải (Bước 2) nên an toàn.
> 🚫 **KHÔNG phụ thuộc skill `/claude-knowledge-update` có trong available list.** Update là việc WF này tự làm được
> (qua `run_command`/Bash). Nếu skill không có trong Cowork → **ĐỪNG thử gọi `Skill claude-knowledge-update` rồi "xin lỗi
> gọi nhầm"** — đi thẳng workflow này (CLAUDE.md + `workflows/` luôn được nạp khi mở project). Chính lúc cần update là lúc
> skill hay bị thiếu/cũ, nên việc chạy thẳng WF10 là ĐÚNG, không phải fallback "đáng xin lỗi".
> **Ngoại lệ duy nhất:** user gõ **"cập nhật" TRƠ** (không tân ngữ) → mới hỏi 1 câu phân biệt:
> *"Cập nhật ứng dụng lên bản mới, hay cập nhật tri thức/nội dung?"* rồi mới chạy.
> Nên TỰ kiểm tra ở cuối setup (workflow 00 Bước 7) và khi user hỏi "đang bản nào".
>
> **Mô hình phát hành:** user TẢI ZIP → giải nén → mở trong Cowork → setup. Đa số KHÔNG có
> `.git`. Cập nhật = tải phần CORE mới đè lên, GIỮ NGUYÊN DATA (xem CLAUDE.md §6).

## Bước 1 — So phiên bản

1. Đọc `version.json` ở gốc repo → `LOCAL` = version + codename hiện tại.
2. Lấy bản mới nhất trên GitHub — **LẤY TAG QUA REDIRECT `releases/latest`** (no-auth, KHÔNG dính
   rate-limit `api.github.com` — hay bị **403** trên IP công ty, KHÔNG dính CDN cache của raw.githubusercontent):
   ```
   REPO=isc-fkit/Kora-Framework
   TAG=$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest" 2>/dev/null | sed -E 's#.*/tag/##')
   [ -n "$TAG" ] || TAG=$(command -v gh >/dev/null 2>&1 && gh api "repos/$REPO/releases/latest" --jq .tag_name 2>/dev/null)
   REMOTE=${TAG#v}
   # Đọc version.json + CHANGELOG THEO TAG (đường dẫn tag = IMMUTABLE → KHÔNG bị CDN trả bản cũ; thay cho SHA hay bị 403):
   curl -fsSL "https://raw.githubusercontent.com/$REPO/$TAG/version.json"
   ```
   — không lấy được `$TAG` (offline/chặn) → "chưa kiểm tra được bản mới, thử lại khi có mạng", DỪNG. **Giữ `$TAG`/`$REMOTE`** cho Bước 2.
   > ⚠️ **KHÔNG** so version bằng cách `curl release/version.json` thẳng (không tag/SHA): raw.githubusercontent
   > **CACHE theo path, BỎ QUA `?t=`** → trả bản CŨ. Đây ĐÚNG là bug "app nhận version GitHub cũ" + `api.github.com` 403.
3. So `version` bằng **SEMVER xác định** (KHÔNG nhìn bằng mắt — so chuỗi thì "2.12.9" > "2.12.25" là SAI):
   ```
   newest=$(printf '%s\n%s\n' "$REMOTE" "$LOCAL" | sort -V | tail -1)
   ```
   - `$LOCAL` == `$REMOTE` → "Bạn đang ở bản mới nhất: Kora-1 v$LOCAL." DỪNG.
   - `newest` == `$REMOTE` (khác LOCAL) → GitHub mới hơn → sang Bước 2.
   - `newest` == `$LOCAL` (local cao hơn — hiếm, chỉ máy maintainer chưa release) → báo "local mới hơn", KHÔNG hạ cấp.

## Bước 2 — Trình bày + ✋ confirm

- **Đọc `intro` + `force` từ remote `version.json`** (đã lấy ở Bước 1):
  - `intro` (nội dung giới thiệu maintainer điền lúc phát hành) khác rỗng → **hiện nổi bật ĐẦU
    TIÊN** (nguyên văn, dạng trích dẫn) để user biết bản mới có gì đáng chú ý.
  - `force: true` → mở đầu bằng **"🔴 Bản cập nhật quan trọng/ưu tiên"**, lời lẽ mạnh hơn (nên
    cập nhật sớm). `force` vắng/false → thông báo bình thường.
- Lấy "có gì mới" từ GitHub CHANGELOG — **theo `$TAG` ở Bước 1** (đường dẫn tag IMMUTABLE → tươi, không cache CDN):
  `curl -fsSL "https://raw.githubusercontent.com/isc-fkit/Kora-Framework/$TAG/CHANGELOG.md"`
  (fallback `/release/CHANGELOG.md?t=$(date +%s)` nếu thiếu `$TAG`) → tóm tắt tiếng Việt: từ vX → vY có gì mới.
- Nhấn mạnh: **tri thức của bạn (vault, `.kb`, config, docs) GIỮ NGUYÊN** — chỉ thay phần chương trình.
- **Nêu rõ cách nâng cấp** (1 dòng): "Gõ **'đồng ý'** để tôi cập nhật ngay; hoặc tự chạy
  `scripts/update.command`."
- Hỏi confirm: "Cập nhật ngay chứ?" (thao tác GHI/NẶNG — bắt buộc confirm; kể cả `force` vẫn chờ user đồng ý).

## Bước 3 — Chạy cập nhật

> ⚠️ **Sandbox Cowork chặn mạng** → Claude KHÔNG tự tải/ghi đè CORE từ trong chat. **CORE bản cài nằm ở
> `~/.claude/kora-framework` (ngoài sandbox).** Có 2 đường, ưu tiên theo thứ tự:

**Xác định LỆNH cập nhật đúng cho máy này:**
- **Bản cài SKILL** (KHÔNG có `scripts/update.command` trong project; CORE ở `~/.claude/kora-framework`) → cập nhật =
  **chạy lại installer**: `bash <(curl -fsSL https://raw.githubusercontent.com/isc-fkit/Kora-Framework/release/install.command)`
  (Windows: tải `install.bat` về `%TEMP%` rồi chạy). Kéo CORE+skill mới, **GIỮ NGUYÊN tri thức** (vault/config/.env/docs).
- **Bản DEV / có `scripts/update.command`** → `bash scripts/update.command` (git pull --ff-only nếu có `.git`; else tải
  `release.zip` ghi đè **chỉ CORE**, loại trừ MỌI DATA: vault `*_Brain/`, `.kb/*`, `docs/`, `inbox/`, `config/factory-config.yaml`,
  `config/domain-rules.md`, `.env.*`; KHÔNG `--delete`).

**1. ⚡ ƯU TIÊN — có MCP `local-terminal` (`run_command`, Claude Desktop)?** → gọi `run_command(command="<lệnh cập nhật ở trên>")`
   chạy THẲNG trên máy thật (ngoài sandbox), tường thuật output → sang Bước 4. **KHÔNG bắt user tự mở Terminal.**
**2. KHÔNG có `run_command` → BÀN GIAO Terminal:** đưa user **đúng 1 lệnh** ở trên để dán vào **Terminal** chạy; xong
   user gõ **"đã cập nhật"** → làm Bước 4. (Tuyệt đối KHÔNG bảo double-click `.command` — macOS Gatekeeper chặn; chạy bằng `bash`.)

## Bước 4 — Sau cập nhật

1. Đọc lại `version.json` → báo "đã lên vY (Kora-…)".
2. **Đọc lại `CLAUDE.md` + `workflows/`** (vừa có thể đổi) trước khi làm việc tiếp.
3. Chạy `python3 tools/kb-indexer/build_index.py --root .` (Windows: `py`) (phòng khi indexer đổi).
4. Bản mới có bước "migration" (đổi cấu trúc config/vault) → làm theo `CHANGELOG.md`;
   TUYỆT ĐỐI không tự ý đổi cấu trúc DATA của user khi CHANGELOG không nói.
