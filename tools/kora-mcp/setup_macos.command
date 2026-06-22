#!/bin/bash
# setup_macos.command — Gắn MCP `local-terminal` vào Claude Desktop (macOS) một cách AN TOÀN.
# Chạy: bash "tools/kora-mcp/setup_macos.command"   (hoặc qua run_command nếu đã có MCP)
#
# ⚠️ PHẢI chạy khi Claude Desktop ĐÃ THOÁT (Cmd+Q) — vì app ghi đè config lúc thoát, sửa khi đang
#    chạy sẽ mất. Script này TỪ CHỐI chạy nếu phát hiện Claude đang mở.
set -euo pipefail

CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
SERVER="$HOME/.claude/kora-framework/tools/kora-mcp/local_terminal_mcp.py"
# Bản dev (chạy từ repo) → dùng server cạnh script này nếu bản cài chưa có.
[ -f "$SERVER" ] || SERVER="$(cd "$(dirname "$0")" && pwd)/local_terminal_mcp.py"

if pgrep -x Claude >/dev/null 2>&1; then
  echo "⚠️  Claude Desktop ĐANG CHẠY → hãy Cmd+Q thoát hẳn rồi chạy lại script này (app ghi đè config khi thoát)."
  exit 1
fi
[ -f "$SERVER" ] || { echo "❌ Không thấy MCP server: $SERVER (cài/cập nhật framework trước)."; exit 1; }
PYBIN="$(command -v python3)" || { echo "❌ Không thấy python3."; exit 1; }

mkdir -p "$(dirname "$CFG")"
[ -f "$CFG" ] && cp "$CFG" "$CFG.bak-$(date +%Y%m%d%H%M%S)" && echo "🗂  backup: $CFG.bak-*"

CFG="$CFG" SERVER="$SERVER" PYBIN="$PYBIN" python3 - <<'PY'
import json, os
p = os.environ["CFG"]
d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
d.setdefault("mcpServers", {})["local-terminal"] = {"command": os.environ["PYBIN"], "args": [os.environ["SERVER"]]}
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2); open(p, "a").write("\n")
print("✅ Đã thêm mcpServers.local-terminal →", os.environ["SERVER"])
PY

cat <<EOF

✅ Xong. Tiếp theo:
  1. Đặt token nguồn API/Server vào ~/.zshrc (vd Jira Server):
       export JIRA_BASE_URL="https://jira.cong-ty.vn"
       export JIRA_AUTH_MODE="server"
       export JIRA_PAT="<PAT của bạn>"
     (run_command tự source ~/.zshrc mỗi lần → đổi token KHÔNG cần restart.)
  2. Mở Claude Desktop → tool 'run_command' sẵn sàng trong Cowork.
  3. Test: "dùng run_command chạy: whoami && echo \$JIRA_BASE_URL"
EOF
