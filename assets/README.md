# assets/ — ảnh cho trang landing & email báo cáo

Đặt 2 ảnh sau vào thư mục này (đã được tham chiếu trong `index.html` và email báo cáo):

| File | Dùng ở đâu | Gợi ý kích thước |
|---|---|---|
| `flow.png` | `index.html` — mục **Nguyên lý hoạt động** (sơ đồ KORA AI) | ~1670×940, PNG |
| `banner-daily-report.png` | **Header email** báo cáo tiến độ + mục **Mail & Báo cáo** trên trang | ~2000×600, PNG |

> Email nhúng banner qua **URL public** (`reports.email.banner_url` trong config — mặc định raw GitHub
> nhánh `release`). Email client KHÔNG load file local, nên ảnh phải public (raw.githubusercontent / Pages).
