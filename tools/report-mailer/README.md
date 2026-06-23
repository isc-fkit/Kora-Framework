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
