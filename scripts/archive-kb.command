#!/usr/bin/env bash
# archive-kb.command — ĐÓNG GÓI KB có PHÂN QUYỀN + mật khẩu để bàn giao cho user khác.
#
# Khác export-kb (sao lưu thuần): có CỔNG MẬT KHẨU, ship key READ-ONLY cloud-KB, và đánh
# dấu gói là HOST hay USER. Gói = thư mục 'kora-archive/' { manifest.json, data/, .env.local
# (chỉ key READ), markers/package.type }.
#
# Skill /kora-archive truyền lựa chọn qua BIẾN MÔI TRƯỜNG (Claude điều phối):
#   KORA_ARCHIVE_PW         mật khẩu (hoặc nhập qua stdin)         [bắt buộc]
#   KORA_PKG_TYPE           user | host                            [mặc định user]
#   KORA_PKG_PERMISSION     read-only | read-write                 [mặc định read-only]
#   KORA_CLOUD_READ_BASE_URL / KORA_CLOUD_READ_USER / KORA_CLOUD_READ_TOKEN   key READ ship kèm
#   KORA_CLOUD_SPACE        space KB chung
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib-paths.sh
source "$SCRIPT_DIR/lib-paths.sh"
cd "$REPO_ROOT"
self_dequarantine

have() { command -v "$1" >/dev/null 2>&1; }
die() { echo ""; echo "❌ $1"; echo ""; read -r -p "Nhấn Enter để đóng cửa sổ..." _ || true; exit 1; }
have zip || die "Thiếu lệnh 'zip'."

# --- CỔNG MẬT KHẨU -----------------------------------------------------------
PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || die "Cần Python 3."
echo "🔐 Kiểm tra mật khẩu archive..."
if [ -n "${KORA_ARCHIVE_PW:-}" ]; then
  KORA_ARCHIVE_PW="$KORA_ARCHIVE_PW" "$PY" "$REPO_ROOT/tools/archive-gate/verify_password.py" >/dev/null \
    || die "Sai mật khẩu — không tạo archive."
else
  "$PY" "$REPO_ROOT/tools/archive-gate/verify_password.py" >/dev/null \
    || die "Sai mật khẩu — không tạo archive."
fi
echo "   ✅ Mật khẩu hợp lệ."

PKG_TYPE="${KORA_PKG_TYPE:-user}"
PKG_PERM="${KORA_PKG_PERMISSION:-read-only}"
NGAY="${NGAY:-$(date +%Y%m%d-%H%M)}"
VAULT="$(vault_dir)"; PROJECT="$(project_name)"; VERSION="$(read_version)"
SAFE_PROJECT="$(printf '%s' "$PROJECT" | tr ' /\\:' '----' | tr -cd '[:alnum:]._-')"; [ -n "$SAFE_PROJECT" ] || SAFE_PROJECT="project"
ZIP_PATH="$REPO_ROOT/kora-archive-${SAFE_PROJECT}-${NGAY}.zip"

echo "================================================================"
echo "  ARCHIVE bàn giao — Kora-Framework"
echo "  Project: $PROJECT | Loại: $PKG_TYPE ($PKG_PERM) | v$VERSION"
echo "================================================================"

# --- Dựng staging kora-archive/ ---------------------------------------------
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/akb-archive.XXXXXX")"; trap 'rm -rf "$TMP_DIR"' EXIT
STAGE="$TMP_DIR/kora-archive"; mkdir -p "$STAGE/data" "$STAGE/markers"

stage_copy() { # $1 = path tương đối repo root
  local rel="$1"; [ -e "$REPO_ROOT/$rel" ] || return 0
  mkdir -p "$STAGE/data/$(dirname "$rel")"; cp -R "$REPO_ROOT/$rel" "$STAGE/data/$(dirname "$rel")/"
}

[ -e "$REPO_ROOT/$VAULT" ] && stage_copy "$VAULT" || echo "⚠️  Không thấy vault '$VAULT'."
for p in "${DATA_PATHS[@]}"; do
  # Gói USER: bỏ reports/ (chỉ HOST mới có báo cáo).
  if [ "$PKG_TYPE" = "user" ] && [ "$p" = "reports" ]; then continue; fi
  stage_copy "$p"
done

# AN TOÀN: tuyệt đối KHÔNG để lọt .env (token write/mail/jira) vào data/.
find "$STAGE/data" -name ".env" -o -name ".env.local" -o -name ".env.*" 2>/dev/null \
  | grep -v "\.env\.example$" | while read -r f; do rm -f "$f"; done || true

# --- Key READ-ONLY (ship riêng, KHÔNG phải token của host) -------------------
if [ -n "${KORA_CLOUD_READ_TOKEN:-}" ]; then
  cat > "$STAGE/.env.local" <<EOF
# Key READ-ONLY cloud-KB chung (ship trong archive) — chỉ GET. KHÔNG có quyền đẩy.
CONFLUENCE_BASE_URL=${KORA_CLOUD_READ_BASE_URL:-}
CONFLUENCE_EMAIL=${KORA_CLOUD_READ_USER:-}
CONFLUENCE_API_TOKEN=${KORA_CLOUD_READ_TOKEN}
CONFLUENCE_AUTH=token
EOF
  echo "🔑 Đã ship key READ-ONLY (.env.local trong gói)."
else
  echo "ℹ️  Không có KORA_CLOUD_READ_TOKEN → gói KHÔNG kèm key đọc (user tự cấu hình sau)."
fi

# --- (Tùy chọn) Cred SMTP NO-REPLY báo lỗi → để gói USER tự email người phụ trách khi lịch lỗi ----
# Chỉ ship khi HOST cung cấp (KHÔNG dùng mail cá nhân host). Gửi 1 chiều, đặt vào report-mailer/.env.local lúc import.
if [ -n "${KORA_NOTIFY_SMTP_USER:-}" ] && [ -n "${KORA_NOTIFY_SMTP_PASS:-}" ]; then
  cat > "$STAGE/notify-smtp.env" <<EOF
# SMTP NO-REPLY báo SỰ CỐ (ship trong archive USER) — gửi 1 chiều cho người phụ trách khi lịch nền lỗi.
SMTP_HOST=${KORA_NOTIFY_SMTP_HOST:-smtp.gmail.com}
SMTP_PORT=${KORA_NOTIFY_SMTP_PORT:-587}
SMTP_SECURITY=${KORA_NOTIFY_SMTP_SECURITY:-starttls}
SMTP_USER=${KORA_NOTIFY_SMTP_USER}
SMTP_PASS=${KORA_NOTIFY_SMTP_PASS}
MAIL_FROM=${KORA_NOTIFY_MAIL_FROM:-${KORA_NOTIFY_SMTP_USER}}
EOF
  echo "📨 Đã ship cred SMTP no-reply báo lỗi (notify-smtp.env trong gói) → USER lỗi sẽ email người phụ trách."
else
  echo "ℹ️  Không có KORA_NOTIFY_SMTP_USER/PASS → gói USER lỗi chỉ GHI LOG cục bộ (không email người phụ trách)."
fi

# --- manifest + marker (KHÔNG secret trong manifest) -------------------------
cat > "$STAGE/manifest.json" <<EOF
{
  "version": "$VERSION",
  "exported_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "vault_path": "$VAULT",
  "project_name": "$PROJECT",
  "package_type": "$PKG_TYPE",
  "permission": "$PKG_PERM",
  "cloud_kb": { "base_url": "${KORA_CLOUD_READ_BASE_URL:-}", "space": "${KORA_CLOUD_SPACE:-}" }
}
EOF
printf '%s\n' "$PKG_TYPE" > "$STAGE/markers/package.type"

# --- Zip cả thư mục kora-archive/ -------------------------------------------
[ -f "$ZIP_PATH" ] && rm -f "$ZIP_PATH"
( cd "$TMP_DIR" && zip -q -r "$ZIP_PATH" kora-archive ) || die "Đóng gói thất bại."

SIZE="$(du -h "$ZIP_PATH" | awk '{print $1}')"
echo ""
echo "✅ Đã tạo archive: $ZIP_PATH ($SIZE)"
echo "💡 Gửi file cho user → họ chạy: scripts/import-kb.command (macOS) / scripts\\import-kb.bat (Windows)."
[ "$PKG_TYPE" = "user" ] && echo "   Gói USER: máy nhận sẽ TẮT report/mail, chỉ get&post KB chung (1 chiều nếu read-only)."
echo ""
read -r -p "Xong. Nhấn Enter để đóng cửa sổ..." _ || true
