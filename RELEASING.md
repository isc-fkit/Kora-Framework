# Phát hành & Deploy — Genesis-1

> Repo này đóng **2 vai**:
> 1. **Landing page** — GitHub Pages tự deploy `index.html` MỖI lần push lên `release`.
> 2. **App base** — người dùng tải zip về, cài trong Cowork; cập nhật bằng cách so `version.json`.
>
> 👉 Tín hiệu "có bản APP mới" là **`version.json`** — KHÔNG phải việc Pages deploy.

**⚡ Nhanh nhất:** gõ **"phát hành"** trong Cowork → Claude chạy `workflows/12-release.md`:
tự xác định landing-only hay app-release, bump `version.json` + ghi `CHANGELOG.md`, rồi push (có confirm).
Tài liệu dưới đây để hiểu/đối chiếu khi làm tay.

---

## Quy tắc 1 dòng

- **Đổi `version.json` (tăng version) = PHÁT HÀNH APP** → app đã cài thấy bản mới khi gõ `cập nhật phiên bản`.
- **KHÔNG đổi `version.json` = chỉ deploy landing** → web cập nhật, app đã cài KHÔNG báo có bản mới.

GitHub Pages deploy lại web mỗi lần push (kể cả landing-only) — điều đó **bình thường và độc lập**
với app. App đã cài chỉ đọc `version.json`, không quan tâm Pages.

| Bạn muốn | Đổi `version.json`? | Kết quả |
|---|---|---|
| Chỉnh landing/web | KHÔNG | Pages deploy web; app đã cài im lặng |
| Vá lỗi / thêm tính năng cho app | CÓ (tăng) | App báo cập nhật được + Pages deploy |

---

## A. Chỉ sửa landing page (index.html / ảnh / chữ giới thiệu)

1. Sửa `index.html` (hoặc asset landing).
2. **GIỮ NGUYÊN `version.json`.**
3. `git add -A && git commit && git push origin release`.

→ GitHub Pages tự deploy web mới. App đã cài: không có gì thay đổi, không bị làm phiền.

## B. Phát hành bản app mới (sửa CORE)

CORE = `workflows/`, `tools/`, `CLAUDE.md`, `scripts/`, `templates/`, `config/domain-presets/`,
`config/factory-config.example.yaml`, `kb-indexer/`, `index.html`…

1. Sửa code CORE.
2. **Tăng `version.json`** theo ngữ nghĩa (semantic):
   - `1.0.0 → 1.0.1` — **vá lỗi** (patch).
   - `1.0.0 → 1.1.0` — **thêm tính năng** (minor).
   - `1.0.0 → 2.0.0` — **thay đổi phá vỡ / cần migration** (major).
   - Đổi `released` = ngày phát hành. `codename` giữ `"Genesis-1"` đến đời lớn kế tiếp.
2b. **Đồng bộ nhãn version trên landing `index.html`** theo version mới: thẻ `mc-ver` +
   footer `Phiên bản: Genesis-1 (vX.Y.Z)`. (Quên → web hiện version cũ. Soát:
   `grep -n 'mc-ver\|Phiên bản:' index.html`.)
3. **Thêm mục vào `CHANGELOG.md`**: từ vX → vY có gì mới. Nếu cần user/Claude thao tác thêm
   (migration: đổi cấu trúc config/vault…) → ghi RÕ các bước ở đây — `workflows/10-update.md`
   sẽ đọc CHANGELOG để biết "cần làm những gì" và làm theo.
4. `git commit && git push origin release`.
   (Tùy chọn đánh dấu bản phát hành: `git tag vX.Y.Z-genesis-1 && git push origin vX.Y.Z-genesis-1`.)

→ App đã cài: user gõ **`cập nhật phiên bản`** → so `version.json` local với `release` → thấy mới hơn →
   xem "có gì mới" từ CHANGELOG → confirm → tải CORE mới, **GIỮ nguyên tri thức (DATA)**.
   Pages cũng tự deploy web mới luôn.

---

## C. Force update + nội dung giới thiệu (thông báo cho app bản cũ)

`version.json` có 2 field tùy chọn để chủ động báo cho người dùng bản cũ:

```json
{
  "version": "1.0.2",
  "force": false,
  "intro": "Mô tả ngắn bản này có gì — hiện cho user khi họ kiểm tra cập nhật."
}
```

- **`force`** (bool, mặc định `false`): `true` = bản BẮT BUỘC / ưu tiên cập nhật → khi user bản
  cũ kiểm tra, `workflows/10-update.md` hiện khung **"🔴 Bản cập nhật quan trọng"** + lời lẽ mạnh
  hơn (vẫn chờ user đồng ý, không tự ép).
- **`intro`** (string, mặc định `""`): nội dung giới thiệu hiện **nổi bật đầu tiên** khi user bản
  cũ kiểm tra cập nhật (kèm tóm tắt CHANGELOG + cách nâng cấp).
- **Khi nào user thấy?** Theo thiết kế hiện tại: **chỉ khi user chủ động** gõ "cập nhật phiên bản" /
  "kiểm tra phiên bản" (KHÔNG nag tự động mỗi phiên).
- Lúc phát hành, `workflows/12-release.md` Bước 1b hỏi force? + nội dung giới thiệu rồi ghi 2 field này.

---

## Lưu ý

- `index.html` thuộc CORE → khi app cập nhật (vì version tăng) nó cũng được tải mới. **Vô hại**
  (app không chạy `index.html` lúc làm việc). Nên cứ sửa landing thoải mái mà không sợ ảnh hưởng app.
- Nút **"Tải về"** trên web trỏ `…/archive/refs/heads/release.zip` = luôn là bản mới nhất trên `release`.
- **Migration** (đổi cấu trúc DATA của user) PHẢI ghi trong `CHANGELOG.md`; `workflows/10-update.md`
  TUYỆT ĐỐI không tự đổi cấu trúc DATA nếu CHANGELOG không nói.
- Lịch sử **app** ở `CHANGELOG.md`; lịch sử **tri thức của user** ở `.kb/changelog.md` (khác nhau).
