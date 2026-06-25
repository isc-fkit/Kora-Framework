# report-mailer — Gửi báo cáo tiến độ qua email (SMTP)

Gửi dashboard báo cáo (workflow 14 / lịch 08) tới danh sách email — **full-auto**, chạy
được cả khi phiên nền. Chỉ dùng thư viện chuẩn Python (không cần cài thêm).

## Cài 1 lần
1. Copy `.env.local.example` → `.env.local` (cùng thư mục này). File `.env.local` đã được
   gitignore, KHÔNG commit, KHÔNG dán nội dung vào chat.
2. Điền SMTP. **Gmail:** bật 2FA → tạo **App Password** tại
   https://myaccount.google.com/apppasswords → dán vào `SMTP_PASS`.

## Dùng
```bash
# Gửi thử (không cần report) tới chính mình:
python3 tools/report-mailer/send_report.py --test

# Gửi báo cáo thật (nhúng + đính kèm HTML):
python3 tools/report-mailer/send_report.py \
  --to "a@x.com,b@y.com" \
  --subject "Báo cáo tiến độ 2026-06-18" \
  --html-file reports/progress-report-latest.html
```
Windows: thay `python3` bằng `py`.

## Cấu hình người nhận
Danh sách email + bật/tắt nằm ở `config/factory-config.yaml` mục `reports.email`
(không phải secret). Mật khẩu **chỉ** ở `.env.local`. Workflow đọc `reports.email.to`
rồi truyền vào `--to`.

## Gmail API fallback (HTTPS 443 qua proxy) — cho mạng chặn SMTP
Mạng công ty có thể chặn **MỌI cổng SMTP** (587/465/25/2525) nhưng cho proxy CONNECT tới 443.
Khi đó SMTP gửi không được. Bật fallback để `send_report.py` **tự gửi lại CÙNG email qua Gmail API
(HTTPS)**, định tuyến qua proxy — giữ nguyên tài khoản gửi, banner CID, đính kèm.

**Bật 1 lần:**
1. Google Cloud Console: tạo project → bật **Gmail API** → tạo **OAuth client "Desktop app"**
   (Client ID + Secret). Consent screen nên **Publish** để refresh token không hết hạn sau 7 ngày.
2. Lấy refresh token:
   ```bash
   HTTPS_PROXY=http://proxy.hcm.fpt.vn:80 \
   python3 tools/report-mailer/gmail_oauth_setup.py --client-id <ID> --client-secret <SECRET>
   ```
   → in 3 dòng `export GMAIL_OAUTH_*` để dán vào `~/.zshrc` **hoặc** `.env.local` (bỏ chữ `export`).
   Lịch nền (cron/launchd) KHÔNG đọc shell → phải để trong `.env.local`. Thêm `HTTPS_PROXY` cùng chỗ.
3. Kiểm tra: `python3 tools/report-mailer/send_report.py --check` (kiểm cả SMTP lẫn Gmail API),
   hoặc ép HTTPS: `--check --transport https`.

**Cờ `--transport`:** `auto` (mặc định — SMTP rồi fallback Gmail API khi mạng chặn) ·
`smtp` (chỉ SMTP) · `https` (ép Gmail API). Lỗi **sai App Password** (`SMTP_AUTH_FAILED`) **KHÔNG**
fallback (lỗi credential, không phải mạng) — chỉ lỗi **kết nối** SMTP mới chuyển HTTPS.
