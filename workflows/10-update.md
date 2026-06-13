# Workflow 10 — Cập nhật phiên bản (GIỮ NGUYÊN tri thức)

> Trigger: "cập nhật model", "kiểm tra phiên bản model", "có bản model mới không" (confirm ý định trước).
> ⚠️ Từ **"cập nhật" trơ** dễ trùng câu giao tiếp thường → KHÔNG tự chạy; HỎI xác nhận
> *"Bạn muốn kiểm tra cập nhật model, hay chỉ đang nói chuyện?"* rồi mới chạy.
> Nên TỰ kiểm tra ở cuối setup (workflow 00 Bước 7) và khi user hỏi "đang bản nào".
>
> **Mô hình phát hành:** user TẢI ZIP → giải nén → mở trong Cowork → setup. Đa số KHÔNG có
> `.git`. Cập nhật = tải phần CORE mới đè lên, GIỮ NGUYÊN DATA (xem CLAUDE.md §6).

## Bước 1 — So phiên bản

1. Đọc `version.json` ở gốc repo → version + codename hiện tại.
2. Lấy bản mới nhất trên GitHub (WebFetch):
   `https://raw.githubusercontent.com/luugiakhanh689/adaptive_knowledge_base/release/version.json`
   — offline/không lấy được → báo "chưa kiểm tra được bản mới, thử lại khi có mạng", DỪNG.
3. So `version`:
   - Bằng nhau → "Bạn đang ở bản mới nhất: Genesis-1 vX.Y.Z." DỪNG.
   - GitHub mới hơn → sang Bước 2.

## Bước 2 — Trình bày + ✋ confirm

- Lấy "có gì mới" từ GitHub CHANGELOG:
  `https://raw.githubusercontent.com/luugiakhanh689/adaptive_knowledge_base/release/CHANGELOG.md`
  → tóm tắt tiếng Việt: từ vX → vY có gì mới.
- Nhấn mạnh: **tri thức của bạn (vault, `.kb`, config, docs) GIỮ NGUYÊN** — chỉ thay phần chương trình.
- Hỏi confirm: "Cập nhật ngay chứ?" (thao tác GHI/NẶNG — bắt buộc confirm).

## Bước 3 — Chạy cập nhật

Chạy `scripts/update.command` (Claude tự chạy trong Cowork; sandbox chặn mạng → hướng dẫn user double-click file):
- Có `.git` → `git pull --ff-only` (DATA đã gitignore nên không đụng).
- Không có `.git` (bản zip) → tải `…/archive/refs/heads/release.zip`, giải nén, **chỉ ghi đè CORE**;
  loại trừ MỌI DATA (vault `*_Brain/`, `.kb/*`, `docs/` nội dung, `inbox/`,
  `config/factory-config.yaml`, `config/domain-rules.md`, `.env.*`). KHÔNG dùng `--delete`.

Tường thuật tiến độ. Lỗi mạng/quyền → hướng dẫn double-click `scripts/update.command`.

## Bước 4 — Sau cập nhật

1. Đọc lại `version.json` → báo "đã lên vY (Genesis-…)".
2. **Đọc lại `CLAUDE.md` + `workflows/`** (vừa có thể đổi) trước khi làm việc tiếp.
3. Chạy `python3 tools/kb-indexer/build_index.py --root .` (phòng khi indexer đổi).
4. Bản mới có bước "migration" (đổi cấu trúc config/vault) → làm theo `CHANGELOG.md`;
   TUYỆT ĐỐI không tự ý đổi cấu trúc DATA của user khi CHANGELOG không nói.
