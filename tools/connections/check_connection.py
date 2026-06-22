#!/usr/bin/env python3
"""
check_connection.py — Đọc SỔ ĐĂNG KÝ kết nối (config/factory-config.yaml > connections)
và kiểm tra trạng thái từng nguồn. Helper dùng chung cho /kora-connect, /kora-scan, /kora-schedule.

KHÔNG in token ra log. Chỉ dùng thư viện chuẩn Python 3.

Ví dụ:
  python3 tools/connections/check_connection.py --list
  python3 tools/connections/check_connection.py --check jira_cloud__api
  # Windows: thay python3 bằng py

Quy tắc:
  - Nguồn API (jira_server|jira_cloud|github|gitlab) → gọi thử HTTP probe (đọc creds từ env/.env),
    in OK/❌ + 1 dòng JSON {id,status,last_checked,last_error} để skill GHI ngược vào YAML.
  - Nguồn MCP → KHÔNG probe được bằng Python (phải gọi MCP tool) → in status=needs_model_probe
    để skill tự gọi MCP tool rồi ghi lại trạng thái.
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
CONFIG = REPO_ROOT / "config" / "factory-config.yaml"   # fallback bản dev (tool nằm trong repo)
TIMEOUT = 30


def resolve_config(arg: str = "") -> Path:
    """Chọn factory-config.yaml ĐÚNG project. Tool có thể chạy từ CORE (~/.claude/kora-framework/tools)
    cho 1 project ở thư mục khác → KHÔNG được đọc CORE config. Ưu tiên tồn-tại-đầu-tiên:
    --config → cwd/config/factory-config.yaml (PROJECT — /kora-connect chạy ở thư mục project) → REPO_ROOT (dev)."""
    cands = []
    if arg:
        cands.append(Path(arg).expanduser())
    cands.append(Path.cwd() / "config" / "factory-config.yaml")
    cands.append(CONFIG)
    for p in cands:
        if p.exists():
            return p
    return cands[0]   # không cái nào tồn tại → trả candidate đầu để thông báo hợp lý


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_env(path: Path) -> dict:
    env = {}
    if path and path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def _scalar(v: str):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
    return v.strip('"').strip("'")


def parse_connections(path: Path):
    """Đọc block 'connections:' → list các dict phẳng (key->value, last-wins).
    Hỗ trợ inline map {k: v, ...} và inline list [a, b]. Đủ cho các entry kết nối."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    # tìm dòng 'connections:'
    start = None
    for idx, ln in enumerate(lines):
        if re.match(r"^connections:\s*(#.*)?$", ln.strip()) or ln.strip().startswith("connections:"):
            start = idx
            # 'connections: []' → rỗng
            after = ln.split(":", 1)[1].strip()
            if after.startswith("[]"):
                return []
            break
    if start is None:
        return []

    entries, cur = [], None
    for ln in lines[start + 1:]:
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        indent = len(ln) - len(ln.lstrip(" "))
        if indent == 0:  # hết block connections
            break
        body = ln.strip()
        if body.startswith("- "):
            if cur is not None:
                entries.append(cur)
            cur = {}
            body = body[2:].strip()
        if cur is None:
            cur = {}
        if ":" not in body:
            continue
        key, _, val = body.partition(":")
        key, val = key.strip(), val.strip()
        if val.startswith("{") and val.endswith("}"):     # inline map
            for part in val[1:-1].split(","):
                if ":" in part:
                    k2, _, v2 = part.partition(":")
                    cur[k2.strip()] = _scalar(v2)
        elif val == "":                                    # block con (creds:/verify:/oauth:)
            continue                                        # con sẽ được gộp phẳng ở dòng kế
        else:
            cur[key] = _scalar(val)
    if cur:
        entries.append(cur)
    return entries


def http_get(url: str, headers: dict):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read()


def resolve_token(entry: dict):
    """Trả về (token, email) từ env var hoặc file .env mà entry trỏ tới (KHÔNG in ra)."""
    keys = entry.get("env_keys") or []
    if isinstance(keys, str):
        keys = [keys]
    dotenv = entry.get("dotenv_path")
    src = load_env(REPO_ROOT / dotenv) if dotenv else {}

    def pick(name):
        return os.getenv(name) or src.get(name)

    token = email = None
    for k in keys:
        if "EMAIL" in k.upper():
            email = pick(k)
        elif token is None:
            token = pick(k)
    # fallback tên phổ biến
    token = token or pick("JIRA_PAT") or pick("KORA_GITHUB_TOKEN") or pick("KORA_GITLAB_TOKEN")
    email = email or pick("JIRA_EMAIL")
    return token, email


def probe_api(entry: dict):
    st = entry.get("source_type", "")
    base = (entry.get("base_url") or "").rstrip("/")
    if st == "sharepoint":
        # Token Graph lấy động (client-credentials / device-flow) → ủy quyền cho tool --check.
        tool = REPO_ROOT / "tools" / "sharepoint-sync" / "sync_sharepoint.py"
        if not tool.exists():
            return "error", "Thiếu tools/sharepoint-sync (chưa cài tool SharePoint)."
        try:
            p = subprocess.run([sys.executable, str(tool), "--check"],
                               capture_output=True, text=True, timeout=60)
        except Exception as e:  # noqa: BLE001
            return "error", str(e)[:200]
        return ("connected", "") if p.returncode == 0 else ("error", (p.stderr or p.stdout).strip()[-200:])
    probe = entry.get("probe") or {
        "jira_server": "/rest/api/2/myself", "jira_cloud": "/rest/api/2/myself",
        "github": "/user", "gitlab": "/user", "confluence": "/rest/api/user/current",
    }.get(st, "/")
    # 'verify: { probe: "GET /rest/..." }' → tách phần path
    probe = probe.replace("GET ", "").strip()
    token, email = resolve_token(entry)
    if not token:
        return "error", "Thiếu token (chưa set env var / .env). Chạy /kora-connect."
    if not base:
        return "error", "Thiếu base_url trong entry."

    headers = {"Accept": "application/json"}
    if st == "jira_cloud" and email:
        headers["Authorization"] = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
    elif st in ("jira_server", "confluence"):
        headers["Authorization"] = f"Bearer {token}"
    elif st == "github":
        headers["Authorization"] = f"Bearer {token}"
    elif st == "gitlab":
        headers["PRIVATE-TOKEN"] = token
    else:
        headers["Authorization"] = f"Bearer {token}"

    try:
        code, _ = http_get(base + probe, headers)
        return ("connected", "") if 200 <= code < 300 else ("error", f"HTTP {code}")
    except urllib.error.HTTPError as e:
        return "error", f"HTTP {e.code} (token sai/hết hạn hoặc thiếu quyền)"
    except urllib.error.URLError as e:
        return "error", f"network: {e.reason}"


def _gh_api(base: str) -> str:
    """Base API GitHub: github.com → api.github.com; Enterprise <host> → <host>/api/v3."""
    base = (base or "").rstrip("/")
    if not base or base in ("https://github.com", "http://github.com"):
        return "https://api.github.com"
    if "api.github.com" in base:
        return base
    return base + "/api/v3"


def _gl_api(base: str) -> str:
    """Base API GitLab: <host> → <host>/api/v4 (mặc định gitlab.com)."""
    base = (base or "").rstrip("/") or "https://gitlab.com"
    return base if base.endswith("/api/v4") else base + "/api/v4"


def list_repos(entry: dict):
    """In JSON danh sách repo (GitHub) / project (GitLab) của 1 connection để skill cho user CHỌN.
    GitHub: GET /user/repos · GitLab: GET /projects?membership=true. Tái dùng resolve_token + http_get."""
    st = entry.get("source_type", "")
    token, _ = resolve_token(entry)
    if not token:
        print(json.dumps({"error": "Thiếu token (chưa set env var / .env). Chạy /kora-connect."}, ensure_ascii=False))
        sys.exit(1)
    base = entry.get("base_url") or ""
    try:
        if st == "github":
            url = (_gh_api(base) + "/user/repos?per_page=100&sort=updated"
                   "&affiliation=owner,collaborator,organization_member")
            _code, body = http_get(url, {"Accept": "application/vnd.github+json",
                                         "Authorization": f"Bearer {token}", "User-Agent": "kora-connect"})
            data = json.loads(body)
            out = [{"full_name": r.get("full_name"), "private": r.get("private"),
                    "default_branch": r.get("default_branch")} for r in data if isinstance(r, dict)]
        elif st == "gitlab":
            url = _gl_api(base) + "/projects?membership=true&per_page=100&order_by=last_activity_at&simple=true"
            _code, body = http_get(url, {"Accept": "application/json", "PRIVATE-TOKEN": token})
            data = json.loads(body)
            out = [{"path_with_namespace": r.get("path_with_namespace"), "id": r.get("id"),
                    "default_branch": r.get("default_branch")} for r in data if isinstance(r, dict)]
        else:
            print(json.dumps({"error": f"--list-repos chỉ hỗ trợ github/gitlab (source_type={st})"}, ensure_ascii=False))
            sys.exit(1)
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": f"HTTP {e.code} (token sai/hết hạn hoặc thiếu quyền)"}, ensure_ascii=False))
        sys.exit(1)
    except urllib.error.URLError as e:
        print(json.dumps({"error": f"network: {e.reason}"}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="Kiểm tra sổ kết nối Kora.")
    ap.add_argument("--list", action="store_true", help="In bảng các kết nối đã đăng ký.")
    ap.add_argument("--check", metavar="ID", help="Kiểm tra 1 kết nối theo id.")
    ap.add_argument("--list-repos", dest="list_repos", metavar="ID",
                    help="Liệt kê repo (GitHub) / project (GitLab) của connection <id> (JSON) để CHỌN.")
    ap.add_argument("--json", action="store_true", help="In JSON thay vì bảng (cho --list).")
    ap.add_argument("--config", default="", help="Đường dẫn factory-config.yaml (mặc định: config của "
                    "thư mục hiện tại = PROJECT). Cần khi tool chạy từ CORE cho project ở nơi khác.")
    args = ap.parse_args()

    conns = parse_connections(resolve_config(args.config))

    if args.list_repos:
        entry = next((c for c in conns if c.get("id") == args.list_repos), None)
        if not entry:
            print(json.dumps({"error": f"không tìm thấy id '{args.list_repos}' trong connections"}, ensure_ascii=False))
            sys.exit(1)
        list_repos(entry)
        return

    if args.list or (not args.check):
        if args.json:
            print(json.dumps(conns, ensure_ascii=False, indent=2))
            return
        if not conns:
            print("ℹ️  Chưa có kết nối nào. Chạy /kora-connect để thêm.")
            return
        print(f"{'ID':30} {'METHOD':6} {'SOURCE_TYPE':12} {'STATUS':11} BASE_URL / DOMAIN")
        for c in conns:
            print(f"{c.get('id','?'):30} {c.get('method','?'):6} {c.get('source_type','?'):12} "
                  f"{c.get('status','?'):11} {c.get('base_url','') or '-'}")
        return

    # --check <id>
    entry = next((c for c in conns if c.get("id") == args.check), None)
    if not entry:
        print(json.dumps({"id": args.check, "status": "error",
                          "last_error": "không tìm thấy id trong connections"}, ensure_ascii=False))
        sys.exit(1)

    if entry.get("method") == "mcp":
        print(json.dumps({"id": args.check, "status": "needs_model_probe",
                          "note": "Gọi MCP tool của connector để verify rồi ghi lại trạng thái.",
                          "verify_tool": entry.get("tool") or entry.get("connector")},
                         ensure_ascii=False))
        return

    status, err = probe_api(entry)
    result = {"id": args.check, "status": status, "last_checked": now_iso(), "last_error": err}
    if status == "connected":
        print(f"✅ {args.check}: kết nối OK")
    else:
        print(f"❌ {args.check}: {err}", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if status == "connected" else 1)


if __name__ == "__main__":
    main()
