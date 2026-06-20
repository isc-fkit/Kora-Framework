#!/usr/bin/env bash
# schedule.command — wrapper gọi tools/kora-scheduler/schedule.py (lịch cấp HĐH macOS/Linux).
# Dùng: ./scripts/schedule.command register --id daily --cron "0 8 * * 1-5" --scan jira:local --post confluence:KB
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$DIR/lib-paths.sh"
self_dequarantine
PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || { echo "❌ Cần Python 3 (python3)."; exit 1; }
exec "$PY" "$REPO_ROOT/tools/kora-scheduler/schedule.py" "$@"
