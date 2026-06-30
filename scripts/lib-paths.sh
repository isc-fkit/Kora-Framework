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

# ── REGISTRY + PROJECT-BUNDLE REFRESH (update đồng bộ HOÀN TOÀN, không partial) ──────────────
# registry_file: file liệt kê các DATA-PROJECT user mở (mỗi project có bundle CORE riêng: CLAUDE.md +
# Skill/ + config). update refresh các project này để Cowork luôn có tính năng mới (không "lúc có lúc mất").
registry_file() {
  printf '%s' "${XDG_CONFIG_HOME:-$HOME/.config}/claude-knowledge/projects.list"
}

# register_project <path>: thêm project vào registry (dedupe). Chỉ ghi nếu trông giống project Kora.
register_project() {
  local p="${1:-}"
  [ -n "$p" ] || return 0
  p="$(cd "$p" 2>/dev/null && pwd || echo "")"; [ -n "$p" ] || return 0
  [ -f "$p/config/factory-config.yaml" ] || [ -f "$p/CLAUDE.md" ] || [ -d "$p/Skill" ] || return 0
  local rf; rf="$(registry_file)"
  mkdir -p "$(dirname "$rf")" 2>/dev/null || true
  touch "$rf" 2>/dev/null || return 0
  grep -qxF "$p" "$rf" 2>/dev/null || printf '%s\n' "$p" >> "$rf"
}

# refresh_project_bundle <project_dir> <core_dir> <global_cmd>: đồng bộ phần CORE BUNDLE trong 1 project
# (Skill/ + CLAUDE.md + .kb/rules.md + .kb/system-lessons.md + docs/07-research + MERGE config) — DATA GIỮ NGUYÊN.
refresh_project_bundle() {
  local proj="${1:-}" core="${2:-}" gcmd="${3:-}"
  [ -d "$proj" ] || return 0
  # Skill/ (Cowork upload) — refresh claude-knowledge-* (gỡ maintainer + kora-* cũ). find -delete: an toàn mọi shell.
  if [ -d "$proj/Skill" ] && [ -d "$gcmd" ]; then
    find "$proj/Skill" -maxdepth 1 -type f \( -name 'kora-*.md' -o -name 'claude-knowledge-*.md' \) -delete 2>/dev/null || true
    cp "$gcmd"/claude-knowledge-*.md "$proj/Skill"/ 2>/dev/null || true
    rm -f "$proj/Skill/claude-knowledge-release.md" 2>/dev/null || true
  fi
  # CLAUDE.md (Cowork đọc từ project) — chỉ khi project bundle sẵn có
  [ -f "$proj/CLAUDE.md" ] && [ -f "$core/CLAUDE.md" ] && cp "$core/CLAUDE.md" "$proj/CLAUDE.md" 2>/dev/null || true
  # .kb CORE (rules + system-lessons) — KHÔNG phải DATA của user
  if [ -d "$proj/.kb" ]; then
    [ -f "$core/.kb/rules.md" ] && cp "$core/.kb/rules.md" "$proj/.kb/rules.md" 2>/dev/null || true
    [ -f "$core/.kb/system-lessons.md" ] && cp "$core/.kb/system-lessons.md" "$proj/.kb/system-lessons.md" 2>/dev/null || true
  fi
  # (KHÔNG đụng docs/07-research trong project — tránh rm -rf nhầm file user nếu họ để dữ liệu ở đó;
  #  07-research chỉ refresh ở managed CORE, project đọc fallback từ đó khi cần.)
  # MERGE config keys mới (giữ nguyên giá trị user) — tránh "tính năng mới thiếu config → lỗi"
  if [ -f "$proj/config/factory-config.yaml" ] && [ -f "$core/config/factory-config.example.yaml" ] \
     && [ -f "$core/tools/config-merge/merge_config.py" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$core/tools/config-merge/merge_config.py" \
      --user "$proj/config/factory-config.yaml" \
      --example "$core/config/factory-config.example.yaml" --write --quiet 2>/dev/null || true
  fi
}

# discover_kora_projects [managed_core]: in ra MỌI DATA-PROJECT Kora khả dĩ để update tự fix (KHÔNG cần
# đăng ký tay từng máy). Nguồn: registry + cwd + ~/Desktop + ~/Documents. Nhận diện CHẶT để tránh đè nhầm:
# phải có config/factory-config.yaml VÀ (.kb/ HOẶC Skill/ HOẶC vault *_Brain/). Loại .maintainer + managed CORE.
discover_kora_projects() {
  local skip_core="${1:-}"
  local rf; rf="$(registry_file)"
  {
    [ -f "$rf" ] && cat "$rf" 2>/dev/null
    local r
    for r in "$PWD" "$HOME/Desktop" "$HOME/Documents"; do
      [ -d "$r" ] || continue
      # prune thư mục nặng/không liên quan để find KHÔNG treo trên cây lớn.
      find "$r" -maxdepth 4 \
        \( -name node_modules -o -name '.git' -o -name 'Library' -o -name '.Trash' -o -name '*_Brain' \) -prune -o \
        -type f -path '*/config/factory-config.yaml' -print 2>/dev/null \
        | while IFS= read -r cf; do dirname "$(dirname "$cf")"; done
    done
  } 2>/dev/null | while IFS= read -r d; do
      [ -n "$d" ] || continue
      d="$(cd "$d" 2>/dev/null && pwd || echo "")"; [ -n "$d" ] || continue
      [ -f "$d/.maintainer" ] && continue
      [ -n "$skip_core" ] && [ "$d" = "$skip_core" ] && continue
      [ -f "$d/config/factory-config.yaml" ] || continue
      if [ -d "$d/.kb" ] || [ -d "$d/Skill" ] || ls -d "$d"/*_Brain >/dev/null 2>&1; then
        printf '%s\n' "$d"
      fi
    done | sort -u
}

# reconcile_projects <core> <global_cmd>: TỰ phát hiện + đăng ký + refresh bundle CORE cho MỌI project Kora.
# In ra SỐ project đã đồng bộ. Mấu chốt "update 1 LẦN fix hết root-cause" cho máy cũ chưa đăng ký.
reconcile_projects() {
  local core="${1:-}" gcmd="${2:-}" n=0 p
  while IFS= read -r p; do
    [ -n "$p" ] && [ -d "$p" ] || continue
    register_project "$p"
    refresh_project_bundle "$p" "$core" "$gcmd"
    n=$((n + 1))
  done < <(discover_kora_projects "$core")
  printf '%s' "$n"
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
  # Đếm bằng grep -c (đọc HẾT input → KHÔNG gây SIGPIPE cho xattr dưới 'set -o pipefail'); || true cho count 0.
  local marks
  marks="$(xattr -lr "$target" 2>/dev/null | grep -c "com.apple.quarantine" 2>/dev/null || true)"
  if [ "${marks:-0}" != "0" ]; then
    xattr -dr com.apple.quarantine "$target" >/dev/null 2>&1 || true
    echo "🔓 Đã gỡ nhãn cảnh báo của macOS cho các script — lần sau double-click chạy thẳng, không bị hỏi lại."
    echo ""
  fi
}
