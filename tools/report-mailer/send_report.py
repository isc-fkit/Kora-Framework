#!/usr/bin/env python3
"""
send_report.py — Gửi báo cáo tiến độ Kora qua email bằng SMTP (full-auto).

Bí mật (mật khẩu / App Password) đọc từ tools/report-mailer/.env.local (đã gitignore
qua **/.env.local). KHÔNG in mật khẩu ra log. Chỉ dùng thư viện chuẩn Python.

Ví dụ:
  # Gửi thử (email test nhỏ, không cần report) tới chính mình:
  python3 tools/report-mailer/send_report.py --test

  # Gửi thử tới 1 địa chỉ cụ thể:
  python3 tools/report-mailer/send_report.py --test --to you@example.com

  # Gửi báo cáo thật (nhúng + đính kèm dashboard HTML):
  python3 tools/report-mailer/send_report.py \
      --to "a@x.com,b@y.com" \
      --subject "[Kora] Báo cáo tiến độ 2026-06-18" \
      --html-file reports/progress-report-latest.html
"""
import argparse
import mimetypes
import os
import re
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Tên người gửi hiển thị mặc định — CẤU HÌNH được qua MAIL_FROM_NAME trong .env.local.
DEFAULT_FROM_NAME = "Kora AI Daily Report"


def load_env(path: Path) -> dict:
    """Đọc .env.local dạng KEY=VALUE (bỏ dòng trống / dòng bắt đầu bằng #)."""
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def resolve_env_path(cli_env=None) -> Path:
    """Tìm file .env.local theo THỨ TỰ ưu tiên (deterministic, không đoán cwd):
    1) --env <path>  2) biến môi trường KORA_MAILER_ENV  3) .env.local CẠNH script (HERE).
    Skill/orchestrator truyền KORA_MAILER_ENV trỏ tới file thật trong project → bản CÀI (script ở
    ~/.claude/kora-framework/...) vẫn đọc đúng file user điền."""
    for cand in (cli_env, os.getenv("KORA_MAILER_ENV")):
        if cand and cand.strip():
            return Path(cand.strip()).expanduser()
    return HERE / ".env.local"


def die(msg: str, code: int = 1):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def split_addrs(raw: str):
    return [x.strip() for x in (raw or "").split(",") if x.strip()]


def main():
    ap = argparse.ArgumentParser(description="Gửi báo cáo Kora qua SMTP.")
    ap.add_argument("--to", help="Danh sách email nhận, phân tách bằng dấu phẩy.")
    ap.add_argument("--cc", default="", help="CC, phân tách bằng dấu phẩy.")
    ap.add_argument("--bcc", default="", help="BCC, phân tách bằng dấu phẩy.")
    ap.add_argument("--subject", default="", help="Tiêu đề email.")
    ap.add_argument("--html-file", help="File HTML để nhúng (và đính kèm).")
    ap.add_argument("--body", default="", help="Nội dung text thuần (fallback).")
    ap.add_argument("--attach", action="append", default=[], help="File đính kèm thêm (lặp lại được).")
    ap.add_argument("--no-attach-html", action="store_true", help="Chỉ nhúng HTML, không đính kèm file.")
    ap.add_argument("--banner", help="Ảnh banner nhúng inline (cid:kora-banner). Mặc định assets/banner-daily-report.png.")
    ap.add_argument("--test", action="store_true", help="Gửi email test nhỏ (không cần report).")
    ap.add_argument("--check", action="store_true", help="Chỉ kiểm tra cấu hình + đăng nhập SMTP (KHÔNG gửi).")
    ap.add_argument("--env", help="Đường dẫn .env.local (ưu tiên cao nhất; mặc định đọc KORA_MAILER_ENV rồi .env.local cạnh script).")
    args = ap.parse_args()

    env_path = resolve_env_path(args.env)
    env = load_env(env_path)
    file_exists = env_path.exists()

    def cfg(key, default=None):
        return os.getenv(key) or env.get(key) or default

    host = cfg("SMTP_HOST", "smtp.gmail.com")
    port = int(cfg("SMTP_PORT", "587"))
    security = (cfg("SMTP_SECURITY", "starttls") or "starttls").lower()
    user = cfg("SMTP_USER")
    raw_pw = cfg("SMTP_PASS")
    placeholder = bool(raw_pw and raw_pw.strip().startswith("PASTE_"))
    pw = None if placeholder else raw_pw   # placeholder chưa thay → coi như chưa cấu hình
    mail_from = cfg("MAIL_FROM") or user
    from_name = cfg("MAIL_FROM_NAME") or DEFAULT_FROM_NAME   # tên hiển thị → "Tên <email>"

    def _missing_msg():
        if not file_exists:
            return (f"Không thấy file cấu hình mail: {env_path}\n"
                    f"   → Tạo file đó (copy từ .env.local.example) rồi điền SMTP_USER/SMTP_PASS, HOẶC trỏ "
                    f"biến KORA_MAILER_ENV / cờ --env tới đúng .env.local của bạn.")
        if placeholder:
            return (f"SMTP_PASS vẫn là placeholder 'PASTE_…' trong {env_path} — dán App Password (16 ký tự) THẬT vào.")
        return (f"Thiếu SMTP_USER/SMTP_PASS trong {env_path} (tạo Google App Password rồi điền). "
                f"Script đọc TRỰC TIẾP file này — KHÔNG cần 'source'.")

    if args.check:
        print(f"ℹ️  Đọc cấu hình mail từ: {env_path}")
        if not user or not pw:
            die(_missing_msg())
        try:
            if security == "ssl":
                with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as s:
                    s.login(user, pw)
            else:
                with smtplib.SMTP(host, port, timeout=30) as s:
                    s.ehlo()
                    s.starttls(context=ssl.create_default_context())
                    s.ehlo()
                    s.login(user, pw)
        except smtplib.SMTPAuthenticationError:
            die("Đăng nhập SMTP THẤT BẠI — App Password sai hoặc không thuộc SMTP_USER. Sửa lại .env.local.")
        except Exception as e:  # noqa: BLE001
            die(f"Không kết nối được SMTP: {e}")
        print(f"✅ Cấu hình gửi mail OK — đăng nhập thành công: {user} @ {host}:{port} · "
              f"gửi dạng \"{from_name} <{mail_from}>\"")
        return

    if not user or not pw:
        die(_missing_msg())

    to = split_addrs(args.to)
    cc = split_addrs(args.cc)
    bcc = split_addrs(args.bcc)
    if not to:
        if args.test and mail_from:
            to = [mail_from]   # test: mặc định gửi cho chính mình
        else:
            die("Thiếu --to (danh sách email nhận).")

    subject = args.subject
    text = args.body
    html = None
    attachments = list(args.attach)

    if args.test:
        subject = subject or "[Kora] Test gửi báo cáo (SMTP)"
        text = text or (
            "Đây là email TEST từ Kora qua SMTP.\n"
            "Nếu bạn nhận được email này, cấu hình gửi mail đã hoạt động.\n— Kora"
        )
        html = (
            '<div style="font-family:Arial,Helvetica,sans-serif;line-height:1.55;color:#222">'
            '<h2 style="color:#0b804b;margin:0 0 8px">✅ Kora — Test SMTP thành công</h2>'
            '<p>Nếu bạn nhận được email này, cấu hình gửi báo cáo qua SMTP đã hoạt động.</p>'
            '<p>Báo cáo thật sẽ gồm dashboard (sprint, assignee, % hoàn thành) và phân tích AI.</p>'
            '<p style="color:#888;font-size:12px">— Tự động gửi bởi Kora.</p></div>'
        )
    else:
        if args.html_file:
            p = Path(args.html_file)
            if not p.exists():
                die(f"Không thấy file HTML: {p}")
            html = p.read_text(encoding="utf-8")
            if not args.no_attach_html:
                attachments.append(str(p))
        subject = subject or "[Kora] Báo cáo tiến độ"
        text = text or "Báo cáo tiến độ Kora — xem nội dung email (HTML) hoặc file đính kèm."

    # Banner header NHÚNG INLINE (cid:kora-banner) → hiện NGAY cả khi client chặn ảnh remote (Outlook "trust sender").
    # Resolve path bền (như KORA_MAILER_ENV): --banner → KORA_BANNER → cạnh CORE (assets) → cwd/assets.
    banner_cid_path = None
    if html and not args.test:
        cands = [args.banner, os.getenv("KORA_BANNER"),
                 str(HERE.parents[1] / "assets" / "banner-daily-report.png"),
                 str(Path.cwd() / "assets" / "banner-daily-report.png")]
        bpth = next((Path(c).expanduser() for c in cands if c and Path(c).expanduser().exists()), None)
        has_banner = bool(re.search(r"banner-daily-report\.(?:png|jpe?g)", html))
        if bpth and has_banner:
            html = re.sub(r'src="[^"]*banner-daily-report\.(?:png|jpe?g)[^"]*"', 'src="cid:kora-banner"', html)
            banner_cid_path = bpth
            print(f"ℹ️  Banner: nhúng CID inline ← {bpth} ({bpth.stat().st_size // 1024}KB)")
        elif has_banner:
            print("⚠️  Banner: KHÔNG thấy file ảnh local → email giữ link REMOTE (Outlook có thể chặn 'trust sender'). "
                  "Truyền --banner <path> hoặc đặt KORA_BANNER trỏ tới assets/banner-daily-report.png.", file=sys.stderr)

    msg = EmailMessage()
    msg["From"] = formataddr((from_name, mail_from))
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg.set_content(text or "")
    if html:
        msg.add_alternative(html, subtype="html")
        if banner_cid_path:
            ctype, _ = mimetypes.guess_type(str(banner_cid_path))
            mt, st = (ctype.split("/", 1) if ctype else ("image", "png"))
            msg.get_payload()[-1].add_related(banner_cid_path.read_bytes(),
                                              maintype=mt, subtype=st, cid="kora-banner")

    for fp in attachments:
        p = Path(fp)
        if not p.exists():
            print(f"⚠️  Bỏ qua đính kèm (không thấy): {p}", file=sys.stderr)
            continue
        ctype, _ = mimetypes.guess_type(str(p))
        maintype, subtype = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
        msg.add_attachment(p.read_bytes(), maintype=maintype, subtype=subtype, filename=p.name)

    all_rcpt = to + cc + bcc
    try:
        if security == "ssl":
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as s:
                s.login(user, pw)
                s.send_message(msg, from_addr=mail_from, to_addrs=all_rcpt)
        else:  # starttls (mặc định, cổng 587)
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                s.login(user, pw)
                s.send_message(msg, from_addr=mail_from, to_addrs=all_rcpt)
    except smtplib.SMTPAuthenticationError:
        die("Xác thực SMTP thất bại. Gmail: phải dùng App Password (bật 2FA rồi tạo tại "
            "https://myaccount.google.com/apppasswords), KHÔNG dùng mật khẩu Gmail thường.")
    except Exception as e:  # noqa: BLE001 — báo gọn cho user non-tech
        die(f"Gửi mail lỗi: {e}")

    print(f"✅ Đã gửi tới: {', '.join(all_rcpt)} | host={host}:{port} | from={mail_from}")


if __name__ == "__main__":
    main()
