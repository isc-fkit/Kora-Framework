---
description: Maintainer-only. Automate a release — choose version bump + branch scope (default: ĐỒNG BỘ cả 5 nhánh env dev/qc/uat/release/main), bump version.json + CHANGELOG + map index.html labels, then commit/push/ff-merge/tag/GitHub Release. Excluded from end-user installs.
---

The user invoked `/claude-knowledge-release` — automate a release (**MAINTAINER ONLY**; skill này KHÔNG được phát hành
cho người dùng — installer/update tự loại `claude-knowledge-release.md` + `workflows/12-release.md` khỏi bản cài).

Read and execute `workflows/12-release.md` following `CLAUDE.md`. Drive với AskUserQuestion (mỗi câu 1 thẻ).

### Bước 0 — Guard (BẮT BUỘC)
Verify `.maintainer` tồn tại ở repo root **và** `git remote -v` trỏ đúng repo gốc + push được. Nếu KHÔNG →
**DỪNG NGAY**, nói nhẹ nhàng (KHÔNG bump, KHÔNG sửa CHANGELOG, KHÔNG push); gợi ý `/claude-knowledge-update` hoặc
`/claude-knowledge-export-knowledge-base`. (Bảo vệ kép: dù lỡ chạy tiếp, `git push` vẫn cần quyền repo gốc.)

### Bước 1 — HỎI (AskUserQuestion, lần lượt)
1. **Có phát hành version MỚI không?**
   - **[Có — bump version]** → sang Bước 2 (bump + CHANGELOG + map index.html).
   - **[Không — chỉ push landing/code]** → GIỮ NGUYÊN `version.json`, bỏ qua Bước 2, sang Bước 3 (Luồng A).
2. **Phạm vi nhánh đẩy** — repo có **5 nhánh env** (`dev` · `qc` · `uat` · `release` · `main`) giữ **ĐỒNG BỘ cùng
   1 commit**. Trước khi hỏi, chạy `git ls-remote --heads origin` xem nhánh nào đang lệch.
   - **[Tất cả nhánh env] (khuyến nghị)** → commit trên `release` → push `release` → **ff-merge `release`→ dev/qc/uat/main**
     + push từng nhánh. Đây là cách v2.3.0/v2.3.1 đã làm.
   - **[Chỉ release]** → chỉ `git push origin release` (GitHub Pages deploy web từ `release`).
   - **[release → main]** → push `release`, rồi ff-merge vào `main`.
   - **[Other]** → nhập danh sách nhánh.
   > Chỉ **ff-merge** (`git merge --ff-only`); nhánh nào KHÔNG ff được → **BÁO user, BỎ QUA nhánh đó, KHÔNG ép** (không force-push).

### Bước 2 — Bump version (chỉ khi câu 1 = "Có")
1. Đọc `version.json`; đề xuất **semantic** kế tiếp (giữ codename "Kora-1"); hỏi **[patch]/[minor]/[major]**.
2. **Auto CHANGELOG:** sinh entry mới từ `git log <last-tag>..HEAD` (group feat/fix/docs…); cho review/sửa.
3. Ghi `version.json`: `version` mới + `released` = hôm nay + `force` + `intro`.
4. **MAP index.html theo version mới (BẮT BUỘC — "mapping"):**
   - Brand sidebar: `<div class="fw">KORA AI<span>vX.Y.Z · Kora-1</span></div>`.
   - Badge hero: `<span class="badge">FPT Telecom · KORA AI · vX.Y.Z · "Kora-1"</span>`.
   - Release Note (`#release`): thêm **card version mới** (ngày + bullet từ CHANGELOG) + chuyển badge **MỚI NHẤT**
     sang card đó + cập nhật callout "Bản mới nhất (latest): vX.Y.Z" + tăng tổng số bản.
   - Soát: `grep -nE 'v[0-9]+\.[0-9]+\.[0-9]+' index.html` → mọi nhãn version khớp `version.json` (đừng để web hiện bản cũ).
5. Nếu `install.command`/`uninstall.command` đổi → re-zip `*.command.zip`.

### Bước 3 — ✋ GATE confirm → commit → push → merge → tag → release
Push là thao tác công khai → **BẮT BUỘC chờ user đồng ý**. KHÔNG commit secret (soát `git add -An` không có `.env*`/token).
1. `git add -A && git commit -m "<mô tả>"` (trên `release`). Commit message kết bằng dòng `Co-Authored-By` theo CLAUDE.md.
2. **Đẩy theo phạm vi đã chọn (câu 2):**
   - **Tất cả nhánh env:** `git push origin release` → rồi vòng lặp từng nhánh:
     `for b in dev qc uat main; do git checkout $b && git merge --ff-only release && git push origin $b; done` →
     `git checkout release`. Nhánh nào không ff → bỏ qua + báo.
   - **Chỉ release:** `git push origin release`.
   - **release → main:** `git push origin release` rồi `git checkout main && git merge --ff-only release && git push origin main && git checkout release`.
3. **Tag = version** (chỉ khi bump): `git tag vX.Y.Z && git push origin vX.Y.Z` — phải TRÙNG `version.json.version`.
4. **GitHub Release** (nếu có `gh`): `gh release create vX.Y.Z --title "Kora-1 vX.Y.Z" --notes "<entry CHANGELOG>" --target release`.

### Bước 4 — Kiểm version khớp + báo cáo
Verify **CÙNG `vX.Y.Z`** ở: `version.json.version` · header `CHANGELOG` (`## vX.Y.Z`) · **index.html** (brand sidebar
+ hero badge + callout "Bản mới nhất: vX.Y.Z" + card MỚI NHẤT) · `git tag` · GitHub Release. Đồng thời
`git ls-remote --heads origin` xác nhận các nhánh đã chọn cùng 1 commit. Sửa mọi lệch.
Báo: **web (Pages) deployed**; app users nhận qua `/claude-knowledge-update`. Never push without the gate; keep secrets out of commits.
