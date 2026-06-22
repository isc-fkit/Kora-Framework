#!/usr/bin/env python3
"""
verify_password.py — Cổng MẬT KHẨU cho luồng đóng gói archive (handover).

Mật khẩu KHÔNG nằm trong source. Hash (SHA-256 có salt) được host trên repo (nhánh release)
nên CHỦ REPO đổi mật khẩu = sửa 1 file, không cần phát hành lại app. Script lấy hash hiện
tại, băm input rồi so khớp hằng-thời-gian (hmac.compare_digest).

Mật khẩu đọc từ stdin hoặc biến môi trường KORA_ARCHIVE_PW — KHÔNG bao giờ qua argv
(tránh lọt vào log/ps). Chỉ in OK/❌, exit 0/1. Chỉ thư viện chuẩn.

Dùng:
  echo -n "<password>" | python3 tools/archive-gate/verify_password.py
  KORA_ARCHIVE_PW="<password>" python3 tools/archive-gate/verify_password.py
"""
import hashlib
import hmac
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SALT = "claude-knowledge-archive::v1"  # đổi salt = phải tính lại hash trên repo
REMOTE = "https://raw.githubusercontent.com/isc-fkit/Kora-Framework/release/config/archive-pw.sha256"
LOCAL_FALLBACKS = [
    REPO_ROOT / "config" / "archive-pw.sha256",
    Path.home() / ".claude" / "kora-framework" / "config" / "archive-pw.sha256",
]


def fetch_hash() -> str:
    """Ưu tiên hash trên repo (cho phép chủ repo đổi mật khẩu từ xa); offline → bản bundle."""
    try:
        with urllib.request.urlopen(REMOTE, timeout=10) as r:
            h = r.read().decode("utf-8").strip()
            if h:
                return h
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        pass
    for p in LOCAL_FALLBACKS:
        if p.exists():
            h = p.read_text(encoding="utf-8").strip()
            if h:
                return h
    return ""


def read_password() -> str:
    pw = os.getenv("KORA_ARCHIVE_PW")
    if pw:
        return pw.strip()
    if not sys.stdin.isatty():
        return sys.stdin.readline().strip()
    try:
        import getpass
        return getpass.getpass("Mật khẩu archive: ").strip()
    except Exception:  # noqa: BLE001
        return ""


def main():
    expected = fetch_hash()
    if not expected:
        print("❌ Không lấy được hash mật khẩu (mạng lỗi và không có bản bundle). "
              "Kiểm tra mạng hoặc cài lại app.", file=sys.stderr)
        sys.exit(1)
    pw = read_password()
    if not pw:
        print("❌ Chưa nhập mật khẩu.", file=sys.stderr)
        sys.exit(1)
    digest = hashlib.sha256((SALT + pw).encode("utf-8")).hexdigest()
    if hmac.compare_digest(digest, expected):
        print("OK")
        sys.exit(0)
    print("❌ Sai mật khẩu.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
