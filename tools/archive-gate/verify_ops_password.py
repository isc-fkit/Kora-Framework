#!/usr/bin/env python3
"""
verify_ops_password.py — Cổng MẬT KHẨU VẬN HÀNH cho các luồng GHI/PHÁT ra ngoài:
  • /claude-knowledge-sync     — đẩy KB lên Confluence / GitHub
  • /claude-knowledge-send-mail — gửi email báo cáo
  • bước SYNC trong /claude-knowledge-schedule (lịch tự đẩy)
KHÔNG áp cho /claude-knowledge-export-* (export là thuần, không gác).

Tái dùng NGUYÊN cơ chế của verify_password.py (SHA-256 có salt, so khớp hằng-thời-gian
hmac.compare_digest, hash host trên repo nhánh release để CHỦ REPO đổi mật khẩu từ xa mà
không cần phát hành lại app) nhưng tách riêng:
  - salt:      kora-ops::v1
  - file hash: config/ops-pw.sha256          (độc lập với archive-pw.sha256 → xoay vòng riêng)
  - env:       KORA_OPS_PW

Mật khẩu host (người chạy framework) là "người dùng" — phải nhập mật khẩu do chủ repo đặt.
Mật khẩu KHÔNG bao giờ qua argv (tránh lọt log/ps). Chỉ in OK/❌, exit 0/1. Chỉ stdlib.

Dùng:
  KORA_OPS_PW="<password>" python3 tools/archive-gate/verify_ops_password.py
  echo -n "<password>" | python3 tools/archive-gate/verify_ops_password.py
"""
import os
import sys
from pathlib import Path

# Nạp module gốc (cùng thư mục) rồi GHI ĐÈ hằng số → tái dùng fetch_hash()/main(), không nhân bản logic.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_password as base  # noqa: E402

base.SALT = "kora-ops::v1"  # đổi salt = phải tính lại hash trên repo
base.REMOTE = "https://raw.githubusercontent.com/isc-fkit/Kora-Framework/release/config/ops-pw.sha256"
base.LOCAL_FALLBACKS = [
    base.REPO_ROOT / "config" / "ops-pw.sha256",
    Path.home() / ".claude" / "kora-framework" / "config" / "ops-pw.sha256",
]


def _read_pw_file() -> str:
    """Đọc KORA_OPS_PW từ file (cùng nơi scheduler dùng) → set file là CÓ HIỆU LỰC NGAY trong
    session đang chạy, KHÔNG cần `source ~/.zshrc` / mở terminal mới."""
    for p in (Path.home() / ".config" / "claude-knowledge" / "ops-pw.env",   # MỚI (claude-knowledge)
              Path.home() / ".claude-knowledge" / "ops-pw.env",              # Windows mới: %USERPROFILE%\.claude-knowledge\
              Path.home() / ".config" / "kora" / "ops-pw.env",               # CŨ — backward-compat (máy đặt trước rename)
              Path.home() / ".kora" / "ops-pw.env"):                         # Windows cũ: %USERPROFILE%\.kora\
        try:
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s.startswith("#"):
                    continue
                if s.startswith("export "):
                    s = s[7:].strip()
                if s.startswith("KORA_OPS_PW="):
                    return s.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            continue
    return ""


def read_password() -> str:
    pw = os.getenv("KORA_OPS_PW")          # 1) env var (ưu tiên cao nhất)
    if pw:
        return pw.strip()
    pw = _read_pw_file()                    # 2) file ~/.config/claude-knowledge/ops-pw.env (tức thời, không cần source)
    if pw:
        return pw
    if not sys.stdin.isatty():             # 3) stdin (pipe)
        return sys.stdin.readline().strip()
    try:                                    # 4) hỏi tương tác (TTY)
        import getpass
        return getpass.getpass("Mật khẩu vận hành (sync/mail): ").strip()
    except Exception:  # noqa: BLE001
        return ""


base.read_password = read_password


if __name__ == "__main__":
    base.main()
