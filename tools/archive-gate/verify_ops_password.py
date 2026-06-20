#!/usr/bin/env python3
"""
verify_ops_password.py — Cổng MẬT KHẨU VẬN HÀNH cho các luồng GHI/PHÁT ra ngoài:
  • /kora-sync     — đẩy KB lên Confluence / GitHub
  • /kora-send-mail — gửi email báo cáo
  • bước SYNC trong /kora-schedule (lịch tự đẩy)
KHÔNG áp cho /kora-export (export là thuần, không gác).

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


def read_password() -> str:
    pw = os.getenv("KORA_OPS_PW")
    if pw:
        return pw.strip()
    if not sys.stdin.isatty():
        return sys.stdin.readline().strip()
    try:
        import getpass
        return getpass.getpass("Mật khẩu vận hành (sync/mail): ").strip()
    except Exception:  # noqa: BLE001
        return ""


base.read_password = read_password


if __name__ == "__main__":
    base.main()
