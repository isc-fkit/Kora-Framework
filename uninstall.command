#!/usr/bin/env bash
# uninstall.command — Gỡ Kora-Framework skills khỏi ~/.claude. (Tri thức/project của bạn KHÔNG bị đụng.)
set -euo pipefail

DEST_CMD="$HOME/.claude/commands"
DEST_CORE="$HOME/.claude/kora-framework"

# Resolve Downloads (đồng bộ với installer) để dọn folder Skill
DL_BASE="$HOME/Downloads"
if [ "$(uname -s 2>/dev/null)" = "Linux" ] && command -v xdg-user-dir >/dev/null 2>&1; then
  _d="$(xdg-user-dir DOWNLOAD 2>/dev/null || true)"; [ -n "$_d" ] && DL_BASE="$_d"
fi
[ -d "$DL_BASE" ] || DL_BASE="$HOME"
SKILL_DIR="$DL_BASE/Knowledge-Base/Skill"

pause(){ [ -t 0 ] && read -r -p "${1:-Nhấn Enter để đóng...}" _ || true; }

echo "================================================================"
echo "  Gỡ Kora-Framework skills khỏi ~/.claude"
echo "================================================================"
echo "Sẽ xóa:"
echo "  - $DEST_CMD/kora-*.md"
echo "  - $DEST_CORE/"
echo "  - $SKILL_DIR/  (chỉ skill — tri thức trong Knowledge-Base được giữ)"
echo ""
if [ -t 0 ]; then
  read -r -p "Gõ 'yes' để xác nhận: " ans || true
  [ "${ans:-}" = "yes" ] || { echo "Đã hủy."; exit 0; }
fi

rm -f "$DEST_CMD"/kora-*.md 2>/dev/null || true
rm -rf "$DEST_CORE" 2>/dev/null || true
rm -rf "$SKILL_DIR" 2>/dev/null || true
rmdir "$DL_BASE/Knowledge-Base" 2>/dev/null || true   # chỉ xóa nếu rỗng (chừa tri thức nếu đã /kora-init)
rm -rf "$DL_BASE/Kora-Skills" "$DL_BASE/Kora-Skills.zip" 2>/dev/null || true   # dọn folder cũ nếu còn sót
echo ""
echo "✅ Đã gỡ skill Kora."
echo ""
echo "Nếu bạn từng đặt token API, hãy XÓA TAY các dòng sau trong ~/.zshrc / ~/.bashrc:"
grep -nE '^export KORA_' "$HOME/.zshrc" "$HOME/.bashrc" 2>/dev/null || echo "  (không tìm thấy dòng KORA_ nào)"
pause
