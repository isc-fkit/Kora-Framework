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
import shlex
import smtplib
import ssl
import sys
import time
from datetime import datetime
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
    ap.add_argument("--banner", help="Ảnh banner nhúng inline (cid:kora-banner). Mặc định assets/banner-daily-report.jpg.")
    ap.add_argument("--test", action="store_true", help="Gửi email test nhỏ (không cần report).")
    ap.add_argument("--check", action="store_true", help="Chỉ kiểm tra cấu hình + đăng nhập SMTP (KHÔNG gửi).")
    ap.add_argument("--env", help="Đường dẫn .env.local (ưu tiên cao nhất; mặc định đọc KORA_MAILER_ENV rồi .env.local cạnh script).")
    ap.add_argument("--emit-command", action="store_true",
                    help="KHÔNG gửi — in 1 DÒNG LỆNH (path tuyệt đối) để chạy ở TERMINAL gửi tiếp (bàn giao khi "
                         "Cowork sandbox chặn SMTP). Secret KHÔNG in (vẫn ở .env.local).")
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
            if not args.no_attach_html:
                attachments.append(str(p))
        subject = subject or "[Kora] Báo cáo tiến độ"
        text = text or "Báo cáo tiến độ Kora — xem nội dung email (HTML) hoặc file đính kèm."

    # Banner header NHÚNG INLINE (cid:kora-banner) → hiện NGAY cả khi client chặn ảnh remote (Outlook "trust sender").
    # Resolve path bền (như KORA_MAILER_ENV): --banner → KORA_BANNER → cạnh CORE (assets) → cwd/assets.
    banner_cid_path = None
    if html and not args.test:
        # Ưu tiên JPEG (nhẹ ~117KB) → fallback PNG (bản cũ). Path bền: --banner → KORA_BANNER → cạnh CORE → cwd.
        cands = [args.banner, os.getenv("KORA_BANNER")]
        for base in (HERE.parents[1] / "assets", Path.cwd() / "assets"):
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
            # Outlook hiện ngay ảnh CID (không bắt "tin cậy/download pictures" như ảnh remote) — NHƯNG `add_related`
            # đặt `Content-ID: kora-banner` KHÔNG ngoặc nhọn → Outlook không khớp `src="cid:kora-banner"`. RFC 2392
            # yêu cầu Content-ID bọc <...>. Sửa: thêm ngoặc nhọn + Content-Disposition inline kèm filename + X-Attachment-Id.
            related = msg.get_payload()[-1]          # text/html → đã thành multipart/related sau add_related
            img_part = related.get_payload()[-1]     # phần ảnh vừa thêm
            img_part.replace_header("Content-ID", "<kora-banner>")
            del img_part["Content-Disposition"]      # add_related set 'inline' (không filename) → thay bằng có filename
            img_part.add_header("Content-Disposition", "inline",
                                filename="banner" + (banner_cid_path.suffix or ".jpg"))
            img_part.add_header("X-Attachment-Id", "kora-banner")

    # Tên đính kèm KHÁC NHAU mỗi lần: report HTML cố định (progress-report-latest / email-body-latest /
    # processing_report…) được đổi sang tên có NGÀY-GIỜ → client mail không lấy lại bản cũ cùng tên, và
    # người nhận thấy rõ đây là bản mới. (File đính kèm khác giữ nguyên tên gốc.)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    def _attach_name(name):
        if re.search(r"(progress[-_]?report|processing[-_]?report)", name, re.I) and name.lower().endswith((".html", ".htm")):
            return f"progress-report-{stamp}.html"
        if re.search(r"email[-_]?body", name, re.I) and name.lower().endswith((".html", ".htm")):
            return f"email-body-{stamp}.html"
        return name

    seen_names = set()
    for fp in attachments:
        p = Path(fp)
        if not p.exists():
            print(f"⚠️  Bỏ qua đính kèm (không thấy): {p}", file=sys.stderr)
            continue
        ctype, _ = mimetypes.guess_type(str(p))
        maintype, subtype = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
        fname = _attach_name(p.name)
        if fname in seen_names:  # tránh 2 đính kèm trùng tên trong cùng mail
            continue
        seen_names.add(fname)
        msg.add_attachment(p.read_bytes(), maintype=maintype, subtype=subtype, filename=fname)

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

    try:
        if security == "ssl":
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as s:
                s.login(user, pw)
                sent, failed = _deliver(s)
        else:  # starttls (mặc định, cổng 587)
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                s.login(user, pw)
                sent, failed = _deliver(s)
    except smtplib.SMTPAuthenticationError:
        print("SMTP_AUTH_FAILED", file=sys.stderr)   # marker máy-đọc: sai App Password → nhắc sửa creds
        die("Xác thực SMTP thất bại. Gmail: phải dùng App Password (bật 2FA rồi tạo tại "
            "https://myaccount.google.com/apppasswords), KHÔNG dùng mật khẩu Gmail thường.")
    except (OSError, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError) as e:
        print("SMTP_UNREACHABLE", file=sys.stderr)   # marker: mạng/sandbox chặn → skill bàn giao bash cho terminal
        die(f"Không kết nối được SMTP (mạng/sandbox Cowork chặn?): {e}")
    except Exception as e:  # noqa: BLE001 — báo gọn cho user non-tech
        die(f"Gửi mail lỗi: {e}")

    if args.split:
        print(f"✅ Đã gửi {len(sent)} email RIÊNG (mỗi người 1 mail) tới: {', '.join(sent)} "
              f"| host={host}:{port} | from={mail_from}")
        if failed:
            print("⚠️  Gửi LỖI cho: " + "; ".join(f"{a} ({e})" for a, e in failed), file=sys.stderr)
    else:
        print(f"✅ Đã gửi tới: {', '.join(all_rcpt)} | host={host}:{port} | from={mail_from}")


if __name__ == "__main__":
    main()
