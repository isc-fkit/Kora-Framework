# Workflow 12 — Phát hành phiên bản (release) & deploy

> Trigger: "phát hành", "release", "lên version", "ra bản mới", "tăng version" (confirm ý định trước).
> Đây là phía NGƯỜI PHÁT HÀNH (khác `workflows/10-update.md` là phía người DÙNG đi cập nhật).
> Quy ước đầy đủ: `RELEASING.md`. **Codename GIỮ "Genesis-1", chỉ TĂNG SỐ version (semantic).**

## Bước 0 — CHỈ người DUY TRÌ app mới phát hành được (KIỂM TRA TRƯỚC TIÊN)

Lệnh "phát hành" KHÔNG dành cho user đã cài app — chỉ chủ repo. Kiểm tra NGAY:

1. Có file `.maintainer` ở gốc repo không? (file này gitignore → chỉ máy maintainer có,
   KHÔNG đi kèm bản tải về / clone).
   - **KHÔNG có → DỪNG NGAY**, nói nhẹ nhàng (KHÔNG bump version, KHÔNG sửa CHANGELOG, KHÔNG push):
     > *"Lệnh 'phát hành' là của người DUY TRÌ app (tác giả). Bạn đang dùng bản đã cài rồi.
     > Có lẽ bạn muốn: gõ **'cập nhật phiên bản'** để lấy bản mới nhất, hoặc **'sao lưu'** để backup
     > tri thức. Hai lệnh đó mới đúng cho người dùng."*
   - **Có `.maintainer`** → tiếp tục.
2. Có `.git` + `git remote -v` trỏ đúng repo gốc + push được → OK, sang Bước 1.
   (Chủ repo trên máy MỚI mà chưa có `.maintainer` → hỏi xác nhận "bạn có phải người duy trì repo
   này?" rồi mới tạo `.maintainer` và tiếp.)

> 🔒 **Bảo vệ kép:** dù có lỡ chạy tiếp, `git push` vẫn cần quyền đẩy lên repo gốc — user thường
> KHÔNG có quyền → push thất bại an toàn, không đụng được repo gốc.

## Bước 1 — Xác định loại thay đổi

Chạy `git status --short` + `git diff --stat` → xem đã đổi gì:

- **Chỉ landing** (chỉ `index.html` / asset web / README hiển thị) → **Luồng A** (deploy landing, KHÔNG bump version).
- **Có CORE** (`workflows/`, `tools/`, `CLAUDE.md`, `scripts/`, `templates/`, `config/domain-presets/`,
  `config/factory-config.example.yaml`, `tools/kb-indexer/`, **`.kb/rules.md`, `.kb/system-lessons.md`**)
  → **Luồng B** (phát hành app, BUMP version).
- Không chắc → hỏi user: *"Bản này có muốn app đã cài cập nhật được không?"* — CÓ → B, KHÔNG → A.

## Bước 2A — Chỉ deploy landing (KHÔNG bump)

1. **GIỮ NGUYÊN `version.json`.**
2. ✋ confirm → `git add -A && git commit -m "<mô tả landing>" && git push origin release`.
3. Báo: GitHub Pages sẽ tự deploy web mới; **app đã cài không bị ảnh hưởng** (vì version không đổi).

## Bước 2B — Phát hành app mới (BUMP version)

1. Đọc `version` hiện tại trong `version.json`. **Chọn mức tăng** (hỏi user nếu chưa rõ):
   - **patch** `x.y.(Z+1)` — vá lỗi.
   - **minor** `x.(Y+1).0` — thêm tính năng.
   - **major** `(X+1).0.0` — thay đổi phá vỡ / cần migration.
   - `codename` GIỮ `"Genesis-1"` (chỉ đổi khi sang một đời lớn hoàn toàn mới).
1b. **Force hay không + nội dung giới thiệu** (cơ chế thông báo cho app bản cũ):
   - *AskUserQuestion* (2 lựa chọn): **"Bản này BẮT BUỘC / ưu tiên cập nhật (force)?"**
     → `[Có — bản quan trọng]` / `[Không — cập nhật thường]`.
   - **Hỏi "Nội dung giới thiệu"** (input TỰ DO → hỏi bằng **câu thường**, KHÔNG AskUserQuestion):
     *"Nội dung giới thiệu hiện cho người dùng khi họ kiểm tra bản mới là gì? (vd: 'Bản này vá
     lỗi bảo mật quan trọng, nên cập nhật sớm.' — để trống nếu không cần.)"*
   - Ghi vào `version.json`: `force: true/false` + `intro: "<nội dung>"` (để trống = `""`).
     `workflows/10-update.md` Bước 2 sẽ hiện `intro` + đánh dấu khi `force:true` cho user bản cũ.
2. Sửa `version.json`: `version` mới + `released` = **ngày hôm nay** + `force` + `intro` (Bước 1b).
   (giữ `name`, `repo`, `codename`)
2b. **BẮT BUỘC — đồng bộ nhãn version hiển thị trên landing `index.html`** theo `version` mới:
   thẻ model card `<span class="mc-ver">vX.Y.Z</span>` VÀ footer `Phiên bản: <b>Genesis-1 (vX.Y.Z)</b>`.
   (Quên bước này → web hiện version cũ dù đã phát hành bản mới. `grep -n 'mc-ver\|Phiên bản:' index.html`
   để soát.)
3. Thêm mục ĐẦU vào `CHANGELOG.md`:
   `## vX.Y.Z "Genesis-1" — YYYY-MM-DD` + các gạch đầu dòng "có gì mới".
   **Nếu cần thao tác khi cập nhật** (migration: đổi cấu trúc config/vault…) → ghi RÕ các bước ở đây —
   `workflows/10-update.md` đọc CHANGELOG để biết "cần làm những gì" và làm theo.
4. Trình bày tóm tắt cho user: version cũ → mới, danh sách "có gì mới", có migration không.
5. ✋ **GATE — confirm** (push là thao tác công khai, BẮT BUỘC chờ user đồng ý).
6. `git add -A && git commit -m "Genesis-1 vX.Y.Z: <tóm tắt>" && git push origin release`.
   Tùy chọn đánh dấu: `git tag vX.Y.Z-genesis-1 && git push origin vX.Y.Z-genesis-1`.
7. Báo: app đã cài gõ **`cập nhật phiên bản`** sẽ thấy bản này (đọc CHANGELOG → confirm → tải CORE, giữ DATA);
   GitHub Pages cũng deploy web mới luôn.

## Guardrails

- **Push = outward-facing → LUÔN confirm trước** (Approval Gate). Không tự push.
- **KHÔNG bump version cho thay đổi chỉ-landing** (tránh làm phiền app đã cài bằng "có bản mới" giả).
- **Migration phải nằm trong `CHANGELOG.md`**; `workflows/10-update.md` không tự đổi cấu trúc DATA của
  user nếu CHANGELOG không nói.
- Lịch sử **app** = `CHANGELOG.md`; lịch sử **tri thức của user** = `.kb/changelog.md` (đừng lẫn).
- Chưa từng push lần nào → bản đầu là `v1.0.0` (không cần bump); từ lần sau mới tăng số.
