#!/usr/bin/env python3
"""
sync_confluence.py — Đồng bộ Knowledge Base ↔ Confluence chung (GET & POST).

Nguyên lý Kora: gom tri thức rải rác → KB cục bộ → ĐẨY (post) lên 1 Confluence chung;
user chỉ-đọc thì KÉO (pull) về. Đây là đường HEADLESS (chạy trong cron/scheduler, KHÔNG
cần app Claude). Đường TƯƠNG TÁC trong app dùng connector MCP Atlassian — cả hai cùng ghi
một file map nên không tạo trang trùng.

Bí mật đọc từ tools/confluence-sync/.env.local (đã gitignore). KHÔNG in token ra log.
Chỉ dùng thư viện chuẩn Python 3 (urllib, json, hashlib, http.server...).

Xác thực (tự nhận diện — như import_jira):
  - OAuth 2.0 (3LO): chạy `--login` 1 lần (mở trình duyệt) → lưu .oauth-token.json (tự refresh).
  - API token (Basic email:token): điền CONFLUENCE_EMAIL + CONFLUENCE_API_TOKEN — hợp cho cron.

Ví dụ:
  python3 tools/confluence-sync/sync_confluence.py --check
  python3 tools/confluence-sync/sync_confluence.py --login
  python3 tools/confluence-sync/sync_confluence.py --push --dry-run
  python3 tools/confluence-sync/sync_confluence.py --push --space KB --parent 123456
  python3 tools/confluence-sync/sync_confluence.py --pull --space KB
  python3 tools/confluence-sync/sync_confluence.py --check-fresh
  # Windows: thay python3 bằng py
"""
import argparse
import base64
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
TOKEN_FILE = HERE / ".oauth-token.json"
TIMEOUT = 45


# ───────────────────────────── tiện ích chung ──────────────────────────────
def die(msg: str, code: int = 1):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg: str):
    print(f"⚠️  {msg}", file=sys.stderr)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def load_env(path: Path) -> dict:
    """Đọc .env.local dạng KEY=VALUE (bỏ dòng trống / dòng bắt đầu bằng #)."""
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def load_config(path: Path) -> dict:
    """Đọc factory-config.yaml → dict dotted-key -> value (chỉ scalar; bỏ list/block).
    Đủ để lấy confluence.space_key, knowledge_base.vault_path... mà KHÔNG cần pyyaml."""
    result = {}
    if not path.exists():
        return result
    stack = []  # [(indent, key)]
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or raw.lstrip().startswith("- "):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, rawval = line.partition(":")
        key, rawval = key.strip(), rawval.strip()
        # Tách value: nếu trong nháy → lấy ĐÚNG phần trong nháy (bỏ comment đuôi SAU nháy đóng,
        # vẫn giữ '#' hợp lệ bên trong chuỗi); nếu không nháy → cắt comment '# ...' cuối dòng.
        quoted = rawval[:1] in ('"', "'")
        if quoted:
            q = rawval[0]
            end = rawval.find(q, 1)
            val = rawval[1:end] if end != -1 else rawval[1:]
        else:
            val = re.sub(r"(^|\s)#.*$", "", rawval).strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        dotted = ".".join([k for _, k in stack] + [key])
        if val == "" and not quoted:   # block header (KHÔNG có value) → đẩy vào ngăn xếp
            stack.append((indent, key))
            continue
        result[dotted] = val            # scalar (kể cả '""' → chuỗi rỗng)
    return result


def vault_dir(cfg: dict) -> Path:
    v = cfg.get("knowledge_base.vault_path") or "Project_Name_Brain"
    p = Path(v)
    return p if p.is_absolute() else (REPO_ROOT / p)


def sysdir(cfg: dict) -> Path:
    d = vault_dir(cfg) / "_system" / "confluence"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─────────────────────────── xác thực / client ─────────────────────────────
class Client:
    """Bọc REST Confluence Cloud cho cả 2 chế độ auth. Tự thêm /wiki/rest/api."""

    def __init__(self, base: str, headers: dict, label: str):
        self.base = base.rstrip("/")          # đã gồm .../wiki
        self.headers = headers
        self.label = label

    def _req(self, method: str, path: str, params: dict = None, body=None):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = None
        headers = dict(self.headers)
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            raise ApiError(e.code, detail)
        except urllib.error.URLError as e:
            raise ApiError(0, f"network: {e.reason}")

    def get(self, path, params=None):
        return self._req("GET", path, params=params)

    def post(self, path, body):
        return self._req("POST", path, body=body)

    def put(self, path, body):
        return self._req("PUT", path, body=body)


class ApiError(Exception):
    def __init__(self, code, detail):
        super().__init__(f"HTTP {code}: {detail}")
        self.code = code
        self.detail = detail


def _oauth_refresh_if_needed(env: dict):
    """Nếu token sắp hết hạn và có refresh_token → xin token mới, ghi lại file."""
    if not TOKEN_FILE.exists():
        return None
    tok = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    if tok.get("expires_at", 0) - 60 > time.time():
        return tok
    rt = tok.get("refresh_token")
    cid = env.get("CONFLUENCE_OAUTH_CLIENT_ID")
    cs = env.get("CONFLUENCE_OAUTH_CLIENT_SECRET")
    if not (rt and cid and cs):
        return tok  # không refresh được → để client thử, lỗi sẽ báo rõ
    body = json.dumps({
        "grant_type": "refresh_token", "client_id": cid,
        "client_secret": cs, "refresh_token": rt,
    }).encode()
    req = urllib.request.Request(
        "https://auth.atlassian.com/oauth/token", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            new = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        warn(f"Refresh OAuth thất bại ({e}) — hãy chạy lại `--login` ở Terminal.")
        return tok
    tok["access_token"] = new["access_token"]
    tok["refresh_token"] = new.get("refresh_token", rt)
    tok["expires_at"] = time.time() + int(new.get("expires_in", 3600))
    TOKEN_FILE.write_text(json.dumps(tok, indent=2), encoding="utf-8")
    return tok


def build_client(env: dict, cfg: dict) -> Client:
    """Quyết định auth: oauth (có token file) → token (Basic) → die."""
    auth = (env.get("CONFLUENCE_AUTH") or cfg.get("confluence.auth") or "auto").lower()
    base_url = env.get("CONFLUENCE_BASE_URL") or cfg.get("confluence.base_url") or ""

    if auth in ("auto", "oauth") and TOKEN_FILE.exists():
        tok = _oauth_refresh_if_needed(env)
        cloud_id = tok.get("cloud_id")
        if not cloud_id:
            die("Token OAuth thiếu cloud_id — chạy lại `--login`.")
        base = f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki"
        headers = {"Authorization": f"Bearer {tok['access_token']}", "Accept": "application/json"}
        return Client(base, headers, f"OAuth → cloud {cloud_id[:8]}…")

    if auth in ("auto", "token"):
        email = env.get("CONFLUENCE_EMAIL")
        token = env.get("CONFLUENCE_API_TOKEN")
        if token and token.strip().startswith("PASTE_"):
            token = None
        if base_url and email and token:
            base = base_url.rstrip("/")
            if not base.endswith("/wiki"):
                base += "/wiki"
            cred = base64.b64encode(f"{email}:{token}".encode()).decode()
            headers = {"Authorization": f"Basic {cred}", "Accept": "application/json"}
            return Client(base, headers, f"Token → {email}")

    die("Chưa cấu hình kết nối Confluence. Tạo tools/confluence-sync/.env.local "
        "(copy từ .env.example): điền CONFLUENCE_BASE_URL + (CONFLUENCE_EMAIL + "
        "CONFLUENCE_API_TOKEN) HOẶC chạy `--login` để dùng OAuth 2.0.")


# ──────────────────────────────── OAuth login ──────────────────────────────
def cmd_login(env: dict):
    import http.server
    import webbrowser

    cid = env.get("CONFLUENCE_OAUTH_CLIENT_ID")
    cs = env.get("CONFLUENCE_OAUTH_CLIENT_SECRET")
    if not (cid and cs):
        die("Thiếu CONFLUENCE_OAUTH_CLIENT_ID / _SECRET trong .env.local "
            "(tạo OAuth 2.0 app tại developer.atlassian.com).")
    redirect = env.get("CONFLUENCE_OAUTH_REDIRECT", "http://localhost:8765/callback")
    scopes = env.get("CONFLUENCE_OAUTH_SCOPES",
                     "read:confluence-content.all write:confluence-content offline_access")
    base_url = env.get("CONFLUENCE_BASE_URL", "")
    state = base64.urlsafe_b64encode(os.urandom(12)).decode()

    authorize = "https://auth.atlassian.com/authorize?" + urllib.parse.urlencode({
        "audience": "api.atlassian.com", "client_id": cid, "scope": scopes,
        "redirect_uri": redirect, "state": state, "response_type": "code", "prompt": "consent",
    })

    holder = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.urlparse(self.path).query
            params = dict(urllib.parse.parse_qsl(q))
            holder.update(params)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("✅ Kora: đã nhận uỷ quyền. Quay lại Terminal được rồi."
                             .encode("utf-8"))

        def log_message(self, *a):
            pass

    port = int(urllib.parse.urlparse(redirect).port or 8765)
    httpd = http.server.HTTPServer(("localhost", port), H)
    print("🔐 Mở trình duyệt để uỷ quyền Confluence… (nếu không tự mở, dán URL dưới đây)")
    print(authorize)
    try:
        webbrowser.open(authorize)
    except Exception:  # noqa: BLE001
        pass
    httpd.handle_request()  # chờ đúng 1 callback
    if holder.get("state") != state:
        die("State không khớp — huỷ vì lý do an toàn. Thử lại `--login`.")
    code = holder.get("code")
    if not code:
        die(f"Không nhận được mã uỷ quyền ({holder.get('error', 'unknown')}).")

    body = json.dumps({
        "grant_type": "authorization_code", "client_id": cid, "client_secret": cs,
        "code": code, "redirect_uri": redirect,
    }).encode()
    req = urllib.request.Request("https://auth.atlassian.com/oauth/token", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        tok = json.loads(r.read())

    # tìm cloud_id khớp base_url
    ar_req = urllib.request.Request(
        "https://api.atlassian.com/oauth/token/accessible-resources",
        headers={"Authorization": f"Bearer {tok['access_token']}", "Accept": "application/json"})
    with urllib.request.urlopen(ar_req, timeout=TIMEOUT) as r:
        resources = json.loads(r.read())
    cloud_id = None
    want = urllib.parse.urlparse(base_url).netloc
    for res in resources:
        if want and want in res.get("url", ""):
            cloud_id = res["id"]
            break
    if not cloud_id and resources:
        cloud_id = resources[0]["id"]
        warn(f"Không khớp base_url, dùng site đầu tiên: {resources[0].get('url')}")
    if not cloud_id:
        die("Tài khoản không truy cập được site Confluence nào.")

    out = {
        "access_token": tok["access_token"],
        "refresh_token": tok.get("refresh_token", ""),
        "expires_at": time.time() + int(tok.get("expires_in", 3600)),
        "cloud_id": cloud_id, "obtained_at": now_iso(),
    }
    TOKEN_FILE.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"✅ Đăng nhập OAuth thành công. Đã lưu {TOKEN_FILE.name} (KHÔNG in token).")


# ─────────────────────────── đọc note KB cục bộ ────────────────────────────
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_note(path: Path):
    """Trả về (kb_id, title, body_markdown) cho 1 file .md."""
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body = {}, text
    m = FM_RE.match(text)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.lstrip().startswith("-"):
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip('"').strip("'")
        body = text[m.end():]
    kb_id = (fm.get("jira_key") or fm.get("feature_id")
             or str(path.relative_to(REPO_ROOT)).replace("\\", "/"))
    title = fm.get("title")
    if not title:
        mh = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = mh.group(1).strip() if mh else path.stem
    return kb_id, title, body


def collect_notes(cfg: dict, source: str, scope: str):
    """Tập hợp các file .md để đẩy lên, theo confluence.push.source (vault|docs|both)."""
    roots = []
    if source in ("vault", "both"):
        roots.append(vault_dir(cfg))
    if source in ("docs", "both"):
        roots.append(REPO_ROOT / (cfg.get("knowledge_base.docs_path") or "docs"))
    seen, files = set(), []
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            rel = str(p.relative_to(root))
            if "_system" in p.parts or p.name.startswith("."):
                continue
            if scope and scope not in rel:
                continue
            if p in seen:
                continue
            seen.add(p)
            files.append(p)
    return files


# ─────────────────── chuyển đổi Markdown ↔ Confluence storage ───────────────
def md_to_storage(md: str) -> str:
    """Markdown → Confluence storage (XHTML). Tối giản, an toàn-mất-mát."""
    lines = md.replace("\r\n", "\n").split("\n")
    out, i = [], 0

    def inline(t: str) -> str:
        t = html.escape(t, quote=False)
        t = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                   lambda m: f'<a href="{html.escape(m.group(2), True)}">{m.group(1)}</a>', t)
        return t

    while i < len(lines):
        ln = lines[i]
        # code fence
        if ln.strip().startswith("```"):
            lang = ln.strip()[3:].strip()
            buf, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            code = "\n".join(buf)
            macro = ('<ac:structured-macro ac:name="code">'
                     + (f'<ac:parameter ac:name="language">{html.escape(lang)}</ac:parameter>' if lang else "")
                     + f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
                     + '</ac:structured-macro>')
            out.append(macro)
            continue
        # heading
        mh = re.match(r"^(#{1,6})\s+(.+)$", ln)
        if mh:
            lvl = len(mh.group(1))
            out.append(f"<h{lvl}>{inline(mh.group(2).strip())}</h{lvl}>")
            i += 1
            continue
        # table (pipe)
        if "|" in ln and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]):
            header = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in header)
            trs = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f"<table><tbody><tr>{th}</tr>{trs}</tbody></table>")
            continue
        # unordered list
        if re.match(r"^\s*[-*]\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(inline(re.sub(r"^\s*[-*]\s+", "", lines[i])))
                i += 1
            out.append("<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>")
            continue
        # ordered list
        if re.match(r"^\s*\d+\.\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(inline(re.sub(r"^\s*\d+\.\s+", "", lines[i])))
                i += 1
            out.append("<ol>" + "".join(f"<li>{it}</li>" for it in items) + "</ol>")
            continue
        # blank
        if not ln.strip():
            i += 1
            continue
        # paragraph (gộp tới dòng trống)
        buf = [ln]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|\s*[-*]\s|\s*\d+\.\s|```)", lines[i]):
            buf.append(lines[i]); i += 1
        out.append("<p>" + inline(" ".join(s.strip() for s in buf)) + "</p>")
    return "\n".join(out)


def storage_to_md(storage: str) -> str:
    """Confluence storage → Markdown (best-effort cho pull)."""
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.out = []
            self.skip = 0
            self.list_stack = []

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self.out.append("\n" + "#" * int(tag[1]) + " ")
            elif tag == "p":
                self.out.append("\n\n")
            elif tag in ("ul", "ol"):
                self.list_stack.append(tag)
            elif tag == "li":
                marker = "1. " if (self.list_stack and self.list_stack[-1] == "ol") else "- "
                self.out.append("\n" + marker)
            elif tag in ("strong", "b"):
                self.out.append("**")
            elif tag in ("em", "i"):
                self.out.append("*")
            elif tag == "code":
                self.out.append("`")
            elif tag == "a":
                self.out.append("[")
                self._href = a.get("href", "")
            elif tag == "br":
                self.out.append("\n")
            elif tag == "ac:plain-text-body":
                self.out.append("\n```\n")

        def handle_endtag(self, tag):
            if tag in ("strong", "b"):
                self.out.append("**")
            elif tag in ("em", "i"):
                self.out.append("*")
            elif tag == "code":
                self.out.append("`")
            elif tag == "a":
                self.out.append(f"]({getattr(self, '_href', '')})")
            elif tag in ("ul", "ol") and self.list_stack:
                self.list_stack.pop()
            elif tag == "ac:plain-text-body":
                self.out.append("\n```\n")

        def handle_data(self, data):
            self.out.append(data)

    p = P()
    p.feed(storage)
    text = "".join(p.out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


# ──────────────────────────────── map / mốc ────────────────────────────────
def host_of(client: Client) -> str:
    return urllib.parse.urlparse(client.base).netloc.replace(":", "_")


def map_path(cfg, client):
    return sysdir(cfg) / f"confluence-map-{host_of(client)}.json"


def load_map(cfg, client) -> dict:
    p = map_path(cfg, client)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"space_key": "", "parent_page_id": "", "pages": {}}


def save_map(cfg, client, data):
    data["generated_at"] = now_iso()
    map_path(cfg, client).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def watermark(cfg, client, kind) -> Path:
    return sysdir(cfg) / f"last-{kind}-{host_of(client)}.txt"


# ──────────────────────────────── lệnh push ────────────────────────────────
def find_page_by_title(client, space, title):
    st, data = client.get("/rest/api/content",
                          {"spaceKey": space, "title": title, "expand": "version", "limit": 1})
    results = data.get("results", [])
    return results[0] if results else None


def cmd_push(args, env, cfg, client):
    space = args.space or cfg.get("confluence.space_key") or ""
    parent = args.parent or cfg.get("confluence.parent_page_id") or ""
    permission = (cfg.get("confluence.permission") or "read_write").lower()
    source = args.source or cfg.get("confluence.push.source") or "both"
    scope = args.scope or cfg.get("confluence.push.scope") or ""
    on_conflict = cfg.get("confluence.push.on_conflict") or "skip_human_edited"

    if permission == "read_only":
        die("confluence.permission = read_only → KHÔNG được đẩy (push). "
            "Chỉ user có quyền write mới đẩy lên KB chung.")
    if not space:
        die("Thiếu space đích. Truyền --space hoặc đặt confluence.space_key trong config.")

    notes = collect_notes(cfg, source, scope)
    if not notes:
        print("ℹ️  Không có note nào để đẩy."); return 0

    cmap = load_map(cfg, client)
    cmap["space_key"], cmap["parent_page_id"] = space, parent
    pages = cmap.setdefault("pages", {})
    created = updated = skipped = 0
    errors = []

    for path in notes:
        try:
            kb_id, title, body = parse_note(path)
            content_hash = "sha256:" + hashlib.sha256((title + "\n" + body).encode("utf-8")).hexdigest()
            rec = pages.get(kb_id)
            if rec and rec.get("content_hash") == content_hash and not args.force:
                skipped += 1
                continue
            storage = md_to_storage(body)
            if args.dry_run:
                act = "update" if rec else "create"
                print(f"  [dry] {act}: {title}  ({kb_id})")
                if rec:
                    updated += 1
                else:
                    created += 1
                continue

            page_id = rec.get("page_id") if rec else None
            if not page_id:  # chưa map → tìm theo title để NHẬN (tránh trùng)
                found = find_page_by_title(client, space, title)
                if found:
                    page_id = found["id"]

            if page_id:
                _st, cur = client.get(f"/rest/api/content/{page_id}", {"expand": "version"})
                remote_ver = cur.get("version", {}).get("number", 1)
                if rec and on_conflict == "skip_human_edited" and rec.get("version") \
                        and remote_ver > rec["version"]:
                    warn(f"Bỏ qua (đã bị sửa tay trên Confluence): {title}")
                    skipped += 1
                    continue
                body_req = {
                    "id": page_id, "type": "page", "title": title,
                    "space": {"key": space},
                    "version": {"number": remote_ver + 1, "message": "Kora sync"},
                    "body": {"storage": {"value": storage, "representation": "storage"}},
                }
                _st, res = client.put(f"/rest/api/content/{page_id}", body_req)
                updated += 1
            else:
                body_req = {
                    "type": "page", "title": title, "space": {"key": space},
                    "body": {"storage": {"value": storage, "representation": "storage"}},
                }
                if parent:
                    body_req["ancestors"] = [{"id": str(parent)}]
                _st, res = client.post("/rest/api/content", body_req)
                page_id = res["id"]
                created += 1

            pages[kb_id] = {
                "page_id": str(page_id),
                "title": title,
                "source_path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "content_hash": content_hash,
                "version": res.get("version", {}).get("number", 1),
                "last_pushed_at": now_iso(),
            }
        except ApiError as e:
            errors.append({"kb_id": kb_id, "title": title, "op": "push",
                           "http_code": e.code, "reason": e.detail[:200]})
            warn(f"Lỗi đẩy '{title}': {e}")
        except Exception as e:  # noqa: BLE001
            errors.append({"kb_id": str(path), "title": path.name, "op": "push",
                           "http_code": 0, "reason": str(e)[:200]})
            warn(f"Lỗi đẩy {path.name}: {e}")

    if not args.dry_run:
        save_map(cfg, client, cmap)
        watermark(cfg, client, "push").write_text(now_iso(), encoding="utf-8")
        (sysdir(cfg) / f"daily-confluence-{host_of(client)}-{today_str()}.txt").write_text(
            "push", encoding="utf-8")
        if errors:
            write_error_report(cfg, "push", errors)

    print(f"✅ Push xong: +{created} tạo, ~{updated} cập nhật, ={skipped} bỏ qua, "
          f"✗{len(errors)} lỗi → space {space}")
    return 2 if errors else 0


# ──────────────────────────────── lệnh pull ────────────────────────────────
def cmd_pull(args, env, cfg, client):
    space = args.space or cfg.get("confluence.space_key") or ""
    if not space:
        die("Thiếu space nguồn. Truyền --space hoặc đặt confluence.space_key.")
    into = args.into or cfg.get("confluence.pull.into") or ""
    dest = Path(into) if into else (vault_dir(cfg) / "Confluence")
    if not dest.is_absolute():
        dest = REPO_ROOT / dest
    dest.mkdir(parents=True, exist_ok=True)

    start, limit, pulled, errors = 0, 50, 0, []
    while True:
        try:
            _st, data = client.get("/rest/api/content", {
                "spaceKey": space, "type": "page", "start": start, "limit": limit,
                "expand": "body.storage,version",
            })
        except ApiError as e:
            die(f"Không liệt kê được trang trong space {space}: {e}")
        results = data.get("results", [])
        if not results:
            break
        for pg in results:
            try:
                if args.dry_run:
                    print(f"  [dry] pull: {pg.get('title')}")
                    pulled += 1
                    continue
                title = pg.get("title", pg["id"])
                storage = pg.get("body", {}).get("storage", {}).get("value", "")
                md = storage_to_md(storage)
                slug = re.sub(r"[^\w\-]+", "-", title)[:80].strip("-") or pg["id"]
                fm = (f"---\nsource: confluence\nconfluence_page_id: {pg['id']}\n"
                      f"confluence_version: {pg.get('version', {}).get('number', 1)}\n"
                      f"confluence_space: {space}\ntitle: \"{title}\"\n"
                      f"imported_at: {now_iso()}\n---\n\n")
                (dest / f"{slug}.md").write_text(fm + md, encoding="utf-8")
                pulled += 1
            except Exception as e:  # noqa: BLE001
                errors.append({"page_id": pg.get("id"), "title": pg.get("title"),
                               "op": "pull", "http_code": 0, "reason": str(e)[:200]})
        start += limit
        if len(results) < limit:
            break

    if not args.dry_run:
        watermark(cfg, client, "pull").write_text(now_iso(), encoding="utf-8")
        if errors:
            write_error_report(cfg, "pull", errors)
    print(f"✅ Pull xong: {pulled} trang → {dest}  ({len(errors)} lỗi)")
    return 2 if errors else 0


# ───────────────────────── báo cáo lỗi / freshness ─────────────────────────
def write_error_report(cfg, op, errors):
    d = sysdir(cfg)
    (d / f"confluence-sync-errors-{today_str()}.json").write_text(
        json.dumps({"op": op, "at": now_iso(), "errors": errors}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    md = [f"# Confluence sync errors — {op} — {today_str()}", ""]
    for e in errors:
        md.append(f"- **{e.get('title')}** (`{e.get('kb_id') or e.get('page_id')}`) — "
                  f"HTTP {e.get('http_code')}: {e.get('reason')}")
    (d / f"confluence-sync-errors-{today_str()}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def cmd_check_fresh(cfg, client):
    def read_wm(kind):
        p = watermark(cfg, client, kind)
        return p.read_text(encoding="utf-8").strip() if p.exists() else None
    last_push, last_pull = read_wm("push"), read_wm("pull")
    age_days = None
    newest = max([t for t in (last_push, last_pull) if t], default=None)
    if newest:
        try:
            age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(newest).astimezone(
                timezone.utc)).days
        except Exception:  # noqa: BLE001
            pass
    daily = sysdir(cfg) / f"daily-confluence-{host_of(client)}-{today_str()}.txt"
    print(json.dumps({
        "last_push": last_push, "last_pull": last_pull,
        "age_days": age_days, "is_stale": (age_days is None or age_days >= 1),
        "done_today": daily.exists(), "today": today_str(),
    }, ensure_ascii=False))


# ──────────────────────────────── check ────────────────────────────────────
def cmd_check(cfg, client):
    try:
        _st, me = client.get("/rest/api/user/current")
    except ApiError as e:
        if e.code in (401, 403):
            die(f"Xác thực Confluence THẤT BẠI ({e.code}). Kiểm tra token/OAuth trong .env.local.")
        die(f"Không kết nối được Confluence: {e}")
    name = me.get("displayName") or me.get("publicName") or me.get("accountId", "?")
    print(f"✅ Kết nối Confluence OK — {client.label} — tài khoản: {name}")


# ──────────────────────────────── main ─────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Đồng bộ KB ↔ Confluence chung (get & post).")
    ap.add_argument("--check", action="store_true", help="Kiểm tra kết nối (không ghi).")
    ap.add_argument("--login", action="store_true", help="Đăng nhập OAuth 2.0 (mở trình duyệt) 1 lần.")
    ap.add_argument("--push", action="store_true", help="Đẩy KB cục bộ → Confluence (upsert idempotent).")
    ap.add_argument("--pull", action="store_true", help="Kéo trang Confluence → vault.")
    ap.add_argument("--check-fresh", action="store_true", help="In JSON độ mới (cho scheduler/report).")
    ap.add_argument("--space", help="Space key (mặc định confluence.space_key).")
    ap.add_argument("--parent", help="Parent page id (mặc định confluence.parent_page_id).")
    ap.add_argument("--source", choices=["vault", "docs", "both"], help="Nguồn note để đẩy.")
    ap.add_argument("--scope", help="Lọc theo thư mục/glob khi đẩy.")
    ap.add_argument("--into", help="Thư mục đích khi pull (mặc định <vault>/Confluence).")
    ap.add_argument("--dry-run", action="store_true", help="Chỉ in kế hoạch, KHÔNG ghi.")
    ap.add_argument("--force", action="store_true", help="Bỏ qua kiểm tra hash, đẩy lại tất cả.")
    args = ap.parse_args()

    env = load_env(HERE / ".env.local")
    cfg = load_config(REPO_ROOT / "config" / "factory-config.yaml")

    if args.login:
        return cmd_login(env)

    client = build_client(env, cfg)

    if args.check:
        return cmd_check(cfg, client)
    if args.check_fresh:
        return cmd_check_fresh(cfg, client)
    if args.push:
        sys.exit(cmd_push(args, env, cfg, client))
    if args.pull:
        sys.exit(cmd_pull(args, env, cfg, client))
    ap.print_help()


if __name__ == "__main__":
    main()
