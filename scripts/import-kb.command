#!/usr/bin/env bash
# import-kb.command — NHẬP tri thức (DATA) trên một máy mới đã cài bản app sạch.
#
# Cách dùng:
#   scripts/import-kb.command [đường-dẫn-file.zip]
#   - Không truyền: tự lấy file genesis1-kb-*.zip MỚI NHẤT ở thư mục gốc repo.
#
# Việc làm:
#   - Giải nén ra temp, đọc manifest.json.
#   - Copy DATA về đúng chỗ. Vault đặt theo vault_path trong manifest và cập nhật
#     lại 'vault_path:' trong config/factory-config.yaml cho khớp.
#   - Cảnh báo nếu sẽ ghi đè vault đang tồn tại (hỏi y/N).
#   - Dựng lại index bằng kb-indexer.
#
# Chạy được từ bất kỳ đâu — script tự về thư mục gốc repo.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib-paths.sh
source "$SCRIPT_DIR/lib-paths.sh"
cd "$REPO_ROOT"

# Gỡ nhãn quarantine cho các script còn lại → lần sau double-click không bị macOS hỏi nữa.
self_dequarantine

have() { command -v "$1" >/dev/null 2>&1; }

die() {
  echo ""
  echo "❌ $1"
  echo ""
  read -r -p "Nhấn Enter để đóng cửa sổ..." _ || true
  exit 1
}

have ditto || have unzip || die "Cần 'ditto' (macOS) hoặc 'unzip' để giải nén."

echo "================================================================"
echo "  NHẬP tri thức — Kora-Framework"
echo "  Thư mục: $REPO_ROOT"
echo "================================================================"
echo ""

# --- Xác định file zip -------------------------------------------------------
ZIP_IN="${1:-}"
if [ -z "$ZIP_IN" ]; then
  # Lấy gói kora-kb-*.zip (hoặc genesis1-kb-*.zip cũ) mới nhất ở repo root.
  ZIP_IN="$(ls -t "$REPO_ROOT"/kora-kb-*.zip "$REPO_ROOT"/genesis1-kb-*.zip 2>/dev/null | head -n1 || true)"
  [ -n "$ZIP_IN" ] || die "Không tìm thấy file kora-kb-*.zip (hoặc genesis1-kb-*.zip) nào ở '$REPO_ROOT'. Hãy truyền đường dẫn file zip làm tham số."
  echo "ℹ️  Dùng gói mới nhất: $(basename "$ZIP_IN")"
fi
[ -f "$ZIP_IN" ] || die "Không thấy file zip: $ZIP_IN"

# --- Giải nén ra temp --------------------------------------------------------
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/akb-import.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "📂 Đang giải nén..."
# UTF-8 an toàn cho tên note tiếng Việt: ưu tiên ditto (macOS, chuẩn UTF-8), fallback unzip.
if have ditto; then
  ditto -x -k "$ZIP_IN" "$TMP_DIR" || die "Giải nén thất bại (file có thể hỏng)."
else
  unzip -q "$ZIP_IN" -d "$TMP_DIR" || die "Giải nén thất bại (file có thể hỏng)."
fi

MANIFEST="$TMP_DIR/manifest.json"
[ -f "$MANIFEST" ] || die "Gói không hợp lệ: thiếu manifest.json."

# Đọc vault_path từ manifest (không cần jq).
MANIFEST_VAULT="$(grep -E '"vault_path"[[:space:]]*:' "$MANIFEST" | head -n1 \
  | sed -E 's/.*"vault_path"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')"
[ -n "$MANIFEST_VAULT" ] || MANIFEST_VAULT="$(vault_dir)"
echo "   Vault trong gói: $MANIFEST_VAULT"
echo ""

# --- Cảnh báo nếu sẽ ghi đè vault đang có ------------------------------------
TARGET_VAULT="$REPO_ROOT/$MANIFEST_VAULT"
if [ -e "$TARGET_VAULT" ]; then
  echo "⚠️  Thư mục vault '$MANIFEST_VAULT' ĐÃ tồn tại ở máy này và sẽ bị GHI ĐÈ."
  read -r -p "    Tiếp tục? (y/N) " ans || true
  case "${ans:-}" in
    y|Y|yes|YES) ;;
    *) die "Đã hủy theo yêu cầu của bạn. Không có gì bị thay đổi." ;;
  esac
fi

# Vault đích đã tồn tại + user đồng ý → XÓA SẠCH để thay mới (tránh file thừa lẫn lộn).
[ -e "$TARGET_VAULT" ] && rm -rf "$TARGET_VAULT"

echo ""
echo "📥 Đang nhập dữ liệu về đúng chỗ..."

# --- Copy mọi thứ trong temp (trừ manifest.json) về repo root ----------------
# Dùng cp -R giữ cấu trúc; đếm số file đã copy.
COUNT=0
shopt -s dotglob nullglob
for entry in "$TMP_DIR"/*; do
  base="$(basename "$entry")"
  [ "$base" = "manifest.json" ] && continue
  # Copy đè vào repo root, giữ nguyên cây thư mục.
  cp -R "$entry" "$REPO_ROOT/"
  # Đếm số file (không tính thư mục).
  if [ -d "$entry" ]; then
    n=$(find "$entry" -type f | wc -l | tr -d ' ')
  else
    n=1
  fi
  COUNT=$((COUNT + n))
done
shopt -u dotglob nullglob

# --- Cập nhật vault_path trong config cho khớp manifest ----------------------
CFG="$REPO_ROOT/config/factory-config.yaml"
if [ -f "$CFG" ]; then
  CUR_VAULT="$(vault_dir)"
  if [ "$CUR_VAULT" != "$MANIFEST_VAULT" ]; then
    echo "🛠  Cập nhật vault_path trong config: '$CUR_VAULT' → '$MANIFEST_VAULT'"
    # Thay đúng dòng vault_path đầu tiên, giữ phần thụt đầu dòng.
    tmpcfg="$TMP_DIR/factory-config.yaml.new"
    awk -v val="$MANIFEST_VAULT" '
      BEGIN { done=0 }
      /^[[:space:]]*vault_path:/ && done==0 {
        match($0, /^[[:space:]]*/); indent=substr($0, RSTART, RLENGTH);
        print indent "vault_path: " val;
        done=1; next
      }
      { print }
    ' "$CFG" > "$tmpcfg" && cp "$tmpcfg" "$CFG"
  fi
fi

# --- Dựng lại index ----------------------------------------------------------
echo ""
echo "🔧 Đang dựng lại index (kb-indexer)..."
if have python3 && [ -f "$REPO_ROOT/tools/kb-indexer/build_index.py" ]; then
  if python3 "$REPO_ROOT/tools/kb-indexer/build_index.py" --root .; then
    echo "   Dựng index xong."
  else
    echo "   ⚠️  Dựng index gặp lỗi — bạn có thể chạy lại tay:"
    echo "       python3 tools/kb-indexer/build_index.py --root ."
  fi
else
  echo "   ⚠️  Không thấy python3 hoặc kb-indexer — bỏ qua bước dựng index."
  echo "       Sau khi cài python3, chạy: python3 tools/kb-indexer/build_index.py --root ."
fi

echo ""
echo "✅ Đã nhập xong, $COUNT file."
echo ""
read -r -p "Xong. Nhấn Enter để đóng cửa sổ..." _ || true
