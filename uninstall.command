#!/usr/bin/env bash
# uninstall.command — Gỡ Kora-Framework skills khỏi ~/.claude. (Tri thức/project của bạn KHÔNG bị đụng.)
set -euo pipefail

DEST_CMD="$HOME/.claude/commands"
DEST_CORE="$HOME/.claude/kora-framework"

pause(){ [ -t 0 ] && read -r -p "${1:-Nhấn Enter để đóng...}" _ || true; }

echo "================================================================"
echo "  Gỡ Kora-Framework skills khỏi ~/.claude"
echo "================================================================"
echo "Sẽ xóa:"
echo "  - $DEST_CMD/kora-*.md"
echo "  - $DEST_CORE/"
echo ""
if [ -t 0 ]; then
  read -r -p "Gõ 'yes' để xác nhận: " ans || true
  [ "${ans:-}" = "yes" ] || { echo "Đã hủy."; exit 0; }
fi

rm -f "$DEST_CMD"/kora-*.md 2>/dev/null || true
rm -rf "$DEST_CORE" 2>/dev/null || true
echo ""
echo "✅ Đã gỡ skill Kora."
echo ""
echo "Nếu bạn từng đặt token API, hãy XÓA TAY các dòng sau trong ~/.zshrc / ~/.bashrc:"
grep -nE '^export KORA_' "$HOME/.zshrc" "$HOME/.bashrc" 2>/dev/null || echo "  (không tìm thấy dòng KORA_ nào)"
pause
