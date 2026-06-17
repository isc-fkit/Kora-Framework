#!/usr/bin/env bash
# install.command — Cài Kora-Framework skills vào ~/.claude (managed, KHÔNG để lại folder source).
#
# Cách dùng:
#   - Double-click file này (macOS), hoặc
#   - 1 dòng:  bash <(curl -fsSL https://raw.githubusercontent.com/isc-fkit/Kora-Framework/release/install.command)
#   - Chạy lại bất cứ lúc nào = CẬP NHẬT (tự kéo bản mới, thêm skill mới).
#
# Test cục bộ (không tải mạng):  KORA_SRC=/duong/dan/repo  bash install.command
set -euo pipefail

REPO="${KORA_REPO:-isc-fkit/Kora-Framework}"
REF="${KORA_REF:-release}"
SRC_LOCAL="${KORA_SRC:-}"                 # set = copy từ repo cục bộ (để test), bỏ trống = tải GitHub
DEST_CMD="$HOME/.claude/commands"
DEST_CORE="$HOME/.claude/kora-framework"

have(){ command -v "$1" >/dev/null 2>&1; }
pause(){ [ -t 0 ] && read -r -p "${1:-Nhấn Enter để đóng...}" _ || true; }
die(){ echo ""; echo "❌ $1"; echo ""; pause; exit 1; }

# Tự gỡ nhãn quarantine cho thư mục chứa script (macOS) → double-click lần sau sạch.
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
if [ "$(uname -s 2>/dev/null)" = "Darwin" ] && have xattr && [ -n "$SELF_DIR" ]; then
  xattr -dr com.apple.quarantine "$SELF_DIR" >/dev/null 2>&1 || true
fi

echo "================================================================"
echo "  Kora-Framework — cài skills vào ~/.claude"
echo "================================================================"
echo ""
mkdir -p "$DEST_CMD" "$DEST_CORE"

# --- Lấy cây nguồn CORE (SRC) ---
if [ -n "$SRC_LOCAL" ]; then
  SRC="$SRC_LOCAL"
  echo "ℹ️  Dùng nguồn cục bộ: $SRC"
else
  have curl || die "Thiếu 'curl'."
  have tar  || die "Thiếu 'tar'."
  TMP="$(mktemp -d "${TMPDIR:-/tmp}/kora-install.XXXXXX")"
  trap 'rm -rf "$TMP"' EXIT
  echo "⬇️  Đang tải bản mới nhất..."
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/$REF.tar.gz" -o "$TMP/src.tgz" \
    || die "Tải thất bại. Kiểm tra mạng rồi thử lại."
  tar -xzf "$TMP/src.tgz" -C "$TMP" || die "Giải nén thất bại."
  SRC="$(find "$TMP" -maxdepth 1 -type d -name "*-$REF" | head -n1)"
  [ -n "$SRC" ] && [ -d "$SRC" ] || die "Không thấy thư mục nguồn sau giải nén."
fi

# --- 1) Skills → ~/.claude/commands/ (xóa kora-* cũ trước → bỏ skill đã đổi tên/gỡ) ---
echo "📥 Cài lệnh /kora-* ..."
rm -f "$DEST_CMD"/kora-*.md 2>/dev/null || true
cp "$SRC"/.claude/commands/kora-*.md "$DEST_CMD"/ 2>/dev/null || die "Không thấy skill kora-*.md trong nguồn."
N="$(ls -1 "$DEST_CMD"/kora-*.md 2>/dev/null | wc -l | tr -d ' ')"

# --- 2) CORE hỗ trợ → ~/.claude/kora-framework/ (ẩn, quản lý; KHÔNG phải folder source để sửa) ---
echo "📥 Cài workflows hỗ trợ ..."
for d in workflows scripts templates config tools; do
  if [ -e "$SRC/$d" ]; then
    rm -rf "$DEST_CORE/$d" 2>/dev/null || true
    cp -R "$SRC/$d" "$DEST_CORE/$d"
  fi
done
[ -f "$SRC/CLAUDE.md" ] && cp "$SRC/CLAUDE.md" "$DEST_CORE/" || true

echo ""
echo "✅ Đã cài $N skill Kora vào ~/.claude."
echo "   Mở Claude Cowork (hoặc chat mới) → gõ  /kora-init  để bắt đầu."
echo "   Cập nhật:  chạy lại file này (hoặc /kora-update)."
echo "   Gỡ:        chạy uninstall.command (hoặc /kora-uninstall)."
pause
