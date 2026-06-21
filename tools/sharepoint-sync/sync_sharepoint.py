#!/usr/bin/env python3
"""
sync_sharepoint.py — Đồng bộ Knowledge Base ↔ SharePoint (Microsoft Graph). GET & POST.

Anh em với tools/confluence-sync và tools/github-sync: cùng triết lý "gom tri thức cục bộ →
ĐẨY (push) lên 1 nơi chung; chỉ-đọc thì KÉO (pull) về". Target là 1 thư viện tài liệu
(document library) trên SharePoint. Đường HEADLESS (chạy được trong cron/scheduler).

Xác thực (TỰ NHẬN DIỆN — hỗ trợ CẢ HAI):
  - client-credentials (app-only): có SHAREPOINT_TENANT_ID + SHAREPOINT_CLIENT_ID +
    SHAREPOINT_CLIENT_SECRET → xin token mỗi lần chạy (scope .default; cần admin consent
    Sites.ReadWrite.All). CHẠY NỀN được (lịch launchd/cron).
  - device-flow (delegated): chạy `--login` 1 lần (nhập mã trên trình duyệt) → lưu
    .oauth-token.json (tự refresh). CHỈ tương tác — token hết hạn phải đăng nhập lại.

Bảo mật:
  - Bí mật đọc từ ENV (shell ~/.zshrc) hoặc tools/sharepoint-sync/.env.local (đã gitignore).
  - Token KHÔNG vào log/chat/git. Chỉ thư viện chuẩn Python 3. Tái dùng helper sync_confluence.

Idempotent: map <vault>/_system/sharepoint/sharepoint-map-<host>-<site>.json (kb_id ↔ drive item).
Chỉ ghi/cập nhật file đổi nội dung (so content_hash) — không nhân bản.

Ví dụ:
  python3 tools/sharepoint-sync/sync_sharepoint.py --check
  python3 tools/sharepoint-sync/sync_sharepoint.py --login
  python3 tools/sharepoint-sync/sync_sharepoint.py --push --dry-run
  python3 tools/sharepoint-sync/sync_sharepoint.py --push --site FTEL_Medicare
  python3 tools/sharepoint-sync/sync_sharepoint.py --pull
  # Windows: thay python3 bằng py
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Tái dùng helper của confluence-sync (die/warn/now_iso/load_env/load_config/vault_dir/
# parse_note/collect_notes/REPO_ROOT/TIMEOUT/ApiError).
sys.path.insert(0, str(HERE.parents[0] / "confluence-sync"))
import sync_confluence as cs  # noqa: E402

REPO_ROOT = cs.REPO_ROOT
CONFIG = REPO_ROOT / "config" / "factory-config.yaml"
TOKEN_FILE = HERE / ".oauth-token.json"
GRAPH = "https://graph.microsoft.com/v1.0"
AUTHORITY = "https://login.microsoftonline.com"
TIMEOUT = cs.TIMEOUT
FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

TENANT_KEYS = ("SHAREPOINT_TENANT_ID", "SHAREPOINT_TENANT", "AZURE_TENANT_ID")
CLIENT_KEYS = ("SHAREPOINT_CLIENT_ID", "AZURE_CLIENT_ID")
SECRET_KEYS = ("SHAREPOINT_CLIENT_SECRET", "AZURE_CLIENT_SECRET")
# Quyền delegated cho device-flow (app-only client-credentials luôn dùng /.default).
DELEGATED_SCOPE = "https://graph.microsoft.com/Sites.ReadWrite.All offline_access"


def die(msg, code=1):
    cs.die(msg, code)


def warn(msg):
    cs.warn(msg)


def envget(env: dict, keys) -> str:
    for k in keys:
        v = env.get(k) or os.getenv(k)
        if v and not v.strip().startswith("PASTE_"):
            return v.strip()
    return ""


# ─────────────────────────── HTTP Graph client ─────────────────────────────
class Graph:
    """Bọc Microsoft Graph REST (token Bearer). KHÔNG in token."""

    def __init__(self, token: str, label: str):
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        self.label = label

    def _req(self, method, path, params=None, body=None, raw=None, ctype=None):
        url = path if path.startswith("http") else GRAPH + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = dict(self.headers)
        data = None
        if raw is not None:
            data = raw
            headers["Content-Type"] = ctype or "application/octet-stream"
        elif body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                buf = r.read()
                if r.headers.get("Content-Type", "").startswith("application/json"):
                    return r.status, (json.loads(buf) if buf else {})
                return r.status, buf
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            raise cs.ApiError(e.code, detail)
        except urllib.error.URLError as e:
            raise cs.ApiError(0, f"network: {e.reason}")

    def get(self, path, params=None):
        return self._req("GET", path, params=params)

    def get_bytes(self, path):
        return self._req("GET", path)

    def put_raw(self, path, data: bytes, ctype="text/markdown"):
        return self._req("PUT", path, raw=data, ctype=ctype)

    def delete(self, path):
        return self._req("DELETE", path)


# ──────────────────────────────── Xác thực ─────────────────────────────────
def _client_credentials_token(tenant, client, secret) -> str:
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client,
        "client_secret": secret,
        "scope": "https://graph.microsoft.com/.default",
    }).encode()
    req = urllib.request.Request(
        f"{AUTHORITY}/{tenant}/oauth2/v2.0/token", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            tok = json.loads(r.read())
    except urllib.error.HTTPError as e:
        die("Lấy token app-only (client-credentials) thất bại — kiểm tra TENANT/CLIENT/SECRET "
            f"và admin consent Sites.ReadWrite.All. ({e.code})")
    except urllib.error.URLError as e:
        die(f"Mạng lỗi khi lấy token: {e.reason}")
    return tok.get("access_token", "")


def _device_token(env) -> str:
    """Đọc .oauth-token.json (device-flow), refresh nếu sắp hết hạn."""
    if not TOKEN_FILE.exists():
        return ""
    tok = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    if tok.get("expires_at", 0) - 60 > time.time():
        return tok.get("access_token", "")
    rt = tok.get("refresh_token")
    tenant = tok.get("tenant") or envget(env, TENANT_KEYS) or "common"
    client = tok.get("client") or envget(env, CLIENT_KEYS)
    if not (rt and client):
        warn("Token device-flow hết hạn, không refresh được — chạy lại `--login`.")
        return tok.get("access_token", "")
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token", "client_id": client,
        "refresh_token": rt, "scope": DELEGATED_SCOPE,
    }).encode()
    req = urllib.request.Request(
        f"{AUTHORITY}/{tenant}/oauth2/v2.0/token", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            new = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        warn(f"Refresh device-flow thất bại ({e}) — chạy lại `--login`.")
        return tok.get("access_token", "")
    tok["access_token"] = new["access_token"]
    tok["refresh_token"] = new.get("refresh_token", rt)
    tok["expires_at"] = time.time() + int(new.get("expires_in", 3600))
    TOKEN_FILE.write_text(json.dumps(tok, indent=2), encoding="utf-8")
    return tok["access_token"]


def acquire_token(env, cfg):
    """Auto-detect: client-credentials (app-only, nền) → device-flow (file) → die."""
    tenant = envget(env, TENANT_KEYS)
    client = envget(env, CLIENT_KEYS)
    secret = envget(env, SECRET_KEYS)
    auth = (env.get("SHAREPOINT_AUTH") or cfg.get("sharepoint.auth") or "auto").lower()
    if auth in ("auto", "client_credentials", "app") and tenant and client and secret:
        return _client_credentials_token(tenant, client, secret), "app-only (client-credentials)"
    if auth in ("auto", "oauth", "device") and TOKEN_FILE.exists():
        t = _device_token(env)
        if t:
            return t, "device-flow (delegated)"
    die("Chưa cấu hình kết nối SharePoint. Đặt ở ENV (~/.zshrc) hoặc tools/sharepoint-sync/.env.local "
        "(copy .env.example): SHAREPOINT_TENANT_ID + SHAREPOINT_CLIENT_ID + SHAREPOINT_CLIENT_SECRET "
        "(app-only, chạy nền) HOẶC chạy `--login` để dùng device-flow (delegated).")


def cmd_login(env, cfg):
    """Device code flow: in mã + link cho user, poll tới khi nhận token."""
    tenant = envget(env, TENANT_KEYS) or "common"
    client = envget(env, CLIENT_KEYS)
    if not client:
        die("Thiếu SHAREPOINT_CLIENT_ID (app đăng ký Azure AD) để chạy device-flow.")
    data = urllib.parse.urlencode({"client_id": client, "scope": DELEGATED_SCOPE}).encode()
    req = urllib.request.Request(
        f"{AUTHORITY}/{tenant}/oauth2/v2.0/devicecode", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        dc = json.loads(r.read())
    print(f"🔑 Mở {dc['verification_uri']} và nhập mã: {dc['user_code']}", flush=True)
    interval = int(dc.get("interval", 5))
    deadline = time.time() + int(dc.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(interval)
        poll = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": client, "device_code": dc["device_code"],
        }).encode()
        preq = urllib.request.Request(
            f"{AUTHORITY}/{tenant}/oauth2/v2.0/token", data=poll,
            headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        try:
            with urllib.request.urlopen(preq, timeout=TIMEOUT) as r:
                tok = json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode("utf-8", "replace") or "{}")
            if body.get("error") in ("authorization_pending", "slow_down"):
                continue
            die(f"Đăng nhập thất bại: {body.get('error_description', body.get('error'))}")
        TOKEN_FILE.write_text(json.dumps({
            "access_token": tok["access_token"],
            "refresh_token": tok.get("refresh_token", ""),
            "expires_at": time.time() + int(tok.get("expires_in", 3600)),
            "tenant": tenant, "client": client,
        }, indent=2), encoding="utf-8")
        print("✅ Đã lưu token device-flow (.oauth-token.json).", flush=True)
        return 0
    die("Hết thời gian chờ đăng nhập device-flow.")


# ─────────────────────────── Site / Drive / Map ────────────────────────────
def host_of(base_url: str) -> str:
    netloc = urllib.parse.urlparse(base_url).netloc
    return netloc or base_url.replace("https://", "").replace("http://", "").strip("/")


def resolve_site(g: Graph, base_url: str, site_name: str) -> dict:
    host = host_of(base_url)
    path = f"/sites/{host}:/sites/{urllib.parse.quote(site_name)}" if site_name else f"/sites/{host}"
    _st, data = g.get(path)
    return data  # có "id", "webUrl"


def resolve_drive(g: Graph, site_id: str, library: str, drive_id: str) -> str:
    if drive_id:
        return drive_id
    if library:
        _st, data = g.get(f"/sites/{site_id}/drives")
        for d in data.get("value", []):
            if d.get("name", "").lower() == library.lower():
                return d["id"]
        warn(f"Không thấy thư viện '{library}' — dùng thư viện mặc định.")
    _st, d = g.get(f"/sites/{site_id}/drive")
    return d["id"]


def sysdir(cfg) -> Path:
    d = cs.vault_dir(cfg) / "_system" / "sharepoint"
    d.mkdir(parents=True, exist_ok=True)
    return d


def map_path(cfg, host, site) -> Path:
    slug = re.sub(r"[^\w.-]+", "-", f"{host}-{site or 'root'}").strip("-")
    return sysdir(cfg) / f"sharepoint-map-{slug}.json"


def load_map(p: Path) -> dict:
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"files": {}}


def save_map(p: Path, mp: dict):
    mp["generated_at"] = cs.now_iso()
    p.write_text(json.dumps(mp, ensure_ascii=False, indent=2), encoding="utf-8")


def content_hash(title, body) -> str:
    return "sha256:" + hashlib.sha256((title + "\n" + body).encode("utf-8")).hexdigest()


def slugify(title: str) -> str:
    s = re.sub(r"[^\w.-]+", "-", title, flags=re.UNICODE).strip("-")[:90]
    return s or "note"


def unique_name(title, kb_id, used: set) -> str:
    base = slugify(title)
    if base.lower().endswith(".md"):
        base = base[:-3]
    name = f"{base}.md"
    if name in used:
        name = f"{base}-{hashlib.sha1(kb_id.encode()).hexdigest()[:6]}.md"
    used.add(name)
    return name


def _drive_root(site_id, drive_id):
    return f"/sites/{site_id}/drives/{drive_id}"


# ──────────────────────────────── PUSH ─────────────────────────────────────
def cmd_push(env, cfg, args):
    perm = (cfg.get("sharepoint.permission") or "read_write").lower()
    if perm == "read_only" and not args.dry_run:
        die("sharepoint.permission = read_only → KHÔNG được --push (chỉ pull). Sửa config nếu cần đẩy.")

    source = args.source or cfg.get("sharepoint.push.source") or "both"
    scope = args.scope or cfg.get("sharepoint.push.scope") or ""
    subdir = (args.subdir if args.subdir is not None else cfg.get("sharepoint.push.subdir") or "").strip("/")
    site_name = args.site or cfg.get("sharepoint.site_name") or ""
    base_url = cfg.get("sharepoint.base_url") or env.get("SHAREPOINT_BASE_URL") or ""
    host = host_of(base_url)

    notes = cs.collect_notes(cfg, source, scope)
    mpath = map_path(cfg, host, site_name)
    mp = load_map(mpath)
    files = mp.setdefault("files", {})

    used = {r.get("name") for r in files.values() if r.get("name")}
    plan = []  # (kb_id, title, body, ch, name, rec)
    for path in notes:
        kb_id, title, body = cs.parse_note(path)
        ch = content_hash(title, body)
        rec = files.get(kb_id)
        name = rec.get("name") if rec else unique_name(title, kb_id, used)
        plan.append((kb_id, title, body, ch, name, rec))
    current = {p[0] for p in plan}
    deletions = [(kid, r) for kid, r in files.items() if kid not in current]

    creates = [p for p in plan if not p[5]]
    updates = [p for p in plan if p[5] and p[5].get("content_hash") != p[3]]
    skips = [p for p in plan if p[5] and p[5].get("content_hash") == p[3]]

    if args.dry_run:
        print(f"[dry-run] SharePoint {host}/{site_name or 'root'} (folder='{subdir or '/'}'):")
        for p in creates:
            print(f"  + tạo   {p[4]}")
        for p in updates:
            print(f"  ~ cập nhật {p[4]}")
        for kid, r in deletions:
            print(f"  - xóa   {r.get('name', kid)}")
        print(f"  = bỏ qua {len(skips)} (không đổi). Tổng: +{len(creates)} ~{len(updates)} "
              f"-{len(deletions)} ={len(skips)}.")
        return 0

    token, label = acquire_token(env, cfg)
    g = Graph(token, label)
    site = resolve_site(g, base_url, site_name)
    drive_id = resolve_drive(g, site["id"], cfg.get("sharepoint.library") or "", cfg.get("sharepoint.drive_id") or "")
    root = _drive_root(site["id"], drive_id)

    created = updated = deleted = 0
    errors = 0
    for kb_id, title, body, ch, name, rec in plan:
        if rec and rec.get("content_hash") == ch and not args.force:
            continue
        rel = f"{subdir}/{name}" if subdir else name
        enc = urllib.parse.quote(rel, safe="/")
        try:
            _st, item = g.put_raw(f"{root}/root:/{enc}:/content", body.encode("utf-8"))
        except cs.ApiError as e:
            warn(f"Đẩy '{name}' lỗi: {e}")
            errors += 1
            continue
        files[kb_id] = {
            "item_id": item.get("id", ""),
            "name": name,
            "etag": item.get("eTag", ""),
            "web_url": item.get("webUrl", ""),
            "content_hash": ch,
            "source_path": _note_src(kb_id, name),
            "last_pushed_at": cs.now_iso(),
        }
        if rec:
            updated += 1
        else:
            created += 1
    for kid, r in deletions:
        iid = r.get("item_id")
        if iid:
            try:
                g.delete(f"{root}/items/{iid}")
            except cs.ApiError as e:
                warn(f"Xóa '{r.get('name', kid)}' lỗi: {e}")
                errors += 1
                continue
        files.pop(kid, None)
        deleted += 1

    mp["site_url"] = site.get("webUrl", "")
    mp["drive_id"] = drive_id
    save_map(mpath, mp)
    print(f"SharePoint sync ({label}): +{created} ~{updated} -{deleted}"
          + (f" · {errors} lỗi" if errors else ""))
    return 2 if errors else 0


def _note_src(kb_id, name):
    # kb_id thường là đường dẫn tương đối repo (nếu note không có jira_key/feature_id).
    return kb_id if ("/" in kb_id or kb_id.endswith(".md")) else name


# ──────────────────────────────── PULL ─────────────────────────────────────
def cmd_pull(env, cfg, args):
    site_name = args.site or cfg.get("sharepoint.site_name") or ""
    base_url = cfg.get("sharepoint.base_url") or env.get("SHAREPOINT_BASE_URL") or ""
    subdir = (args.subdir if args.subdir is not None else cfg.get("sharepoint.pull.subdir") or "").strip("/")
    into = Path(args.into or cfg.get("sharepoint.pull.into") or (cs.vault_dir(cfg) / "SharePoint"))
    if not into.is_absolute():
        into = REPO_ROOT / into
    into.mkdir(parents=True, exist_ok=True)

    token, label = acquire_token(env, cfg)
    g = Graph(token, label)
    site = resolve_site(g, base_url, site_name)
    drive_id = resolve_drive(g, site["id"], cfg.get("sharepoint.library") or "", cfg.get("sharepoint.drive_id") or "")
    root = _drive_root(site["id"], drive_id)

    start = f"{root}/root:/{urllib.parse.quote(subdir, safe='/')}:/children" if subdir else f"{root}/root/children"
    count = 0
    count = _pull_children(g, root, start, into, count, args.dry_run)
    print(f"SharePoint pull ({label}): {count} file .md → {into}")
    return 0


def _pull_children(g, root, listing_path, dest: Path, count, dry):
    _st, data = g.get(listing_path)
    for it in data.get("value", []):
        if it.get("folder"):
            sub = f"{root}/items/{it['id']}/children"
            count = _pull_children(g, root, sub, dest, count, dry)
            continue
        name = it.get("name", "")
        if not name.lower().endswith(".md"):
            continue
        count += 1
        if dry:
            print(f"  · {name}")
            continue
        url = it.get("@microsoft.graph.downloadUrl")
        try:
            if url:
                _st, raw = g.get_bytes(url)
            else:
                _st, raw = g.get_bytes(f"{root}/items/{it['id']}/content")
        except cs.ApiError as e:
            warn(f"Tải '{name}' lỗi: {e}")
            continue
        text = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
        if not FM_RE.match(text):
            fm = (f"---\nsource: sharepoint\nsharepoint_item_id: {it.get('id','')}\n"
                  f"sharepoint_etag: {it.get('eTag','')}\nimported_at: {cs.now_iso()}\n---\n\n")
            text = fm + text
        (dest / name).write_text(text, encoding="utf-8")
    return count


# ──────────────────────────────── CHECK ────────────────────────────────────
def cmd_check(env, cfg):
    base_url = cfg.get("sharepoint.base_url") or env.get("SHAREPOINT_BASE_URL") or ""
    site_name = cfg.get("sharepoint.site_name") or ""
    if not base_url:
        die("Thiếu sharepoint.base_url trong config (vd https://<tenant>.sharepoint.com).")
    token, label = acquire_token(env, cfg)
    g = Graph(token, label)
    try:
        site = resolve_site(g, base_url, site_name)
    except cs.ApiError as e:
        die(f"Kết nối SharePoint thất bại ({label}): {e}")
    drive_id = resolve_drive(g, site["id"], cfg.get("sharepoint.library") or "", cfg.get("sharepoint.drive_id") or "")
    print(f"✅ SharePoint OK — {label} · site {site.get('webUrl','')} · drive {drive_id[:12]}…")
    return 0


# ──────────────────────────────── main ─────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Đồng bộ KB ↔ SharePoint (Microsoft Graph).")
    ap.add_argument("--check", action="store_true", help="Kiểm tra kết nối Graph + site/drive")
    ap.add_argument("--login", action="store_true", help="Đăng nhập device-flow (delegated)")
    ap.add_argument("--push", action="store_true", help="Đẩy KB → SharePoint (idempotent)")
    ap.add_argument("--pull", action="store_true", help="Kéo .md từ SharePoint → <vault>/SharePoint/")
    ap.add_argument("--dry-run", action="store_true", help="Xem trước, không ghi")
    ap.add_argument("--force", action="store_true", help="Bỏ qua so hash, đẩy lại tất cả")
    ap.add_argument("--source", choices=["vault", "docs", "both"], help="Nguồn note (mặc định config)")
    ap.add_argument("--scope", help="Lọc theo thư mục/glob (tùy chọn)")
    ap.add_argument("--site", help="Tên site SharePoint (override config)")
    ap.add_argument("--library", help="Tên thư viện tài liệu (override config)")
    ap.add_argument("--subdir", help="Thư mục con trong thư viện (override config)")
    ap.add_argument("--into", help="Thư mục đích khi --pull")
    args = ap.parse_args()

    env = cs.load_env(HERE / ".env.local")
    cfg = cs.load_config(CONFIG)
    if args.library:
        cfg["sharepoint.library"] = args.library

    if args.login:
        return cmd_login(env, cfg)
    if args.check:
        return cmd_check(env, cfg)
    if args.push:
        return cmd_push(env, cfg, args)
    if args.pull:
        return cmd_pull(env, cfg, args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
