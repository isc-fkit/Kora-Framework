# Workflow 12 — Phát hành phiên bản (release) & deploy

> Trigger: "phát hành", "release", "lên version", "ra bản mới", "tăng version" (confirm ý định trước).
> Đây là phía NGƯỜI PHÁT HÀNH (khác `workflows/10-update.md` là phía người DÙNG đi cập nhật).
> Quy ước đầy đủ: `RELEASING.md`. **Codename GIỮ "Kora-1", chỉ TĂNG SỐ version (semantic).**

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
>
> 📦 **KHÔNG phát hành cho người dùng:** `kora-release.md` (skill) + `workflows/12-release.md` +
> `workflows/13-evolve-system.md` bị **installer/update TỰ LOẠI** khỏi bản cài (`install.command`/`.bat`,
> `scripts/update.command`) — chỉ tồn tại trên repo của người duy trì. Người dùng thường không thấy lệnh phát hành.

## Bước 0b — HỎI 3 câu trước khi làm (qua `/kora-release`)

1. **Có phát hành version MỚI không?** → [Có — bump] (Luồng B/Bước 2B) / [Không — chỉ push landing/code] (Luồng A/Bước 2A).
2. **Push lên nhánh nào?** → [release] (mặc định) / [main] / [Other].
3. **Merge nhánh nào → nhánh nào?** → [release → main] / [Không merge] / [Other]. Chỉ ff-merge.

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
   - `codename` GIỮ `"Kora-1"` (chỉ đổi khi sang một đời lớn hoàn toàn mới).
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
2b. **BẮT BUỘC — MAP nhãn version trên landing `index.html`** theo `version` mới (3 chỗ):
   - **Brand sidebar:** `<div class="fw">KORA AI<span>vX.Y.Z · Kora-1</span></div>`.
   - **Badge hero:** `<span class="badge">FPT Telecom · KORA AI · vX.Y.Z · "Kora-1"</span>`.
   - **Release Note (`#release`):** thêm **card version mới** (ngày + bullet rút từ CHANGELOG), chuyển badge
     **MỚI NHẤT** sang card đó, cập nhật callout *"Bản mới nhất (latest): vX.Y.Z"* + tăng tổng số bản.
   Soát: `grep -nE 'v[0-9]+\.[0-9]+\.[0-9]+' index.html` → mọi nhãn version khớp `version.json`
   (quên bước này → web hiện version cũ dù đã phát hành bản mới).
3. Thêm mục ĐẦU vào `CHANGELOG.md`:
   `## vX.Y.Z "Kora-1" — YYYY-MM-DD` + các gạch đầu dòng "có gì mới".
   **Nếu cần thao tác khi cập nhật** (migration: đổi cấu trúc config/vault…) → ghi RÕ các bước ở đây —
   `workflows/10-update.md` đọc CHANGELOG để biết "cần làm những gì" và làm theo.
4. Trình bày tóm tắt cho user: version cũ → mới, danh sách "có gì mới", có migration không.
5. ✋ **GATE — confirm** (push là thao tác công khai, BẮT BUỘC chờ user đồng ý).
6. `git add -A && git commit -m "Kora-1 vX.Y.Z: <tóm tắt>"`.
6b. **HỎI: Phạm vi nhánh đẩy? — AskUserQuestion** (repo 5 nhánh env `dev/qc/uat/release/main` giữ đồng bộ 1 commit):
   - **[Tất cả nhánh env] (khuyến nghị)** → `git push origin release`, rồi
     `for b in dev qc uat main; do git checkout $b && git merge --ff-only release && git push origin $b; done && git checkout release`.
     Đây là cách v2.3.0/v2.3.1 đã làm (mọi nhánh cùng commit).
   - **[Deploy từ `release`]** → chỉ `git push origin release` → GitHub Pages deploy web từ `release`.
   - **[Merge `release` → `main`]** → `git push origin release`, rồi `git checkout main && git merge --ff-only
     release && git push origin main && git checkout release`.
   - Nhánh nào **không ff-merge được** → BÁO user, **BỎ QUA**, KHÔNG ép (không force-push).
6c. **Đánh tag KHỚP version** (BẮT BUỘC; KHÔNG thêm hậu tố codename):
   `git tag vX.Y.Z && git push origin vX.Y.Z` — `vX.Y.Z` phải **TRÙNG** `version.json.version`.
6d. **GitHub Release + release note** (nếu có `gh`): nội dung = đúng mục CHANGELOG vừa thêm:
   `gh release create vX.Y.Z --title "Kora-1 vX.Y.Z" --notes "<nội dung mục CHANGELOG vX.Y.Z>"`.
7. **KIỂM VERSION KHỚP (5 nơi)** trước khi xong: `version.json.version` == header `CHANGELOG`
   (`## vX.Y.Z`) == **brand + badge `index.html`** (Bước 2b) == git tag `vX.Y.Z` == GitHub Release.
   Lệch chỗ nào → sửa cho khớp rồi báo.
8. Báo: app đã cài gõ **`cập nhật phiên bản`** sẽ thấy bản này (đọc CHANGELOG → confirm → tải CORE, giữ DATA);
   **web (GitHub Pages) đã deploy** bản mới.

## Guardrails

- **Push = outward-facing → LUÔN confirm trước** (Approval Gate). Không tự push.
- **KHÔNG bump version cho thay đổi chỉ-landing** (tránh làm phiền app đã cài bằng "có bản mới" giả).
- **Migration phải nằm trong `CHANGELOG.md`**; `workflows/10-update.md` không tự đổi cấu trúc DATA của
  user nếu CHANGELOG không nói.
- Lịch sử **app** = `CHANGELOG.md`; lịch sử **tri thức của user** = `.kb/changelog.md` (đừng lẫn).
- Chưa từng push lần nào → bản đầu là `v1.0.0` (không cần bump); từ lần sau mới tăng số.
