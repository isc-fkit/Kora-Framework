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
  # ⚠️ TRÁNH CACHE CŨ: archive theo NHÁNH (refs/heads/<ref>.tar.gz) bị CDN của GitHub cache rất dai →
  # cài nhầm bản cũ dù đã phát hành bản mới. Cách chuẩn: hỏi API SHA commit MỚI NHẤT của nhánh, rồi tải
  # archive theo SHA (immutable, không bao giờ cache cũ). Fallback về archive nhánh nếu API bị giới hạn.
  SHA="$(curl -fsSL -H 'Accept: application/vnd.github.sha' "https://api.github.com/repos/$REPO/commits/$REF" 2>/dev/null || true)"
  if printf '%s' "$SHA" | grep -qiE '^[0-9a-f]{40}$'; then
    DL_URL="https://github.com/$REPO/archive/$SHA.tar.gz"; echo "   (bản mới nhất: ${SHA:0:7})"
  else
    DL_URL="https://github.com/$REPO/archive/refs/heads/$REF.tar.gz"
  fi
  curl -fsSL "$DL_URL" -o "$TMP/src.tgz" \
    || die "Tải thất bại. Kiểm tra mạng rồi thử lại."
  tar -xzf "$TMP/src.tgz" -C "$TMP" || die "Giải nén thất bại."
  SRC="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -n1)"
  [ -n "$SRC" ] && [ -d "$SRC" ] || die "Không thấy thư mục nguồn sau giải nén."
fi

# --- 1) Skills → ~/.claude/commands/ (xóa kora-* CŨ + claude-knowledge-* để cài lại sạch — migration đổi tên) ---
echo "📥 Cài lệnh /claude-knowledge-* ..."
rm -f "$DEST_CMD"/kora-*.md "$DEST_CMD"/claude-knowledge-*.md 2>/dev/null || true
cp "$SRC"/.claude/commands/claude-knowledge-*.md "$DEST_CMD"/ 2>/dev/null || die "Không thấy skill claude-knowledge-*.md trong nguồn."
# Skill CHỈ-DUY-TRÌ (maintainer-only) — KHÔNG cài cho người dùng thường (phát hành = chỉ người viết repo).
for ms in claude-knowledge-release; do rm -f "$DEST_CMD/$ms.md" 2>/dev/null || true; done
N="$(ls -1 "$DEST_CMD"/claude-knowledge-*.md 2>/dev/null | wc -l | tr -d ' ')"

# --- 2) CORE hỗ trợ → ~/.claude/kora-framework/ (ẩn, quản lý; KHÔNG phải folder source để sửa) ---
echo "📥 Cài workflows hỗ trợ ..."
for d in workflows scripts templates config tools assets; do
  if [ -e "$SRC/$d" ]; then
    rm -rf "$DEST_CORE/$d" 2>/dev/null || true
    cp -R "$SRC/$d" "$DEST_CORE/$d"
  fi
done
# Workflow CHỈ-DUY-TRÌ — gỡ khỏi bản cài người dùng (phát hành/tiến hóa hệ thống chỉ ở người viết repo).
for mw in 12-release.md 13-evolve-system.md; do rm -f "$DEST_CORE/workflows/$mw" 2>/dev/null || true; done
# MIGRATION: dọn skill /kora-* CŨ kẹt trong CORE (orphan từ bản cài cũ — đã đổi tên → /claude-knowledge-*) để không lẫn skill.
rm -f "$DEST_CORE/.claude/commands"/kora-*.md 2>/dev/null || true
[ -f "$SRC/CLAUDE.md" ] && cp "$SRC/CLAUDE.md" "$DEST_CORE/" || true
# CORE phụ (cho refresh bundle project): .kb/rules.md + system-lessons.md + docs/07-research — KHÔNG phải DATA user.
mkdir -p "$DEST_CORE/.kb" 2>/dev/null || true
[ -f "$SRC/.kb/rules.md" ] && cp "$SRC/.kb/rules.md" "$DEST_CORE/.kb/" 2>/dev/null || true
[ -f "$SRC/.kb/system-lessons.md" ] && cp "$SRC/.kb/system-lessons.md" "$DEST_CORE/.kb/" 2>/dev/null || true
[ -d "$SRC/docs/07-research" ] && { mkdir -p "$DEST_CORE/docs" 2>/dev/null; rm -rf "$DEST_CORE/docs/07-research" 2>/dev/null; cp -R "$SRC/docs/07-research" "$DEST_CORE/docs/07-research" 2>/dev/null; } || true
# version.json + CHANGELOG → để /claude-knowledge-version /claude-knowledge-update đọc được bản đã cài.
[ -f "$SRC/version.json" ] && cp "$SRC/version.json" "$DEST_CORE/" || true
[ -f "$SRC/CHANGELOG.md" ] && cp "$SRC/CHANGELOG.md" "$DEST_CORE/" || true
# Domain + rule preset đã nằm trong config/ vừa copy (gồm Healthcare/Y tế). Đếm để báo.
NDOM="$(ls -1 "$DEST_CORE"/config/domain-presets/*.md 2>/dev/null | wc -l | tr -d ' ')"
[ -f "$DEST_CORE/config/domain-presets/healthcare.md" ] || echo "⚠️  Thiếu preset Healthcare — nguồn cài có thể cũ."

# --- 3) Folder SKILL (để upload vào Cowork) — DYNAMIC PATH, KHÔNG đổ rác vào Downloads ---
# Mặc định đặt CẠNH CORE: ~/.claude/kora-framework/Skill (theo $HOME, ổn định, không rải file vào Downloads).
# Muốn để trong 1 project cụ thể → đặt biến KORA_PROJECT=<đường dẫn project> trước khi cài.
# KHÔNG tự scaffold project nữa: init (/claude-knowledge-init, workflow 00 Bước 0) tự dựng docs/vault/config ở FOLDER user mở (bất kỳ đâu).
if [ -n "${KORA_PROJECT:-}" ]; then SKILL_DIR="$KORA_PROJECT/Skill"; else SKILL_DIR="$DEST_CORE/Skill"; fi
mkdir -p "$SKILL_DIR"
rm -f "$SKILL_DIR"/kora-*.md 2>/dev/null || true            # dọn skill /kora-* CŨ (đã đổi tên)
rm -f "$SKILL_DIR"/claude-knowledge-*.md 2>/dev/null || true
cp "$DEST_CMD"/claude-knowledge-*.md "$SKILL_DIR"/ 2>/dev/null || true

# Đăng ký PROJECT vào registry + đồng bộ bundle (CLAUDE.md + merge config keys mới) → update sau luôn refresh đúng project.
if [ -n "${KORA_PROJECT:-}" ] && [ -d "$KORA_PROJECT" ]; then
  REG="${XDG_CONFIG_HOME:-$HOME/.config}/claude-knowledge/projects.list"
  KP="$(cd "$KORA_PROJECT" && pwd)"
  mkdir -p "$(dirname "$REG")" 2>/dev/null || true; touch "$REG" 2>/dev/null || true
  grep -qxF "$KP" "$REG" 2>/dev/null || printf '%s\n' "$KP" >> "$REG"
  [ -f "$KP/CLAUDE.md" ] && [ -f "$DEST_CORE/CLAUDE.md" ] && cp "$DEST_CORE/CLAUDE.md" "$KP/CLAUDE.md" 2>/dev/null || true
  if [ -f "$KP/config/factory-config.yaml" ] && [ -f "$DEST_CORE/tools/config-merge/merge_config.py" ] && have python3; then
    python3 "$DEST_CORE/tools/config-merge/merge_config.py" --user "$KP/config/factory-config.yaml" --example "$DEST_CORE/config/factory-config.example.yaml" --write --quiet 2>/dev/null || true
  fi
fi

# Dọn RÁC bản cũ ở Downloads (KHÔNG tạo mới ở Downloads): folder Kora-Skills + folder Skill kiểu cũ.
rm -rf "$HOME/Downloads/Kora-Skills" "$HOME/Downloads/Kora-Skills.zip" 2>/dev/null || true
rm -rf "$HOME/Downloads/Knowledge-Base/Skill" "$HOME/Downloads/Knowledge-Base/skill" 2>/dev/null || true

VER="$(grep -E '"version"' "$DEST_CORE/version.json" 2>/dev/null | head -n1 | sed -E 's/.*"version"[^"]*"([^"]*)".*/\1/')"
echo ""
echo "✅ Đã cài Kora-Framework ${VER:+v$VER} — $N skill + $NDOM domain preset (gồm Healthcare/Y tế, Retail, Manufacturing…) vào ~/.claude."
echo "   📁 Folder skill (upload vào Cowork): $SKILL_DIR"
echo "   • Claude Code (CLI): mở FOLDER PROJECT của bạn (bất kỳ đâu) → gõ  /claude-knowledge-init  (tự dựng project + đặt domain) rồi  /claude-knowledge-scan."
echo "   • Claude Cowork (App): upload các file claude-knowledge-*.md trong  $SKILL_DIR/  vào mục Skills → mở project của bạn → gõ /claude-knowledge-init."
echo "   Cập nhật: chạy lại file này → skill mới tự kéo vào ~/.claude VÀ $SKILL_DIR/ (tri thức GIỮ NGUYÊN, KHÔNG tạo rác ở Downloads)."
echo "   Gỡ:       chạy uninstall.command (hoặc /claude-knowledge-uninstall)."
echo ""
echo "   💡 (Tùy chọn) Quét nguồn NỘI BỘ (Jira Server self-host…) THẲNG trong Cowork không cần Terminal?"
echo "      → Thoát hẳn Claude Desktop (Cmd+Q) rồi chạy:"
echo "          bash \"$DEST_CORE/tools/kora-mcp/setup_macos.command\""
echo "      (bật MCP local-terminal — chạy lệnh local ngoài sandbox; opt-in, chỉ Claude Desktop). Bỏ qua nếu chỉ dùng nguồn Cloud/MCP."
pause
