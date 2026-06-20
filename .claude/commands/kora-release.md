---
description: Maintainer-only. Automate a release — ask which branch to push, which branches to merge, and whether to publish a NEW version; if yes, bump version.json + CHANGELOG + map index.html, then commit/push/tag/deploy. Excluded from end-user installs.
---

The user invoked `/kora-release` — automate a release (**MAINTAINER ONLY**; skill này KHÔNG được phát hành
cho người dùng — installer/update tự loại `kora-release.md` + `workflows/12-release.md` khỏi bản cài).

Read and execute `workflows/12-release.md` following `CLAUDE.md`. Drive với AskUserQuestion (mỗi câu 1 thẻ).

### Bước 0 — Guard (BẮT BUỘC)
Verify `.maintainer` tồn tại ở repo root **và** `git remote -v` trỏ đúng repo gốc + push được. Nếu KHÔNG →
**DỪNG NGAY**, nói nhẹ nhàng (KHÔNG bump, KHÔNG sửa CHANGELOG, KHÔNG push); gợi ý `/kora-update` hoặc
`/kora-export-knowledge-base`. (Bảo vệ kép: dù lỡ chạy tiếp, `git push` vẫn cần quyền repo gốc.)

### Bước 1 — HỎI 3 câu (AskUserQuestion, lần lượt)
1. **Có phát hành version MỚI không?**
   - **[Có — bump version]** → sang Bước 2 (bump + CHANGELOG + map index.html).
   - **[Không — chỉ push landing/code]** → GIỮ NGUYÊN `version.json`, bỏ qua Bước 2, sang Bước 3 (Luồng A).
2. **Push lên nhánh nào?** → **[release]** (mặc định) / **[main]** / **[Other]** (nhập tên nhánh).
3. **Merge nhánh nào → nhánh nào?** → **[release → main]** / **[Không merge]** / **[Other]** (nhập `src → dst`).
   Chỉ **ff-merge** (`git merge --ff-only`); không ff được → BÁO user, KHÔNG ép.

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
Push là thao tác công khai → **BẮT BUỘC chờ user đồng ý**.
1. `git add -A && git commit -m "<mô tả>"`.
2. **Push** lên nhánh đã chọn (câu 2): `git push origin <branch>`.
3. **Merge** nếu chọn (câu 3): `git checkout <dst> && git merge --ff-only <src> && git push origin <dst> && git checkout <src>`.
4. **Tag = version** (chỉ khi bump): `git tag vX.Y.Z && git push origin vX.Y.Z` — phải TRÙNG `version.json.version`.
5. **GitHub Release** (nếu có `gh`): `gh release create vX.Y.Z --title "Kora-1 vX.Y.Z" --notes "<entry CHANGELOG>"`.

### Bước 4 — Kiểm version khớp (5 nơi) + báo cáo
`version.json` == header `CHANGELOG` == **brand index.html** == **badge index.html** == git tag == GitHub Release.
Sửa mọi lệch. Báo: **web (Pages) deployed**; app users nhận qua `/kora-update`. Never push without the gate; keep secrets out of commits.
