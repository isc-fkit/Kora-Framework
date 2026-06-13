#!/usr/bin/env bash
# update.command — CẬP NHẬT app "Adaptive Knowledge Base" mà GIỮ NGUYÊN tri thức của bạn.
#
# - Nếu bạn cài bằng git: chạy `git pull` (tri thức đã được gitignore nên không bị đụng).
# - Nếu bạn tải bản zip: tự tải bản mới nhất và chỉ ghi đè phần CHƯƠNG TRÌNH (CORE),
#   TUYỆT ĐỐI không đụng tới thư mục tri thức của bạn.
#
# Chạy được từ bất kỳ đâu — script tự về thư mục gốc repo.

set -euo pipefail

# --- Tự về repo root + nạp thư viện đường dẫn ---------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib-paths.sh
source "$SCRIPT_DIR/lib-paths.sh"
cd "$REPO_ROOT"

ZIP_URL="https://github.com/luugiakhanh689/adaptive_knowledge_base/archive/refs/heads/release.zip"

# --- Tiện ích ----------------------------------------------------------------
have() { command -v "$1" >/dev/null 2>&1; }

die() {
  echo ""
  echo "❌ $1"
  echo ""
  read -r -p "Nhấn Enter để đóng cửa sổ..." _ || true
  exit 1
}

finish() {
  echo ""
  read -r -p "Xong. Nhấn Enter để đóng cửa sổ..." _ || true
}

echo "================================================================"
echo "  CẬP NHẬT Adaptive Knowledge Base"
echo "  Thư mục: $REPO_ROOT"
echo "================================================================"
echo ""

OLD_VER="$(read_version)"
echo "📦 Phiên bản hiện tại: v$OLD_VER"
echo ""

# --- Trường hợp 1: có .git → dùng git pull -----------------------------------
if [ -d "$REPO_ROOT/.git" ]; then
  have git || die "Bạn cài bằng git nhưng máy chưa có 'git'. Hãy cài git rồi chạy lại."

  echo "🔄 Đang cập nhật bằng git (tri thức của bạn được giữ nguyên)..."
  echo ""
  if git pull --ff-only; then
    echo ""
    echo "✅ Cập nhật git thành công."
  else
    echo ""
    echo "⚠️  Không thể cập nhật tự động — thường do bạn có thay đổi cục bộ"
    echo "    trong phần chương trình (CORE), hoặc nhánh đã rẽ khác."
    echo ""
    echo "    Cách xử lý (chọn 1):"
    echo "    1) Xem thay đổi của bạn:   git -C \"$REPO_ROOT\" status"
    echo "    2) Tạm cất rồi cập nhật:   git -C \"$REPO_ROOT\" stash && git -C \"$REPO_ROOT\" pull --ff-only && git -C \"$REPO_ROOT\" stash pop"
    echo "    3) Nếu không cần thay đổi: git -C \"$REPO_ROOT\" reset --hard origin/release  (CẨN THẬN: bỏ thay đổi CORE; tri thức vẫn an toàn vì đã gitignore)"
    echo ""
    echo "    Tri thức của bạn KHÔNG bị ảnh hưởng dù chọn cách nào."
    finish
    exit 0
  fi

# --- Trường hợp 2: KHÔNG có .git → tải zip + rsync chỉ phần CORE --------------
else
  echo "ℹ️  Không thấy thư mục .git → bạn đang dùng bản tải zip."
  echo "    Sẽ tải bản mới nhất và chỉ ghi đè phần CHƯƠNG TRÌNH."
  echo ""
  have curl  || die "Thiếu lệnh 'curl'. Hãy cài curl rồi chạy lại."
  have unzip || die "Thiếu lệnh 'unzip'. Hãy cài unzip rồi chạy lại."
  have rsync || die "Thiếu lệnh 'rsync'. Hãy cài rsync rồi chạy lại."

  TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/akb-update.XXXXXX")"
  # Dọn temp khi thoát (mọi trường hợp).
  trap 'rm -rf "$TMP_DIR"' EXIT

  ZIP_FILE="$TMP_DIR/release.zip"
  echo "⬇️  Đang tải bản mới nhất..."
  curl -fL "$ZIP_URL" -o "$ZIP_FILE" || die "Tải bản mới thất bại. Kiểm tra kết nối mạng rồi thử lại."

  echo "📂 Đang giải nén..."
  unzip -q "$ZIP_FILE" -d "$TMP_DIR" || die "Giải nén thất bại (file tải về có thể hỏng)."

  # Thư mục giải nén thường là <repo>-release/
  SRC_DIR="$(find "$TMP_DIR" -maxdepth 1 -type d -name '*-release' | head -n1)"
  [ -n "$SRC_DIR" ] && [ -d "$SRC_DIR" ] || die "Không tìm thấy thư mục nguồn sau khi giải nén."

  echo "🔁 Đang ghi đè PHẦN CHƯƠNG TRÌNH (giữ nguyên tri thức của bạn)..."
  # rsync chỉ CORE: exclude .git + toàn bộ DATA path + vault động + mọi *_Brain + .env per-source.
  RSYNC_EXCLUDES=( --exclude ".git" --exclude ".git/" )
  for p in "${DATA_PATHS[@]}"; do
    RSYNC_EXCLUDES+=( --exclude "/$p" )
  done
  # Vault động + phòng hờ mọi thư mục *_Brain.
  VAULT="$(vault_dir)"
  RSYNC_EXCLUDES+=( --exclude "/$VAULT" --exclude "*_Brain/" )
  # .env per-source (TRỪ .env.example đã là CORE).
  while IFS= read -r envp; do
    [ -n "$envp" ] && RSYNC_EXCLUDES+=( --exclude "/$envp" )
  done < <(data_env_files)

  # rsync ĐÈ (không --delete để không xóa file người dùng ngoài danh sách).
  rsync -a "${RSYNC_EXCLUDES[@]}" "$SRC_DIR"/ "$REPO_ROOT"/ \
    || die "Ghi đè phần chương trình thất bại."

  echo ""
  echo "✅ Cập nhật chương trình thành công (tri thức của bạn được giữ nguyên)."
fi

# --- Báo version mới + nhắc reindex ------------------------------------------
NEW_VER="$(read_version)"
echo ""
echo "📦 Phiên bản mới: v$NEW_VER"
if [ "$OLD_VER" != "$NEW_VER" ]; then
  echo "   (đã nâng từ v$OLD_VER → v$NEW_VER)"
fi
echo ""
echo "💡 Nếu phần dựng index (kb-indexer) có thay đổi, hãy chạy lại:"
echo "     python3 tools/kb-indexer/build_index.py --root ."
echo "   để index/graph/health khớp với tri thức hiện tại."

finish
