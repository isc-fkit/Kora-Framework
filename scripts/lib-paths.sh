#!/usr/bin/env bash
# lib-paths.sh — thư viện đường dẫn dùng chung cho các script update/export/import.
# Được "source" bởi update.command / export-kb.command / import-kb.command.
# TUYỆT ĐỐI không hardcode đường dẫn tuyệt đối — mọi thứ suy ra từ vị trí file này.

# repo_root: trả về thư mục gốc repo (cha của scripts/).
# Suy ra từ vị trí file lib-paths.sh (nằm trong scripts/), KHÔNG phụ thuộc cwd.
repo_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd
}

# REPO_ROOT — tính sẵn 1 lần để các script dùng lại.
REPO_ROOT="$(repo_root)"

# vault_dir: đọc 'vault_path:' từ config/factory-config.yaml.
# Vault có tên động (vd FMC-Knowledge-Base_Brain) nên không thể đưa vào mảng tĩnh.
# Fallback "Project_Name_Brain" nếu không đọc được config.
vault_dir() {
  local cfg="$REPO_ROOT/config/factory-config.yaml"
  local v=""
  if [ -f "$cfg" ]; then
    # Lấy dòng 'vault_path:' (đầu tiên), cắt phần sau dấu ':', bỏ comment + khoảng trắng + nháy.
    v="$(grep -E '^[[:space:]]*vault_path:' "$cfg" | head -n1 \
        | sed -E 's/^[[:space:]]*vault_path:[[:space:]]*//; s/#.*$//; s/^["'\'']//; s/["'\'']$//' \
        | sed -E 's/[[:space:]]+$//')"
  fi
  if [ -z "$v" ]; then
    v="Project_Name_Brain"
  fi
  printf '%s' "$v"
}

# project_name: đọc 'project_name:' từ config (để đặt tên file export). Fallback "project".
project_name() {
  local cfg="$REPO_ROOT/config/factory-config.yaml"
  local p=""
  if [ -f "$cfg" ]; then
    p="$(grep -E '^[[:space:]]*project_name:' "$cfg" | head -n1 \
        | sed -E 's/^[[:space:]]*project_name:[[:space:]]*//; s/#.*$//; s/^["'\'']//; s/["'\'']$//' \
        | sed -E 's/[[:space:]]+$//')"
  fi
  if [ -z "$p" ]; then
    p="project"
  fi
  printf '%s' "$p"
}

# read_version: đọc trường "version" từ version.json (không cần jq). Fallback "0.0.0".
read_version() {
  local vf="$REPO_ROOT/version.json"
  local ver=""
  if [ -f "$vf" ]; then
    ver="$(grep -E '"version"[[:space:]]*:' "$vf" | head -n1 \
        | sed -E 's/.*"version"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')"
  fi
  if [ -z "$ver" ]; then
    ver="0.0.0"
  fi
  printf '%s' "$ver"
}

# DATA_PATHS — các đường dẫn DATA (tri thức của user) TƯƠNG ĐỐI so với repo root.
# Đây là phần GIỮ NGUYÊN khi update và ĐÓNG GÓI khi export.
# LƯU Ý: vault KHÔNG nằm trong mảng này (tên động) — lấy riêng qua vault_dir().
DATA_PATHS=(
  ".kb/index.json"
  ".kb/relation-graph.json"
  ".kb/source-registry.json"
  ".kb/health-report.md"
  ".kb/changelog.md"
  ".kb/lessons.md"
  "docs/01-domain"
  "docs/02-product"
  "docs/03-features"
  "docs/04-design"
  "docs/05-architecture"
  "docs/06-decisions"
  "docs/08-glossary"
  "inbox"
  "reports"
  "config/factory-config.yaml"
  "config/domain-rules.md"
)

# data_env_files: liệt kê các file .env* trong tools/jira-to-obsidian (TRỪ .env.example),
# in ra dạng đường dẫn tương đối repo root, mỗi dòng 1 file. Có thể rỗng.
data_env_files() {
  local dir="$REPO_ROOT/tools/jira-to-obsidian"
  [ -d "$dir" ] || return 0
  local f base
  for f in "$dir"/.env*; do
    [ -e "$f" ] || continue
    base="$(basename "$f")"
    [ "$base" = ".env.example" ] && continue
    printf '%s\n' "tools/jira-to-obsidian/$base"
  done
}

# confluence_env_files: liệt kê .env* trong tools/confluence-sync (TRỪ .env.example),
# in ra đường dẫn tương đối repo root. Dùng khi HOST export/dời máy để giữ creds Confluence.
# ⚠️ archive-kb.command KHÔNG dùng hàm này (chỉ ship 1 file read-only riêng) — chỉ export/dời-máy mới gói.
confluence_env_files() {
  local dir="$REPO_ROOT/tools/confluence-sync"
  [ -d "$dir" ] || return 0
  local f base
  for f in "$dir"/.env*; do
    [ -e "$f" ] || continue
    base="$(basename "$f")"
    [ "$base" = ".env.example" ] && continue
    printf '%s\n' "tools/confluence-sync/$base"
  done
}

# archive_root: thư mục ghi gói archive (= repo root, giống export-kb). Tách hàm để dễ đổi sau.
archive_root() {
  printf '%s' "$REPO_ROOT"
}

# read_manifest_field <đường dẫn manifest.json> <tên field>
# Đọc 1 field chuỗi/giá-trị-đơn ở manifest.json mà KHÔNG cần jq. Rỗng nếu không thấy.
read_manifest_field() {
  local mf="$1" key="$2"
  [ -f "$mf" ] || return 0
  grep -E "\"$key\"[[:space:]]*:" "$mf" | head -n1 \
    | sed -E "s/.*\"$key\"[[:space:]]*:[[:space:]]*\"?([^\",}]*)\"?.*/\1/" \
    | sed -E 's/[[:space:]]+$//'
}

# self_dequarantine: gỡ nhãn ẩn 'com.apple.quarantine' mà macOS dán cho file tải từ web.
# Mục đích: sau khi user "Open Anyway" 1 file .command ở lần đầu, các script CÒN LẠI sẽ
# KHÔNG bị Gatekeeper hỏi nữa ở những lần double-click sau (chỉ cần vượt 1 lần duy nhất).
# An toàn: chỉ xoá một metadata "tải từ web", không đụng nội dung file. Chỉ chạy trên macOS.
# Luôn nuốt lỗi để không bao giờ làm script dừng (kể cả khi đang 'set -e').
self_dequarantine() {
  [ "$(uname -s 2>/dev/null)" = "Darwin" ] || return 0          # chỉ macOS
  command -v xattr >/dev/null 2>&1 || return 0
  local target="$REPO_ROOT/scripts"
  [ -d "$target" ] || return 0
  # Chỉ gỡ (và chỉ in) khi thực sự còn nhãn — tránh in thừa ở mỗi lần chạy.
  if xattr -lr "$target" 2>/dev/null | grep -q "com.apple.quarantine"; then
    xattr -dr com.apple.quarantine "$target" >/dev/null 2>&1 || true
    echo "🔓 Đã gỡ nhãn cảnh báo của macOS cho các script — lần sau double-click chạy thẳng, không bị hỏi lại."
    echo ""
  fi
}
