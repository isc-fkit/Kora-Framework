#!/usr/bin/env bash
# import-kb.command — NHẬP tri thức (DATA) trên máy đã cài bản app sạch.
#
# Hỗ trợ 2 loại gói:
#   - SAO LƯU (export-kb): kora-kb-*.zip / genesis1-kb-*.zip — DATA phẳng ở gốc + manifest.json.
#   - ARCHIVE bàn giao (archive-kb): kora-archive-*.zip — có thư mục 'kora-archive/' gồm
#     data/, manifest.json (package_type/permission/cloud_kb), .env.local (key READ), markers/.
#
# Cách dùng:  scripts/import-kb.command [đường-dẫn-file.zip]
#   - Không truyền: tự lấy file MỚI NHẤT (kora-archive-* > kora-kb-* > genesis1-kb-*) ở repo root.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib-paths.sh
source "$SCRIPT_DIR/lib-paths.sh"
cd "$REPO_ROOT"
self_dequarantine

have() { command -v "$1" >/dev/null 2>&1; }
die() { echo ""; echo "❌ $1"; echo ""; read -r -p "Nhấn Enter để đóng cửa sổ..." _ || true; exit 1; }

have ditto || have unzip || die "Cần 'ditto' (macOS) hoặc 'unzip' để giải nén."

echo "================================================================"
echo "  NHẬP tri thức — Kora-Framework"
echo "  Thư mục: $REPO_ROOT"
echo "================================================================"
echo ""

# --- Xác định file zip -------------------------------------------------------
ZIP_IN="${1:-}"
if [ -z "$ZIP_IN" ]; then
  ZIP_IN="$(ls -t "$REPO_ROOT"/kora-archive-*.zip "$REPO_ROOT"/kora-kb-*.zip "$REPO_ROOT"/genesis1-kb-*.zip 2>/dev/null | head -n1 || true)"
  [ -n "$ZIP_IN" ] || die "Không tìm thấy gói (kora-archive-*.zip / kora-kb-*.zip) ở '$REPO_ROOT'. Truyền đường dẫn file zip làm tham số."
  echo "ℹ️  Dùng gói mới nhất: $(basename "$ZIP_IN")"
fi
[ -f "$ZIP_IN" ] || die "Không thấy file zip: $ZIP_IN"

# --- Giải nén ra temp --------------------------------------------------------
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/akb-import.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
echo "📂 Đang giải nén..."
if have ditto; then
  ditto -x -k "$ZIP_IN" "$TMP_DIR" || die "Giải nén thất bại (file có thể hỏng)."
else
  unzip -q "$ZIP_IN" -d "$TMP_DIR" || die "Giải nén thất bại (file có thể hỏng)."
fi

# --- Nhận diện loại gói: ARCHIVE (có kora-archive/) hay SAO LƯU phẳng ---------
if [ -f "$TMP_DIR/kora-archive/manifest.json" ]; then
  PKG_ROOT="$TMP_DIR/kora-archive"
  DATA_SRC="$PKG_ROOT/data"
  ARCHIVE_MODE=1
else
  PKG_ROOT="$TMP_DIR"
  DATA_SRC="$TMP_DIR"
  ARCHIVE_MODE=0
fi
MANIFEST="$PKG_ROOT/manifest.json"
[ -f "$MANIFEST" ] || die "Gói không hợp lệ: thiếu manifest.json."

MANIFEST_VAULT="$(read_manifest_field "$MANIFEST" vault_path)"
[ -n "$MANIFEST_VAULT" ] || MANIFEST_VAULT="$(vault_dir)"
PKG_TYPE="$(read_manifest_field "$MANIFEST" package_type)"
PKG_TYPE="${PKG_TYPE:-host}"
PKG_PERM="$(read_manifest_field "$MANIFEST" permission)"
echo "   Vault trong gói : $MANIFEST_VAULT"
echo "   Loại gói        : $PKG_TYPE${PKG_PERM:+ ($PKG_PERM)}"
echo ""

# --- Cảnh báo ghi đè vault ---------------------------------------------------
TARGET_VAULT="$REPO_ROOT/$MANIFEST_VAULT"
if [ -e "$TARGET_VAULT" ]; then
  echo "⚠️  Thư mục vault '$MANIFEST_VAULT' ĐÃ tồn tại và sẽ bị GHI ĐÈ."
  read -r -p "    Tiếp tục? (y/N) " ans || true
  case "${ans:-}" in y|Y|yes|YES) ;; *) die "Đã hủy. Không có gì bị thay đổi." ;; esac
  rm -rf "$TARGET_VAULT"
fi

echo "📥 Đang nhập dữ liệu về đúng chỗ..."
COUNT=0
shopt -s dotglob nullglob
for entry in "$DATA_SRC"/*; do
  base="$(basename "$entry")"
  # Bỏ qua các thành phần điều khiển của gói archive.
  case "$base" in manifest.json|markers|.env.local) [ "$ARCHIVE_MODE" = 1 ] && continue ;; esac
  cp -R "$entry" "$REPO_ROOT/"
  if [ -d "$entry" ]; then n=$(find "$entry" -type f | wc -l | tr -d ' '); else n=1; fi
  COUNT=$((COUNT + n))
done
shopt -u dotglob nullglob

# --- Cập nhật vault_path trong config ----------------------------------------
CFG="$REPO_ROOT/config/factory-config.yaml"
if [ -f "$CFG" ]; then
  CUR_VAULT="$(vault_dir)"
  if [ "$CUR_VAULT" != "$MANIFEST_VAULT" ]; then
    echo "🛠  Cập nhật vault_path: '$CUR_VAULT' → '$MANIFEST_VAULT'"
    tmpcfg="$TMP_DIR/factory-config.yaml.new"
    awk -v val="$MANIFEST_VAULT" '
      BEGIN { done=0 }
      /^[[:space:]]*vault_path:/ && done==0 {
        match($0, /^[[:space:]]*/); indent=substr($0, RSTART, RLENGTH);
        print indent "vault_path: " val; done=1; next }
      { print }' "$CFG" > "$tmpcfg" && cp "$tmpcfg" "$CFG"
  fi
fi

# --- Gói USER: đặt key READ + đánh dấu .kora-user ----------------------------
if [ "$ARCHIVE_MODE" = 1 ] && [ "$PKG_TYPE" = "user" ]; then
  if [ -f "$PKG_ROOT/.env.local" ]; then
    mkdir -p "$REPO_ROOT/tools/confluence-sync"
    cp "$PKG_ROOT/.env.local" "$REPO_ROOT/tools/confluence-sync/.env.local"
    echo "🔑 Đã đặt key READ cloud-KB vào tools/confluence-sync/.env.local (chỉ GET)."
  fi
  if [ -f "$PKG_ROOT/notify-smtp.env" ]; then
    mkdir -p "$REPO_ROOT/tools/report-mailer"
    cp "$PKG_ROOT/notify-smtp.env" "$REPO_ROOT/tools/report-mailer/.env.local"
    echo "📨 Đã đặt cred SMTP no-reply báo lỗi vào tools/report-mailer/.env.local → lịch USER lỗi sẽ email người phụ trách."
  fi
  printf 'package=user\nimported_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$REPO_ROOT/.kora-user"
  echo "🏷  Đã tạo .kora-user → máy này là GÓI NGƯỜI DÙNG: TẮT báo cáo/gửi mail; chỉ get&post KB chung."
  echo ""
  echo "👉 Bước kế (Claude sẽ làm khi bạn mở app): đặt package.type=user + cloud_kb.sync.enabled=true,"
  echo "   reports.email.enabled=false trong config, rồi lên LỊCH get&post (workflows/15-archive.md mục B)."
fi

# --- Dựng lại index ----------------------------------------------------------
echo ""
echo "🔧 Đang dựng lại index (kb-indexer)..."
if have python3 && [ -f "$REPO_ROOT/tools/kb-indexer/build_index.py" ]; then
  python3 "$REPO_ROOT/tools/kb-indexer/build_index.py" --root . \
    && echo "   Dựng index xong." \
    || echo "   ⚠️  Dựng index lỗi — chạy tay: python3 tools/kb-indexer/build_index.py --root ."
else
  echo "   ⚠️  Không thấy python3/kb-indexer — bỏ qua. Sau cài python3: python3 tools/kb-indexer/build_index.py --root ."
fi

echo ""
echo "✅ Đã nhập xong, $COUNT file."
echo ""
read -r -p "Xong. Nhấn Enter để đóng cửa sổ..." _ || true
