#!/usr/bin/env python3
"""
check_connection.py — Đọc SỔ ĐĂNG KÝ kết nối (config/factory-config.yaml > connections)
và kiểm tra trạng thái từng nguồn. Helper dùng chung cho /claude-knowledge-connect, /claude-knowledge-scan, /claude-knowledge-schedule.

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
    --config → cwd/config/factory-config.yaml (PROJECT — /claude-knowledge-connect chạy ở thư mục project) → REPO_ROOT (dev)."""
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


def _proxy_opener():
    """Mạng công ty có thể chỉ cho CONNECT 443 qua proxy (KORA_HTTPS_PROXY = proxy riêng cho Kora,
    không đụng HTTPS_PROXY hệ thống). Ưu tiên: HTTPS_PROXY > https_proxy > KORA_HTTPS_PROXY.
    Không có biến nào → no-proxy tường minh (không để proxy hệ thống sai làm hỏng đường đi trực tiếp)."""
    proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or os.getenv("KORA_HTTPS_PROXY")
    proxy_handler = (urllib.request.ProxyHandler({"https": proxy_url, "http": proxy_url})
                     if proxy_url else urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(proxy_handler)


def http_get(url: str, headers: dict):
    req = urllib.request.Request(url, headers=headers, method="GET")
    with _proxy_opener().open(req, timeout=TIMEOUT) as r:
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

    # env_keys có thể liệt kê CẢ các biến không phải credential (BASE_URL, AUTH_MODE...) để tài
    # liệu hoá đủ biến mà tool scan (import_jira.py...) cần — KHÔNG được coi "phần tử đầu tiên
    # không phải EMAIL" là token, vì phần tử đó có thể là JIRA_BASE_URL. Chỉ nhận key có tên
    # khớp mẫu credential thật (PAT/TOKEN/SECRET/APIKEY/KEY/PASS).
    token_pat = re.compile(r"PAT|TOKEN|SECRET|API_?KEY|_KEY$|PASS", re.IGNORECASE)
    token = email = None
    for k in keys:
        ku = k.upper()
        if "EMAIL" in ku:
            email = pick(k)
        elif token is None and token_pat.search(ku):
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
    default_probe = {
        "jira_server": "/rest/api/2/myself", "jira_cloud": "/rest/api/2/myself",
        "github": "/user", "gitlab": "/user", "confluence": "/rest/api/user/current",
    }.get(st, "/")
    probe = entry.get("probe") or default_probe
    # 'verify: { probe: "GET /rest/..." }' → tách phần path
    probe = probe.replace("GET ", "").strip()
    if not probe.startswith("/"):
        # verify.probe trong config không phải HTTP path hợp lệ (vd lỡ ghi lệnh CLI
        # như "import_jira.py --test") → nối vào base_url sẽ ra URL vô nghĩa, dùng path mặc định.
        probe = default_probe
    token, email = resolve_token(entry)
    if not token:
        return "error", "Thiếu token (chưa set env var / .env). Chạy /claude-knowledge-connect."
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
        print(json.dumps({"error": "Thiếu token (chưa set env var / .env). Chạy /claude-knowledge-connect."}, ensure_ascii=False))
        sys.exit(1)
    base = entry.get("base_url") or ""
    try:
        if st == "github":
            url = (_gh_api(base) + "/user/repos?per_page=100&sort=updated"
                   "&affiliation=owner,collaborator,organization_member")
            _code, body = http_get(url, {"Accept": "application/vnd.github+json",
                                         "Authorization": f"Bearer {token}", "User-Agent": "claude-knowledge-connect"})
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


def mcp_probe_hint(source_type: str) -> str:
    """MCP tool nên gọi để verify 1 nguồn MCP (theo source_type). Skill/model dùng gợi ý này
    để probe ĐÚNG từng nguồn, không bỏ sót Gmail/M365 khi 'kiểm tra tất cả'."""
    return {
        "jira_cloud": "searchJiraIssuesUsingJql | getVisibleJiraProjects",
        "jira_server": "searchJiraIssuesUsingJql | getVisibleJiraProjects",
        "atlassian": "searchJiraIssuesUsingJql | getVisibleJiraProjects",
        "confluence": "searchConfluenceUsingCql",
        "sharepoint": "sharepoint_folder_search | sharepoint_search",
        "outlook": "outlook_email_search",
        "gmail": "list_drafts | list_labels",
        "m365": "sharepoint_folder_search | outlook_email_search",
    }.get(source_type, "gọi 1 MCP tool của connector để verify")


def verify_one(entry: dict) -> dict:
    """Verify 1 connection → dict {id, source_type, method, status, last_checked, last_error,
    [verify_tool|verify_cmd]}. Dùng cho --check-all (lặp MỌI nguồn, không chỉ Jira):
      - api (jira_*/github/gitlab/confluence) + sharepoint → probe THẬT (probe_api).
      - mcp → needs_model_probe + verify_tool (model phải tự gọi MCP tool).
      - gmail_smtp(smtp)/gmail_api(https) → needs_model_probe + verify_cmd (chạy send_report.py --check).
      - local_file (excel) → kiểm tra file tồn tại.
    """
    eid = entry.get("id", "?")
    st = entry.get("source_type", "")
    method = entry.get("method", "")
    res = {"id": eid, "source_type": st, "method": method,
           "last_checked": now_iso(), "last_error": ""}
    if method == "mcp":
        res.update(status="needs_model_probe",
                   verify_tool=entry.get("tool") or entry.get("connector") or mcp_probe_hint(st),
                   note="Gọi MCP tool của connector để verify.")
        return res
    if st == "gmail_smtp" or method == "smtp":
        res.update(status="needs_model_probe",
                   verify_cmd="report-mailer/send_report.py --check",
                   note="Chạy send_report.py --check để verify Gmail SMTP.")
        return res
    if st == "gmail_api" or method == "https":
        res.update(status="needs_model_probe",
                   verify_cmd="report-mailer/send_report.py --check --transport https",
                   note="Chạy send_report.py --check --transport https để verify Gmail API.")
        return res
    if method == "local_file":
        fp = entry.get("file_path", "")
        p = Path(fp).expanduser() if fp else None
        if p and p.exists():
            res.update(status="connected")
        else:
            res.update(status="error", last_error=f"không thấy file: {fp or '(trống)'}")
        return res
    # còn lại: api (jira_*/github/gitlab/confluence) + sharepoint
    status, err = probe_api(entry)
    res.update(status=status, last_error=err)
    return res


def record_result(cfg_path, eid, status, last_error=""):
    """Ghi status/last_checked/last_error cho entry <eid> trong block connections: (sửa YAML TẠI CHỖ,
    stdlib — regex giới hạn đúng vùng indent của entry, KHÔNG đụng creds:/verify: con)."""
    p = Path(cfg_path)
    if not p.exists():
        print(f"❌ Không thấy config: {cfg_path}", file=sys.stderr)
        sys.exit(2)
    lines = p.read_text(encoding="utf-8").splitlines()
    id_re = re.compile(r"^(\s*)-\s+id:\s*['\"]?" + re.escape(eid) + r"['\"]?\s*(#.*)?$")
    start, dash_indent = None, 0
    for i, ln in enumerate(lines):
        m = id_re.match(ln)
        if m:
            start, dash_indent = i, len(m.group(1))
            break
    if start is None:
        print(f"❌ Không thấy id '{eid}' trong connections của {cfg_path}.", file=sys.stderr)
        sys.exit(2)
    child = " " * (dash_indent + 2)               # key con của list-item nằm ngay dưới 'id'
    end = len(lines)                              # cuối entry = dòng non-blank đầu tiên thụt < child
    for j in range(start + 1, len(lines)):
        s = lines[j]
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        if (len(s) - len(s.lstrip())) < len(child):
            end = j
            break
    upd = {"status": f"{child}status: {status}",
           "last_checked": f'{child}last_checked: "{now_iso()}"',
           "last_error": f'{child}last_error: "{last_error or ""}"'}
    seen = set()
    for j in range(start + 1, end):
        s = lines[j]
        if (len(s) - len(s.lstrip())) != len(child):
            continue
        km = re.match(r"^\s*([A-Za-z_]+):", s)
        if km and km.group(1) in upd:
            lines[j] = upd[km.group(1)]
            seen.add(km.group(1))
    miss = [upd[k] for k in ("status", "last_checked", "last_error") if k not in seen]
    if miss:
        lines[start + 1:start + 1] = miss
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✓ Ghi trạng thái '{status}' cho {eid} vào sổ (last_checked cập nhật).")


def main():
    ap = argparse.ArgumentParser(description="Kiểm tra sổ kết nối Kora.")
    ap.add_argument("--list", action="store_true", help="In bảng các kết nối đã đăng ký.")
    ap.add_argument("--check", metavar="ID", help="Kiểm tra 1 kết nối theo id.")
    ap.add_argument("--check-all", dest="check_all", action="store_true",
                    help="Kiểm tra LẠI TẤT␣CẢ kết nối (lặp mọi entry; nguồn mcp/mail → needs_model_probe + gợi ý tool).")
    ap.add_argument("--list-repos", dest="list_repos", metavar="ID",
                    help="Liệt kê repo (GitHub) / project (GitLab) của connection <id> (JSON) để CHỌN.")
    ap.add_argument("--json", action="store_true", help="In JSON thay vì bảng (cho --list).")
    ap.add_argument("--config", default="", help="Đường dẫn factory-config.yaml (mặc định: config của "
                    "thư mục hiện tại = PROJECT). Cần khi tool chạy từ CORE cho project ở nơi khác.")
    ap.add_argument("--record-result", dest="record_result", metavar="ID",
                    help="GHI lại trạng thái verify cho 1 nguồn (sau khi model probe MCP). Cần --status và --confirm.")
    ap.add_argument("--status", dest="rec_status", choices=["connected", "error", "needs_model_probe"],
                    help="Trạng thái để ghi (đi cùng --record-result).")
    ap.add_argument("--last-error", dest="rec_error", default="",
                    help="Mô tả lỗi (đi cùng --record-result, tùy chọn).")
    ap.add_argument("--confirm", action="store_true",
                    help="Xác nhận GHI registry — BẮT BUỘC cho --record-result (cổng chống ghi lén, phải qua Approval Gate).")
    args = ap.parse_args()

    cfg_path = resolve_config(args.config)
    conns = parse_connections(cfg_path)

    if args.record_result:   # ── GATE: ghi registry phải có --status + --confirm ──
        if not args.rec_status:
            print("❌ --record-result cần --status <connected|error|needs_model_probe>.", file=sys.stderr)
            sys.exit(2)
        if not args.confirm:
            print("❌ --record-result cần --confirm (cổng chống ghi registry lén — phải qua Approval Gate).",
                  file=sys.stderr)
            sys.exit(2)
        record_result(cfg_path, args.record_result, args.rec_status, args.rec_error)
        return

    if args.list_repos:
        entry = next((c for c in conns if c.get("id") == args.list_repos), None)
        if not entry:
            print(json.dumps({"error": f"không tìm thấy id '{args.list_repos}' trong connections"}, ensure_ascii=False))
            sys.exit(1)
        list_repos(entry)
        return

    if args.check_all:
        results = [verify_one(c) for c in conns]
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return
        if not conns:
            print("ℹ️  Chưa có kết nối nào. Chạy /claude-knowledge-connect để thêm.")
            return
        icon = {"connected": "✅", "error": "❌", "needs_model_probe": "🔶"}
        print(f"{'ID':30} {'METHOD':6} {'STATUS':20} CHI TIẾT (tool/cmd để verify · hoặc lỗi)")
        for r in results:
            tag = f"{icon.get(r['status'], '?')} {r['status']}"
            detail = r.get("verify_tool") or r.get("verify_cmd") or r.get("last_error") or ""
            print(f"{r.get('id', '?'):30} {r.get('method', '?'):6} {tag:20} {detail}")
        n_probe = sum(1 for r in results if r["status"] == "needs_model_probe")
        if n_probe:
            print(f"\n🔶 {n_probe} nguồn (MCP/mail) cần model tự gọi tool/cmd ở cột CHI TIẾT để verify.")
        return

    if args.list or (not args.check):
        if args.json:
            print(json.dumps(conns, ensure_ascii=False, indent=2))
            return
        if not conns:
            print("ℹ️  Chưa có kết nối nào. Chạy /claude-knowledge-connect để thêm.")
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
