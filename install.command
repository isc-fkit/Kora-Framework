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
[ -f "$SRC/CLAUDE.md" ] && cp "$SRC/CLAUDE.md" "$DEST_CORE/" || true
# version.json + CHANGELOG → để /claude-knowledge-version /claude-knowledge-update đọc được bản đã cài.
[ -f "$SRC/version.json" ] && cp "$SRC/version.json" "$DEST_CORE/" || true
[ -f "$SRC/CHANGELOG.md" ] && cp "$SRC/CHANGELOG.md" "$DEST_CORE/" || true
# Domain + rule preset đã nằm trong config/ vừa copy (gồm Healthcare/Y tế). Đếm để báo.
NDOM="$(ls -1 "$DEST_CORE"/config/domain-presets/*.md 2>/dev/null | wc -l | tr -d ' ')"
[ -f "$DEST_CORE/config/domain-presets/healthcare.md" ] || echo "⚠️  Thiếu preset Healthcare — nguồn cài có thể cũ."

# --- Resolve thư mục Downloads động (theo OS; tự fallback nếu không có) ---
DL_BASE="$HOME/Downloads"
if [ "$(uname -s 2>/dev/null)" = "Linux" ] && have xdg-user-dir; then
  _d="$(xdg-user-dir DOWNLOAD 2>/dev/null || true)"
  [ -n "$_d" ] && DL_BASE="$_d"
fi
[ -d "$DL_BASE" ] || DL_BASE="$HOME"   # Downloads không tồn tại → về home

# --- 3) Dựng ROOT Knowledge-Base trong Downloads + KHỞI TẠO project NGAY (folder skill BÊN TRONG) ---
ROOT="${KORA_PROJECT:-$DL_BASE/Knowledge-Base}"
SKILL_DIR="$ROOT/Skill"
echo "📦 Khởi tạo project tại: $ROOT"
mkdir -p "$SKILL_DIR"

# Folder skill nằm BÊN TRONG ROOT (để upload tay vào Cowork) — refresh mỗi lần cài/update.
rm -f "$SKILL_DIR"/kora-*.md "$SKILL_DIR"/claude-knowledge-*.md 2>/dev/null || true
cp "$DEST_CMD"/claude-knowledge-*.md "$SKILL_DIR"/ 2>/dev/null || true

# Khởi tạo cấu trúc project GỌN ngay trong ROOT — CHỈ khi chưa phải project Kora (tránh đè tri thức).
if [ ! -f "$ROOT/config/factory-config.yaml" ] && [ ! -d "$ROOT/config/domain-presets" ]; then
  echo "📁 Dựng cấu trúc project (docs/ + vault + config) bên trong $ROOT"
  mkdir -p "$ROOT"/docs/01-domain "$ROOT"/docs/02-product "$ROOT"/docs/03-features "$ROOT"/docs/04-design \
           "$ROOT"/docs/05-architecture "$ROOT"/docs/06-decisions "$ROOT"/docs/07-research "$ROOT"/docs/08-glossary \
           "$ROOT/inbox" "$ROOT/.kb" "$ROOT/config" "$ROOT/Kora_Brain/00_Index"
  [ -f "$DEST_CORE/config/factory-config.example.yaml" ] && cp "$DEST_CORE/config/factory-config.example.yaml" "$ROOT/config/factory-config.yaml"
  [ -d "$DEST_CORE/config/domain-presets" ] && cp -R "$DEST_CORE/config/domain-presets" "$ROOT/config/domain-presets"
  printf '@~/.claude/kora-framework/CLAUDE.md\n' > "$ROOT/CLAUDE.md"   # Cowork/CLI nạp rule orchestrator khi mở folder
  printf '# Knowledge Base\n' > "$ROOT/Kora_Brain/00_Index/Knowledge-Base.md"
fi

# (Dọn folder Kora-Skills kiểu cũ nếu còn sót từ bản trước)
rm -rf "$DL_BASE/Kora-Skills" "$DL_BASE/Kora-Skills.zip" 2>/dev/null || true

VER="$(grep -E '"version"' "$DEST_CORE/version.json" 2>/dev/null | head -n1 | sed -E 's/.*"version"[^"]*"([^"]*)".*/\1/')"
echo ""
echo "✅ Đã cài Kora-Framework ${VER:+v$VER} — $N skill + $NDOM domain preset (gồm Healthcare/Y tế, Retail, Manufacturing…) vào ~/.claude."
echo "   📁 Project đã khởi tạo sẵn: $ROOT"
echo "   📁 Folder skill (upload vào Cowork): $SKILL_DIR"
echo "   • Claude Code (CLI): mở  $ROOT  → gõ  /claude-knowledge-init  (đặt domain/tên) rồi  /claude-knowledge-scan."
echo "   • Claude Cowork (App): upload các file claude-knowledge-*.md trong  $SKILL_DIR/  vào mục Skills → mở  $ROOT  → gõ /claude-knowledge-init."
echo "   Cập nhật: chạy lại file này → skill mới tự kéo vào ~/.claude VÀ $SKILL_DIR/ (tri thức GIỮ NGUYÊN)."
echo "   Gỡ:       chạy uninstall.command (hoặc /claude-knowledge-uninstall)."
echo ""
echo "   💡 (Tùy chọn) Quét nguồn NỘI BỘ (Jira Server self-host…) THẲNG trong Cowork không cần Terminal?"
echo "      → Thoát hẳn Claude Desktop (Cmd+Q) rồi chạy:"
echo "          bash \"$DEST_CORE/tools/kora-mcp/setup_macos.command\""
echo "      (bật MCP local-terminal — chạy lệnh local ngoài sandbox; opt-in, chỉ Claude Desktop). Bỏ qua nếu chỉ dùng nguồn Cloud/MCP."
pause
