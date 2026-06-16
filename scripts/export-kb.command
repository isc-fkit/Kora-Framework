#!/usr/bin/env bash
# export-kb.command — XUẤT toàn bộ tri thức (DATA) của bạn ra 1 file .zip để dời máy.
#
# Gói gồm: vault (<...>_Brain), dữ liệu .kb, các thư mục docs nghiệp vụ, inbox,
# config (factory-config.yaml + domain-rules.md) và các file .env (TRỪ .env.example).
# Kèm manifest.json ghi phiên bản + đường dẫn vault để máy mới khôi phục đúng chỗ.
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

have zip || die "Thiếu lệnh 'zip'. Hãy cài zip rồi chạy lại."

# Ngày giờ: truyền từ ngoài (biến môi trường NGAY) hoặc tự sinh.
NGAY="${NGAY:-$(date +%Y%m%d-%H%M)}"

VAULT="$(vault_dir)"
PROJECT="$(project_name)"
VERSION="$(read_version)"

# Tên project an toàn cho tên file (thay khoảng trắng/ký tự lạ bằng '-').
SAFE_PROJECT="$(printf '%s' "$PROJECT" | tr ' /\\:' '----' | tr -cd '[:alnum:]._-')"
[ -n "$SAFE_PROJECT" ] || SAFE_PROJECT="project"

ZIP_NAME="kora-kb-${SAFE_PROJECT}-${NGAY}.zip"
ZIP_PATH="$REPO_ROOT/$ZIP_NAME"

echo "================================================================"
echo "  XUẤT tri thức — Kora-Framework"
echo "  Project : $PROJECT"
echo "  Vault   : $VAULT"
echo "  Phiên bản: v$VERSION"
echo "================================================================"
echo ""

# --- Tập hợp danh sách DATA path thực sự tồn tại -----------------------------
INCLUDE=()

# Vault động.
if [ -e "$REPO_ROOT/$VAULT" ]; then
  INCLUDE+=( "$VAULT" )
else
  echo "⚠️  Không thấy thư mục vault '$VAULT' — bỏ qua."
fi

# Các DATA path cố định.
for p in "${DATA_PATHS[@]}"; do
  if [ -e "$REPO_ROOT/$p" ]; then
    INCLUDE+=( "$p" )
  fi
done

# File .env per-source (trừ .env.example).
while IFS= read -r envp; do
  [ -n "$envp" ] || continue
  if [ -e "$REPO_ROOT/$envp" ]; then
    INCLUDE+=( "$envp" )
  fi
done < <(data_env_files)

if [ "${#INCLUDE[@]}" -eq 0 ]; then
  die "Không tìm thấy bất kỳ dữ liệu tri thức nào để xuất."
fi

# --- Tạo manifest.json tạm ---------------------------------------------------
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/akb-export.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
MANIFEST="$TMP_DIR/manifest.json"
EXPORTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$MANIFEST" <<EOF
{
  "version": "$VERSION",
  "exported_at": "$EXPORTED_AT",
  "vault_path": "$VAULT",
  "project_name": "$PROJECT"
}
EOF

echo "📦 Đang đóng gói ${#INCLUDE[@]} mục dữ liệu..."
echo ""

# Xóa zip cũ trùng tên (nếu chạy lại trong cùng phút).
[ -f "$ZIP_PATH" ] && rm -f "$ZIP_PATH"

# Đóng các DATA path (đường dẫn tương đối repo root) vào zip.
zip -q -r "$ZIP_PATH" "${INCLUDE[@]}" || die "Đóng gói dữ liệu thất bại."

# Thêm manifest.json vào gốc zip (-j: bỏ phần thư mục, nằm ở root zip).
zip -q -j "$ZIP_PATH" "$MANIFEST" || die "Thêm manifest vào gói thất bại."

# --- Báo kết quả -------------------------------------------------------------
SIZE="$(du -h "$ZIP_PATH" | awk '{print $1}')"
echo "✅ Đã tạo gói tri thức:"
echo "     $ZIP_PATH"
echo "     Kích thước: $SIZE"
echo ""
echo "💡 Chép file này sang máy mới (đã cài bản app sạch) rồi chạy:"
echo "     scripts/import-kb.command   (macOS)"
echo "     scripts\\import-kb.bat       (Windows)"

echo ""
read -r -p "Xong. Nhấn Enter để đóng cửa sổ..." _ || true
