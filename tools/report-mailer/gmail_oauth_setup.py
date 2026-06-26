#!/usr/bin/env python3
"""
gmail_oauth_setup.py — Lấy GMAIL_OAUTH_REFRESH_TOKEN MỘT LẦN (luồng installed-app loopback).

Dùng khi muốn bật FALLBACK gửi mail qua Gmail API/HTTPS (xem gmail_api.py + send_report.py).
CHỈ thư viện chuẩn. Đi qua HTTPS_PROXY nên chạy được trên mạng công ty chặn SMTP.

Chuẩn bị (1 lần, ở Google Cloud Console):
  1. Tạo project → bật "Gmail API".
  2. OAuth consent screen: kiểu "External", thêm tài khoản gửi (vd ftel.medicare@gmail.com) vào
     Test users; NÊN "Publish" app để refresh_token không hết hạn sau 7 ngày.
  3. Credentials → Create OAuth client ID → type "Desktop app" → lấy Client ID + Client secret.

Chạy:
  HTTPS_PROXY=http://proxy.hcm.fpt.vn:80 \
  python3 tools/report-mailer/gmail_oauth_setup.py \
      --client-id <CLIENT_ID> --client-secret <CLIENT_SECRET>
  (hoặc export GMAIL_OAUTH_CLIENT_ID / GMAIL_OAUTH_CLIENT_SECRET trước rồi chạy không cần cờ.)

Xong → script in 3 dòng export để bạn DÁN vào ~/.zshrc (hoặc tools/report-mailer/.env.local).
Refresh token chỉ in 1 lần để bạn tự lưu — KHÔNG ghi ra file/git.
"""
import argparse
import os
import secrets
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gmail_api  # noqa: E402  (cùng thư mục)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"


class _OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        q = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(q)
        self.server.auth_code = (params.get("code") or [None])[0]
        self.server.state_recv = (params.get("state") or [None])[0]
        self.server.auth_error = (params.get("error") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        ok = self.server.auth_code and not self.server.auth_error
        msg = ("✅ Đã nhận mã uỷ quyền — bạn có thể đóng tab này và quay lại Terminal."
               if ok else "❌ Uỷ quyền thất bại — xem lại Terminal.")
        self.wfile.write(f"<html><body style='font-family:sans-serif'><h3>{msg}</h3></body></html>"
                         .encode("utf-8"))

    def log_message(self, *a):  # tắt log mặc định
        pass


def _exchange_code(code, client_id, client_secret, redirect_uri, proxy):
    import json
    import urllib.error
    import urllib.request
    data = urllib.parse.urlencode({
        "code": code, "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect_uri, "grant_type": "authorization_code",
    }).encode("ascii")
    req = urllib.request.Request(
        gmail_api.OAUTH_TOKEN_URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with gmail_api._build_opener(proxy).open(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"❌ Đổi code→token lỗi HTTP {e.code}: {gmail_api._safe_read(e)}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        sys.exit(f"❌ Không kết nối được oauth2.googleapis.com (kiểm tra HTTPS_PROXY): {e}")


def _upsert_keys(path, kv, as_export):
    """Ghi/đè 3 key vào file (xoá dòng cũ cùng key rồi thêm mới). KHÔNG in giá trị. as_export=True → 'export K=\"V\"'."""
    path = os.path.expanduser(path)
    keys = set(kv)
    lines = []
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8").read().splitlines():
            s = ln.strip()
            s = s[len("export "):] if s.startswith("export ") else s
            k = s.split("=", 1)[0].strip() if "=" in s else ""
            if k in keys:
                continue   # bỏ dòng cũ của key này
            lines.append(ln)
    while lines and lines[-1].strip() == "":
        lines.pop()
    lines.append("")
    lines.append("# Gmail API fallback (gửi mail khi SMTP bị chặn) — Kora /claude-knowledge-connect")
    for k, v in kv.items():
        lines.append(f'export {k}="{v}"' if as_export else f'{k}={v}')
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(description="Lấy Gmail OAuth refresh token (1 lần).")
    ap.add_argument("--client-id", default=os.getenv("GMAIL_OAUTH_CLIENT_ID"))
    ap.add_argument("--client-secret", default=os.getenv("GMAIL_OAUTH_CLIENT_SECRET"))
    ap.add_argument("--proxy", default=os.getenv("HTTPS_PROXY") or os.getenv("https_proxy"),
                    help="Proxy HTTPS (mặc định đọc HTTPS_PROXY).")
    ap.add_argument("--write-zshrc", action="store_true",
                    help="GHI THẲNG 3 key vào ~/.zshrc (KHÔNG in token ra màn hình) — an toàn khi chạy qua run_command.")
    ap.add_argument("--write-env", dest="write_env",
                    help="GHI THẲNG 3 key vào file .env.local chỉ định (KEY=VALUE, không 'export') — cho lịch nền.")
    args = ap.parse_args()
    if not args.client_id or not args.client_secret:
        sys.exit("❌ Thiếu --client-id/--client-secret (hoặc export GMAIL_OAUTH_CLIENT_ID/SECRET).")

    server = HTTPServer(("127.0.0.1", 0), _OAuthHandler)
    server.auth_code = server.state_recv = server.auth_error = None
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}/"
    state = secrets.token_urlsafe(24)
    consent = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": args.client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": gmail_api.GMAIL_SEND_SCOPE, "access_type": "offline", "prompt": "consent",
        "state": state,
    })
    print("→ Mở trình duyệt để uỷ quyền (nếu không tự mở, copy URL dưới vào trình duyệt):\n")
    print(consent + "\n")
    try:
        import webbrowser
        webbrowser.open(consent)
    except Exception:  # noqa: BLE001
        pass

    print(f"⏳ Đang chờ uỷ quyền tại {redirect_uri} …")
    server.handle_request()   # xử lý đúng 1 request rồi dừng
    if server.auth_error:
        sys.exit(f"❌ Google trả lỗi: {server.auth_error}")
    if not server.auth_code:
        sys.exit("❌ Không nhận được mã uỷ quyền.")
    if server.state_recv != state:
        sys.exit("❌ State không khớp (nghi giả mạo) — huỷ.")

    tok = _exchange_code(server.auth_code, args.client_id, args.client_secret, redirect_uri, args.proxy)
    refresh = tok.get("refresh_token")
    if not refresh:
        sys.exit("❌ Không có refresh_token (thường do app chưa 'prompt=consent' hoặc đã cấp trước). "
                 "Gỡ quyền tại myaccount.google.com/permissions rồi chạy lại.")

    kv = {
        "GMAIL_OAUTH_CLIENT_ID": args.client_id,
        "GMAIL_OAUTH_CLIENT_SECRET": args.client_secret,
        "GMAIL_OAUTH_REFRESH_TOKEN": refresh,
    }
    # GHI THẲNG (an toàn cho run_command — KHÔNG in token ra chat)
    if args.write_zshrc:
        rc = os.path.expanduser("~/.zshrc")
        _upsert_keys(rc, kv, as_export=True)
        print(f"\n✅ THÀNH CÔNG — đã ghi 3 key Gmail API vào {rc} (token KHÔNG in ra màn hình).")
        print("   → Chạy `source ~/.zshrc` (hoặc mở shell mới). Kiểm tra:")
        print("     python3 tools/report-mailer/send_report.py --check --transport https")
        return
    if args.write_env:
        _upsert_keys(args.write_env, kv, as_export=False)
        print(f"\n✅ THÀNH CÔNG — đã ghi 3 key Gmail API vào {args.write_env} (KEY=VALUE, token KHÔNG in). Dùng cho lịch nền.")
        print("   Kiểm tra: python3 tools/report-mailer/send_report.py --check --transport https --env " + args.write_env)
        return
    # Chế độ MẶC ĐỊNH (chạy tay ở Terminal): in để user tự dán
    print("\n✅ THÀNH CÔNG. DÁN 3 dòng sau vào ~/.zshrc (rồi `source ~/.zshrc`) "
          "HOẶC vào tools/report-mailer/.env.local (bỏ chữ 'export'):\n")
    print(f'export GMAIL_OAUTH_CLIENT_ID="{args.client_id}"')
    print(f'export GMAIL_OAUTH_CLIENT_SECRET="{args.client_secret}"')
    print(f'export GMAIL_OAUTH_REFRESH_TOKEN="{refresh}"')
    print("\n(Tuỳ chọn) export GMAIL_API_USER=\"me\"   # hoặc địa chỉ Gmail nếu dùng alias")
    print("Kiểm tra: python3 tools/report-mailer/send_report.py --check --transport https")


if __name__ == "__main__":
    main()
