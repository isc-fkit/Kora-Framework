#!/usr/bin/env python3
"""
send_report.py — Gửi báo cáo tiến độ Kora qua email bằng SMTP (full-auto).

Bí mật (mật khẩu / App Password) đọc theo thứ tự: ENV trước (vd `export SMTP_USER/SMTP_PASS`
trong ~/.zshrc — gom token 1 chỗ, run_command source được) → rồi file tools/report-mailer/.env.local
(gitignore). KHÔNG in mật khẩu ra log. Chỉ dùng thư viện chuẩn Python.

Ví dụ:
  # Gửi thử (email test nhỏ, không cần report) tới chính mình:
  python3 tools/report-mailer/send_report.py --test

  # Gửi thử tới 1 địa chỉ cụ thể:
  python3 tools/report-mailer/send_report.py --test --to you@example.com

  # Gửi báo cáo thật (nhúng + đính kèm dashboard HTML):
  python3 tools/report-mailer/send_report.py \
      --to "a@x.com,b@y.com" \
      --subject "Báo cáo tiến độ 2026-06-18" \
      --html-file reports/progress-report-latest.html
"""
import argparse
import mimetypes
import os
import re
import shlex
import smtplib
import ssl
import sys
import time
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Transport FALLBACK qua Gmail API/HTTPS (cùng thư mục) — dùng khi mạng chặn SMTP.
sys.path.insert(0, str(HERE))
import gmail_api  # noqa: E402

# Tên người gửi hiển thị mặc định — CẤU HÌNH được qua MAIL_FROM_NAME trong .env.local.
DEFAULT_FROM_NAME = "Báo cáo tiến độ"


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


def _emit_command(args, env_path) -> str:
    """Sinh 1 DÒNG LỆNH terminal để gửi tiếp (bàn giao khi Cowork chặn SMTP). Path → TUYỆT ĐỐI để chạy từ
    cwd bất kỳ; secret KHÔNG in (vẫn ở .env.local). Tái dựng từ chính args đã truyền."""
    def absify(p):
        return str(Path(p).expanduser().resolve()) if p else p
    parts = [f"KORA_MAILER_ENV={shlex.quote(str(Path(env_path).resolve()))}",
             "python3", shlex.quote(str(Path(__file__).resolve()))]
    if args.to:
        parts += ["--to", shlex.quote(args.to)]
    if args.cc:
        parts += ["--cc", shlex.quote(args.cc)]
    if args.bcc:
        parts += ["--bcc", shlex.quote(args.bcc)]
    if args.subject:
        parts += ["--subject", shlex.quote(args.subject)]
    if args.html_file:
        parts += ["--html-file", shlex.quote(absify(args.html_file))]
    if args.no_attach_html:
        parts += ["--no-attach-html"]
    for a in (args.attach or []):
        parts += ["--attach", shlex.quote(absify(a))]
    if args.banner:
        parts += ["--banner", shlex.quote(absify(args.banner))]
    if args.split:
        parts += ["--split"]
    if args.stale_after_min != 30:
        parts += ["--stale-after-min", str(args.stale_after_min)]
    if getattr(args, "transport", "auto") != "auto":
        parts += ["--transport", args.transport]
    return " ".join(parts)


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
    ap.add_argument("--split", action="store_true",
                    help="Gửi RIÊNG từng người nhận (mỗi mail To = 1 người, không thấy nhau). "
                         "Mặc định: 1 mail nhiều địa chỉ.")
    ap.add_argument("--stale-after-min", dest="stale_after_min", type=int, default=30,
                    help="Chặn gửi báo cáo CŨ: nếu --html-file cũ hơn N phút → DỪNG (báo build lại). "
                         "0 = tắt kiểm tra. Mặc định 30.")
    ap.add_argument("--allow-empty-ai", dest="allow_empty_ai", action="store_true",
                    help="Bỏ qua guard chặn gửi khi khối AI còn placeholder (mặc định CHẶN — buộc chèn phân tích AI thật trước).")
    ap.add_argument("--banner", help="Ảnh banner nhúng inline (cid:kora-banner). Mặc định assets/banner-daily-report.jpg.")
    ap.add_argument("--test", action="store_true", help="Gửi email test nhỏ (không cần report).")
    ap.add_argument("--check", action="store_true", help="Chỉ kiểm tra cấu hình + đăng nhập SMTP (KHÔNG gửi).")
    ap.add_argument("--env", help="Đường dẫn .env.local (ưu tiên cao nhất; mặc định đọc KORA_MAILER_ENV rồi .env.local cạnh script).")
    ap.add_argument("--emit-command", action="store_true",
                    help="KHÔNG gửi — in 1 DÒNG LỆNH (path tuyệt đối) để chạy ở TERMINAL gửi tiếp (bàn giao khi "
                         "Cowork sandbox chặn SMTP). Secret KHÔNG in (vẫn ở .env.local).")
    ap.add_argument("--transport", choices=["auto", "smtp", "https"], default="auto",
                    help="auto (SMTP → fallback Gmail API/HTTPS khi mạng chặn) | smtp (chỉ SMTP) | "
                         "https (ép Gmail API/HTTPS). Mặc định auto.")
    args = ap.parse_args()

    env_path = resolve_env_path(args.env)
    env = load_env(env_path)
    file_exists = env_path.exists()

    if args.emit_command:   # BÀN GIAO: in lệnh chạy ở terminal (không gửi, không cần creds)
        print(_emit_command(args, env_path))
        return

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

    # ── Fallback Gmail API/HTTPS (mạng chặn SMTP) ── (đọc cùng cơ chế cfg: ENV → .env.local)
    gmail_client_id = cfg("GMAIL_OAUTH_CLIENT_ID")
    gmail_client_secret = cfg("GMAIL_OAUTH_CLIENT_SECRET")
    gmail_refresh_token = cfg("GMAIL_OAUTH_REFRESH_TOKEN")
    gmail_api_user = cfg("GMAIL_API_USER", "me")
    gmail_creds_ok = bool(gmail_client_id and gmail_client_secret and gmail_refresh_token)
    # proxy công ty cho CONNECT 443. KORA_HTTPS_PROXY = proxy RIÊNG cho Kora mailer (để user dùng proxy-toggle
    # mà KHÔNG cần bật HTTPS_PROXY hệ thống cho cả shell). Ưu tiên: HTTPS_PROXY > https_proxy > KORA_HTTPS_PROXY.
    https_proxy = cfg("HTTPS_PROXY") or cfg("https_proxy") or cfg("KORA_HTTPS_PROXY")
    try:
        smtp_timeout = int(cfg("SMTP_TIMEOUT", "15"))         # ngắn để fallback nhanh; override được
    except ValueError:
        smtp_timeout = 15

    def _missing_msg():
        if placeholder:
            return ("SMTP_PASS vẫn là placeholder 'PASTE_…' — dán App Password (16 ký tự) THẬT vào "
                    f"(export trong ~/.zshrc HOẶC file {env_path}).")
        # Creds đọc theo thứ tự: ENV (export ~/.zshrc — run_command source được) → file .env.local.
        return ("Thiếu SMTP_USER/SMTP_PASS. Đặt Gmail App Password ở 1 trong 2 chỗ:\n"
                "   • ~/.zshrc (KHUYẾN NGHỊ, gom token 1 chỗ):  export SMTP_USER=tk@gmail.com  export SMTP_PASS=<AppPassword>\n"
                f"   • hoặc file {env_path} (copy từ .env.local.example){'' if file_exists else ' — CHƯA tồn tại'}.\n"
                "   (Tạo Google App Password: bật 2FA → myaccount.google.com/apppasswords. Script đọc ENV trước rồi file, KHÔNG cần 'source'.)")

    if args.check:
        proxy_disp = https_proxy or "(không)"
        # 1) SMTP (bỏ qua nếu --transport https)
        if args.transport != "https":
            _src = "ENV (~/.zshrc)" if (os.getenv("SMTP_USER") or os.getenv("SMTP_PASS")) else (f"file {env_path}" if file_exists else "(chưa thấy)")
            print(f"ℹ️  Nguồn creds SMTP: {_src}  ·  user={user or '(thiếu)'}")
            if not user or not pw:
                die(_missing_msg())
            try:
                if security == "ssl":
                    with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=smtp_timeout) as s:
                        s.login(user, pw)
                else:
                    with smtplib.SMTP(host, port, timeout=smtp_timeout) as s:
                        s.ehlo()
                        s.starttls(context=ssl.create_default_context())
                        s.ehlo()
                        s.login(user, pw)
            except smtplib.SMTPAuthenticationError:
                die("Đăng nhập SMTP THẤT BẠI — App Password sai hoặc không thuộc SMTP_USER. Sửa lại .env.local.")
            except Exception as e:  # noqa: BLE001
                if args.transport == "smtp" or not gmail_creds_ok:
                    die(f"Không kết nối được SMTP: {e}")
                print(f"⚠️  SMTP không tới được ({e}) — nhưng có creds Gmail API/HTTPS để fallback. Kiểm tra tiếp…", file=sys.stderr)
            else:
                print(f"✅ Cấu hình gửi mail OK — đăng nhập SMTP thành công: {user} @ {host}:{port} · "
                      f"gửi dạng \"{from_name} <{mail_from}>\"")
        # 2) Gmail API/HTTPS (bỏ qua nếu --transport smtp)
        if args.transport == "https" and not gmail_creds_ok:
            die("Thiếu creds Gmail API (GMAIL_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN). "
                "Chạy: python3 tools/report-mailer/gmail_oauth_setup.py")
        if args.transport != "smtp" and gmail_creds_ok:
            try:
                gmail_api.refresh_access_token(gmail_client_id, gmail_client_secret,
                                               gmail_refresh_token, proxy=https_proxy, timeout=30)
            except gmail_api.GmailAuthError as e:
                print("GMAIL_API_AUTH_FAILED", file=sys.stderr)
                die(f"Creds Gmail API sai/hết hạn: {e}\n   → Chạy lại gmail_oauth_setup.py.")
            except gmail_api.GmailUnreachableError as e:
                print("GMAIL_API_UNREACHABLE", file=sys.stderr)
                die(f"Không tới được Gmail API (proxy={proxy_disp}): {e}")
            print(f"✅ Gmail API creds OK (token refresh thành công · proxy={proxy_disp})")
        elif args.transport != "smtp" and not gmail_creds_ok:
            print("ℹ️  Chưa cấu hình Gmail API fallback (GMAIL_OAUTH_*). "
                  "Bật: python3 tools/report-mailer/gmail_oauth_setup.py", file=sys.stderr)
        return

    smtp_possible = bool(user and pw)
    if not smtp_possible:
        # Thiếu SMTP creds: vẫn OK nếu ép https hoặc auto-có-creds-Gmail (sẽ gửi qua Gmail API).
        if not (args.transport == "https" or (args.transport == "auto" and gmail_creds_ok)):
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
        subject = subject or "Test gửi báo cáo (SMTP)"
        text = text or (
            "Đây là email TEST qua SMTP.\n"
            "Nếu bạn nhận được email này, cấu hình gửi mail đã hoạt động."
        )
        html = (
            '<div style="font-family:Arial,Helvetica,sans-serif;line-height:1.55;color:#222">'
            '<h2 style="color:#0b804b;margin:0 0 8px">✅ Test SMTP thành công</h2>'
            '<p>Nếu bạn nhận được email này, cấu hình gửi báo cáo qua SMTP đã hoạt động.</p>'
            '<p>Báo cáo thật sẽ gồm dashboard (sprint, assignee, % hoàn thành) và phân tích AI.</p>'
            '<p style="color:#888;font-size:12px">— Tự động gửi.</p></div>'
        )
    else:
        if args.html_file:
            p = Path(args.html_file)
            if not p.exists():
                die(f"Không thấy file HTML: {p}")
            # GUARD chống gửi báo cáo CŨ: file report phải vừa được build_report tạo (mtime mới).
            # Lý do: report dùng tên cố định (-latest); nếu schedule/sendmail KHÔNG build lại, ta sẽ
            # lặng lẽ gửi bản cũ. Chặn tại đây để bắt buộc tạo mới trước khi gửi.
            if args.stale_after_min and args.stale_after_min > 0:
                age_min = (time.time() - os.path.getmtime(p)) / 60.0
                if age_min > args.stale_after_min:
                    die(f"Báo cáo CŨ ({age_min:.0f} phút > {args.stale_after_min}'): {p.name} chưa được tạo mới. "
                        f"Hãy chạy build_report.py NGAY TRƯỚC khi gửi (lịch nền/gửi-ngay phải build lại). "
                        f"Bỏ kiểm tra: --stale-after-min 0.")
            html = p.read_text(encoding="utf-8")
            # GUARD AI: KHÔNG gửi khi khối phân tích AI còn PLACEHOLDER (chưa chạy build_report --inject-ai).
            # Bảo đảm mail LUÔN có phân tích AI thật. Bỏ kiểm tra: --allow-empty-ai.
            if not getattr(args, "allow_empty_ai", False):
                mm = re.search(r"<!--KR-AI-START-->(.*?)<!--KR-AI-END-->", html, re.DOTALL)
                if mm:
                    inner = re.sub(r"<[^>]+>", "", mm.group(1)).strip()
                    if (not inner) or ("Claude điền" in inner) or ("Claude điền" in mm.group(1)):
                        die("❌ Khối phân tích AI trong email còn PLACEHOLDER (chưa chèn phân tích thật).\n"
                            "   → Viết reports/ai-analysis-latest.md rồi chạy: build_report.py --inject-ai reports/ai-analysis-latest.md\n"
                            "   (workflow 14 Bước 1.5). KHÔNG gửi mail thiếu phân tích AI. Bỏ qua: --allow-empty-ai.")
            if not args.no_attach_html:
                attachments.append(str(p))
        subject = subject or "Báo cáo tiến độ"
        text = text or "Báo cáo tiến độ — xem nội dung email (HTML) hoặc file đính kèm."

    # Banner header NHÚNG INLINE (cid:kora-banner) → hiện NGAY cả khi client chặn ảnh remote (Outlook "trust sender").
    # Resolve path bền (như KORA_MAILER_ENV): --banner → KORA_BANNER → cạnh CORE (assets) → cwd/assets.
    banner_cid_path = None
    if html and not args.test:
        # Ưu tiên JPEG (nhẹ ~117KB) → fallback PNG (bản cũ). Path bền: --banner → KORA_BANNER → cạnh CORE → cwd.
        cands = [args.banner, os.getenv("KORA_BANNER")]
        # Path bền dù gọi từ ĐÂU: cạnh script (CORE đã cài / repo dev) → CORE chuẩn ~/.claude/kora-framework → cwd.
        for base in (HERE.parents[1] / "assets",
                     Path.home() / ".claude" / "kora-framework" / "assets",
                     Path.cwd() / "assets"):
            cands += [str(base / "banner-daily-report.jpg"), str(base / "banner-daily-report.png")]
        bpth = next((Path(c).expanduser() for c in cands if c and Path(c).expanduser().exists()), None)
        has_banner = bool(re.search(r"banner-daily-report\.(?:png|jpe?g)", html))
        if bpth and has_banner:
            html = re.sub(r'src="[^"]*banner-daily-report\.(?:png|jpe?g)[^"]*"', 'src="cid:kora-banner"', html)
            banner_cid_path = bpth
            print(f"ℹ️  Banner: nhúng CID inline ← {bpth} ({bpth.stat().st_size // 1024}KB)")
        elif has_banner:
            print("⚠️  Banner: KHÔNG thấy file ảnh local → email giữ link REMOTE (Outlook có thể chặn 'trust sender'). "
                  "Truyền --banner <path> hoặc đặt KORA_BANNER trỏ tới assets/banner-daily-report.jpg.", file=sys.stderr)

    # Tên đính kèm KHÁC NHAU mỗi lần: report HTML cố định (progress-report-latest / email-body-latest /
    # processing_report…) được đổi sang tên có NGÀY-GIỜ → client mail không lấy lại bản cũ cùng tên.
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    def _attach_name(name):
        if re.search(r"(progress[-_]?report|processing[-_]?report)", name, re.I) and name.lower().endswith((".html", ".htm")):
            return f"progress-report-{stamp}.html"
        if re.search(r"email[-_]?body", name, re.I) and name.lower().endswith((".html", ".htm")):
            return f"email-body-{stamp}.html"
        return name

    # Lọc đính kèm hợp lệ + dedup tên TRƯỚC → quyết định có cần bọc multipart/mixed hay không.
    valid_atts, seen_names = [], set()
    for fp in attachments:
        p = Path(fp)
        if not p.exists():
            print(f"⚠️  Bỏ qua đính kèm (không thấy): {p}", file=sys.stderr)
            continue
        fname = _attach_name(p.name)
        if fname in seen_names:  # tránh 2 đính kèm trùng tên trong cùng mail
            continue
        seen_names.add(fname)
        valid_atts.append((p, fname))

    # ── Dựng BODY. Khi CÓ banner CID + ĐÍNH KÈM: phải để multipart/related NGAY DƯỚI multipart/mixed
    #    (sibling của file đính kèm). Nếu related bị CHÔN dưới alternative+mixed (cách add_related cũ) →
    #    Outlook (nhất là Outlook FPT/Exchange) KHÔNG resolve được `cid:` → coi banner là ảnh NGOÀI →
    #    "Download pictures" + vỡ ảnh. Cấu trúc đích: mixed[ related[ alternative[text,html], image(cid) ], đính-kèm… ].
    def _alt_part():
        a = MIMEMultipart("alternative")
        a.attach(MIMEText(text or "", "plain", "utf-8"))
        if html:
            a.attach(MIMEText(html, "html", "utf-8"))
        return a

    if html and banner_cid_path:
        ctype, _ = mimetypes.guess_type(str(banner_cid_path))
        _mt, st = (ctype.split("/", 1) if ctype else ("image", "jpeg"))
        body = MIMEMultipart("related")
        body.attach(_alt_part())
        img = MIMEImage(banner_cid_path.read_bytes(), _subtype=st)
        img.add_header("Content-ID", "<kora-banner>")              # RFC 2392: src="cid:kora-banner" ↔ <kora-banner>
        img.add_header("Content-Disposition", "inline",
                       filename="banner" + (banner_cid_path.suffix or ".jpg"))
        img.add_header("X-Attachment-Id", "kora-banner")
        body.attach(img)
    elif html:
        body = _alt_part()
    else:
        body = MIMEText(text or "", "plain", "utf-8")

    # CÓ đính kèm → bọc multipart/mixed (body làm phần đầu, related KHÔNG bị chôn). KHÔNG có → body là message.
    if valid_atts:
        msg = MIMEMultipart("mixed")
        msg.attach(body)
        for p, fname in valid_atts:
            ctype, _ = mimetypes.guess_type(str(p))
            maintype, subtype = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
            part = MIMEBase(maintype, subtype)
            part.set_payload(p.read_bytes())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=fname)
            msg.attach(part)
    else:
        msg = body

    msg["From"] = formataddr((from_name, mail_from))
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject

    all_rcpt = to + cc + bcc

    def _deliver(s):
        """Gửi qua kết nối SMTP đã login. Trả (sent, failed). --split → mỗi người 1 mail riêng
        (tái dùng kết nối, 1 người lỗi KHÔNG làm hỏng cả lượt)."""
        if not args.split:
            s.send_message(msg, from_addr=mail_from, to_addrs=all_rcpt)
            return list(all_rcpt), []
        sent, failed = [], []
        if "Cc" in msg:
            del msg["Cc"]   # split → mỗi mail chỉ 1 người, bỏ Cc
        for addr in all_rcpt:
            del msg["To"]
            msg["To"] = addr
            try:
                s.send_message(msg, from_addr=mail_from, to_addrs=[addr])
                sent.append(addr)
            except Exception as e:  # noqa: BLE001 — 1 người lỗi vẫn gửi tiếp người khác
                failed.append((addr, str(e)))
        return sent, failed

    def send_via_smtp():
        """Mở SMTP, login, gửi. RAISE lỗi (không die) để controller quyết fallback."""
        if security == "ssl":
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=smtp_timeout) as s:
                s.login(user, pw)
                return _deliver(s)
        with smtplib.SMTP(host, port, timeout=smtp_timeout) as s:   # starttls (mặc định, cổng 587)
            s.ehlo()
            s.starttls(context=ssl.create_default_context())
            s.ehlo()
            s.login(user, pw)
            return _deliver(s)

    def send_via_gmail_api():
        """Gửi qua Gmail API/HTTPS (định tuyến qua proxy). Dùng CHUNG object msg (không dựng lại MIME)."""
        token = gmail_api.refresh_access_token(gmail_client_id, gmail_client_secret,
                                               gmail_refresh_token, proxy=https_proxy, timeout=30)
        approx = len(msg.as_bytes()) * 4 // 3   # base64url ~ +33%
        if approx > 25 * 1024 * 1024:
            print(f"⚠️  Email ~{approx // (1024 * 1024)}MB — gần giới hạn Gmail API (~35MB).", file=sys.stderr)
        if not args.split:
            if bcc and "Bcc" not in msg:
                msg["Bcc"] = ", ".join(bcc)   # API lấy người nhận từ HEADER (Gmail tự gỡ Bcc khi gửi)
            gmail_api.send_message(msg, token, api_user=gmail_api_user, proxy=https_proxy)
            return list(all_rcpt), []
        for h in ("Cc", "Bcc"):
            if h in msg:
                del msg[h]
        sent_, failed_ = [], []
        for addr in all_rcpt:
            del msg["To"]
            msg["To"] = addr
            try:
                gmail_api.send_message(msg, token, api_user=gmail_api_user, proxy=https_proxy)
                sent_.append(addr)
            except Exception as e:  # noqa: BLE001 — 1 người lỗi vẫn gửi tiếp
                failed_.append((addr, str(e)))
        return sent_, failed_

    def _gmail_fallback(prefix):
        try:
            return send_via_gmail_api()
        except gmail_api.GmailAuthError as e:
            print("GMAIL_API_AUTH_FAILED", file=sys.stderr)
            die(f"{prefix}Gmail API auth lỗi (creds sai/hết hạn): {e}\n   → Chạy lại gmail_oauth_setup.py.")
        except gmail_api.GmailUnreachableError as e:
            print("GMAIL_API_UNREACHABLE", file=sys.stderr)
            die(f"{prefix}Gmail API không tới được (proxy={https_proxy or '(không)'}): {e}")

    transport_used = "smtp"
    if args.transport == "https" or not smtp_possible:
        # Ép HTTPS, hoặc auto nhưng thiếu SMTP creds → đi thẳng Gmail API.
        sent, failed = _gmail_fallback("")
        transport_used = "https"
    else:
        try:
            sent, failed = send_via_smtp()
        except smtplib.SMTPAuthenticationError:
            print("SMTP_AUTH_FAILED", file=sys.stderr)   # marker: sai App Password → KHÔNG fallback (lỗi creds, không phải mạng)
            die("Xác thực SMTP thất bại. Gmail: phải dùng App Password (bật 2FA rồi tạo tại "
                "https://myaccount.google.com/apppasswords), KHÔNG dùng mật khẩu Gmail thường.")
        except (OSError, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError) as e:
            print("SMTP_UNREACHABLE", file=sys.stderr)   # marker: mạng/sandbox chặn
            if args.transport == "smtp" or not gmail_creds_ok:
                die(f"Không kết nối được SMTP (mạng/sandbox Cowork chặn?): {e}")
            print("ℹ️  SMTP bị chặn → thử lại qua Gmail API/HTTPS (443, qua proxy)…", file=sys.stderr)
            sent, failed = _gmail_fallback("Fallback ")
            transport_used = "https"
        except Exception as e:  # noqa: BLE001 — báo gọn cho user non-tech
            die(f"Gửi mail lỗi: {e}")

    where = " (qua Gmail API/HTTPS)" if transport_used == "https" else f" | host={host}:{port}"
    if args.split:
        print(f"✅ Đã gửi {len(sent)} email RIÊNG (mỗi người 1 mail) tới: {', '.join(sent)}{where} | from={mail_from}")
        if failed:
            print("⚠️  Gửi LỖI cho: " + "; ".join(f"{a} ({e})" for a, e in failed), file=sys.stderr)
    else:
        print(f"✅ Đã gửi tới: {', '.join(all_rcpt)}{where} | from={mail_from}")


if __name__ == "__main__":
    main()
