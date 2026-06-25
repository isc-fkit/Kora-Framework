#!/usr/bin/env python3
"""
import_excel.py — Nạp 1 bảng TASK/TIẾN ĐỘ (Excel .xlsx / Google Sheet / CSV / JSON rows) thành
note trong vault, CÙNG ĐỊNH DẠNG `import_jira.py` → báo cáo (build_report.py) GỘP CHUNG với Jira.

CHỈ thư viện chuẩn Python 3 (zipfile, xml.etree, csv, json...). KHÔNG cần cài gì.

2 đường nạp:
  • Local .xlsx :  python3 import_excel.py --file ke-hoach.xlsx [--sheet "Sheet1"]
  • Rows sẵn   :  python3 import_excel.py --from-rows rows.csv     (hoặc rows.json = list[dict])
                  (dùng khi Claude lấy dữ liệu Google Sheet/SharePoint qua MCP rồi chuẩn hoá thành CSV/JSON)

Mapping cột (header người dùng → field báo cáo): tự nhận theo tên cột phổ biến (Việt/Anh); override bằng
  --map '{"Tên cột của bạn":"assignee", ...}'  (hoặc --map map.json).

Mỗi DÒNG → 1 note `source: excel`. Mỗi lần nạp GHI ĐÈ TOÀN BỘ thư mục của nguồn đó (idempotent, không nhân đôi).
"""
import argparse
import csv
import json
import os
import re
import ssl
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, date
from pathlib import Path
from xml.etree import ElementTree as ET

NOW = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
TODAY = date.today().isoformat()
XLSX_EPOCH = date(1899, 12, 30)   # mốc serial-date của Excel

# Thư mục theo loại (khớp import_jira để report walk như nhau).
TYPE_DIRS = {"epic": "02_Epics", "user_story": "03_UserStories", "story": "03_UserStories",
             "task": "04_Tasks", "bug": "05_Bugs", "sub-task": "06_SubTasks", "subtask": "06_SubTasks"}
RAW_DIR = "08_RawIssues"
IMPORT_ROOT = "07_Imported"   # gốc cho nguồn excel/sheet: 07_Imported/<source_id>/ (ghi đè trọn mỗi lần)

# Nhận diện type từ chữ người dùng (substring, không phân biệt hoa thường).
_TYPE_MAP = {"epic": "epic", "story": "user_story", "us": "user_story", "sub": "sub-task",
             "bug": "bug", "lỗi": "bug", "defect": "bug", "task": "task", "công việc": "task",
             "feature": "user_story", "request": "user_story"}

# Mapping MẶC ĐỊNH: field đích ← các tên cột phổ biến (lowercase). Override bằng --map.
DEFAULT_SYNONYMS = {
    "excel_key": ["key", "id", "mã", "ma", "task id", "item", "code", "stt"],
    "summary": ["summary", "title", "tên", "ten", "name", "task", "công việc", "tiêu đề", "nội dung", "subject"],
    "type": ["type", "loại", "loai", "issue type", "kind"],
    "status": ["status", "trạng thái", "trang thai", "tình trạng", "tinh trang", "state"],
    "assignee": ["assignee", "người làm", "nguoi lam", "phụ trách", "phu trach", "owner", "thực hiện", "thuc hien", "pic"],
    "reporter": ["reporter", "người tạo", "nguoi tao", "báo cáo", "creator", "created by"],
    "project": ["project", "dự án", "du an", "prj"],
    "story_points": ["story points", "storypoints", "points", "điểm", "diem", "sp", "point"],
    "complexity": ["complexity", "độ phức tạp", "do phuc tap", "phức tạp", "phuc tap"],
    "estimate_hours": ["estimate", "ước tính", "uoc tinh", "estimate hours", "est", "estimated", "giờ ước tính"],
    "spent_hours": ["spent", "đã log", "da log", "logged", "actual", "giờ thực", "gio thuc", "thời gian thực"],
    "remaining_hours": ["remaining", "còn lại", "con lai", "remain"],
    "duedate": ["duedate", "due date", "due", "hạn", "han", "deadline", "ngày hết hạn", "ngay het han"],
    "sprint_name": ["sprint", "sprint name", "iteration"],
    "sprint_state": ["sprint state", "trạng thái sprint"],
    "sprint_end": ["sprint end", "kết thúc sprint", "ngày kết thúc sprint"],
    "status_category": ["status category", "nhóm trạng thái", "category"],
    "updated": ["updated", "cập nhật", "cap nhat", "ngày cập nhật", "last updated", "modified"],
}
DATE_FIELDS = {"duedate", "sprint_end", "updated"}
HOURS_FIELDS = {"estimate_hours": "time_estimate_s", "spent_hours": "time_spent_s", "remaining_hours": "time_remaining_s"}


def die(msg, code=1):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


# ── Vault resolution (mirror build_report: --vault → OBSIDIAN_VAULT → vault_path trong config; theo cwd) ──
def resolve_vault(cli_vault):
    data = os.getcwd()
    if cli_vault:
        v = cli_vault
    elif os.getenv("OBSIDIAN_VAULT"):
        v = os.getenv("OBSIDIAN_VAULT")
    else:
        cfg = os.path.join(data, "config", "factory-config.yaml")
        v = None
        if os.path.exists(cfg):
            m = re.search(r"^\s*vault_path:\s*(.+)$", open(cfg, encoding="utf-8").read(), re.M)
            if m:
                v = m.group(1).strip().strip('"').strip("'")
        if not v:
            die("Không tìm thấy vault. Truyền --vault <path> hoặc đặt vault_path trong config/factory-config.yaml.")
    v = os.path.expanduser(v)
    if not os.path.isabs(v):
        v = os.path.normpath(os.path.join(data, v))
    if not os.path.isdir(v):
        die(f"Vault không tồn tại: {v}")
    return v


def safe_name(key, summary, maxlen=80):
    s = (summary or "untitled").strip()
    s = re.sub(r'[\\/:*?"<>|#\[\]^]', "", s)
    s = re.sub(r"\s+", "-", s)
    s = unicodedata.normalize("NFC", s)
    return f"{key}_{s[:maxlen].rstrip('-')}"


def norm_type(raw):
    t = (raw or "").strip().lower()
    for pat, nt in _TYPE_MAP.items():
        if pat in t:
            return nt
    return "task" if not t else "issue"   # trống → coi như task (có log giờ); lạ → issue (08_RawIssues)


def infer_status_category(status):
    s = (status or "").strip().lower()
    if not s:
        return ""
    if any(k in s for k in ("done", "closed", "complete", "resolved", "hoàn thành", "hoan thanh", "xong", "đóng")):
        return "done"
    if any(k in s for k in ("progress", "doing", "review", "đang", "dang", "thực hiện", "test", "wip")):
        return "in_progress"
    if any(k in s for k in ("todo", "to do", "open", "backlog", "new", "chưa", "chua", "mới", "moi", "pending")):
        return "todo"
    return ""


# ── XLSX parser (stdlib) ──────────────────────────────────────────────────────
def _ln(tag):  # local-name (bỏ namespace)
    return tag.rsplit("}", 1)[-1]


def _col_to_idx(ref):  # "B3" → 1 (0-based cột)
    letters = re.match(r"[A-Z]+", ref or "")
    if not letters:
        return 0
    idx = 0
    for ch in letters.group(0):
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def parse_xlsx(path, sheet_name=None):
    """Trả (headers, rows) — rows = list[dict header→value(str)]."""
    if not os.path.exists(path):
        die(f"Không thấy file Excel: {path}")
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        die(f"File không phải .xlsx hợp lệ (zip hỏng): {path}")
    names = zf.namelist()
    # 1) shared strings
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in root:
            if _ln(si.tag) != "si":
                continue
            shared.append("".join(t.text or "" for t in si.iter() if _ln(t.tag) == "t"))
    # 2) chọn sheet
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels_raw = zf.read("xl/_rels/workbook.xml.rels")
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(rels_raw)}
    sheet_target = None
    sheets = [s for s in wb.iter() if _ln(s.tag) == "sheet"]
    for s in sheets:
        rid = next((s.get(a) for a in s.attrib if _ln(a) == "id"), None)
        if sheet_name is None or (s.get("name") or "").strip() == sheet_name.strip():
            tgt = rels.get(rid)
            if tgt:
                sheet_target = tgt if tgt.startswith("xl/") else "xl/" + tgt.lstrip("/")
                break
    if not sheet_target:
        avail = ", ".join((s.get("name") or "?") for s in sheets)
        die(f"Không thấy sheet '{sheet_name}'. Có: {avail}" if sheet_name else "Không xác định được sheet.")
    # 3) parse rows
    ws = ET.fromstring(zf.read(sheet_target))
    grid = []
    for row in (e for e in ws.iter() if _ln(e.tag) == "row"):
        cells = {}
        maxc = -1
        for c in (e for e in row if _ln(e.tag) == "c"):
            ci = _col_to_idx(c.get("r", ""))
            t = c.get("t")
            vtext = ""
            for ch in c:
                if _ln(ch.tag) == "v":
                    vtext = ch.text or ""
                elif _ln(ch.tag) == "is":
                    vtext = "".join(x.text or "" for x in ch.iter() if _ln(x.tag) == "t")
            if t == "s" and vtext.isdigit():
                val = shared[int(vtext)] if int(vtext) < len(shared) else ""
            else:
                val = vtext
            cells[ci] = val.strip()
            maxc = max(maxc, ci)
        grid.append([cells.get(i, "") for i in range(maxc + 1)] if maxc >= 0 else [])
    # bỏ dòng trống đầu, lấy dòng có dữ liệu đầu tiên làm header
    grid = [r for r in grid if any(str(x).strip() for x in r)]
    if not grid:
        die("Sheet rỗng — không có dữ liệu.")
    headers = [str(h).strip() for h in grid[0]]
    rows = []
    for r in grid[1:]:
        rows.append({headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))})
    return headers, rows


def read_rows_file(path):
    """--from-rows: CSV (header dòng đầu) hoặc JSON (list[dict])."""
    if not os.path.exists(path):
        die(f"Không thấy file rows: {path}")
    if path.lower().endswith(".json"):
        data = json.loads(open(path, encoding="utf-8").read())
        if not isinstance(data, list):
            die("File JSON rows phải là MẢNG các object {cột: giá trị}.")
        headers = list(data[0].keys()) if data else []
        return headers, [{k: ("" if v is None else str(v)) for k, v in row.items()} for row in data]
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        rows = [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in rd]
    return (rd.fieldnames or []), rows


GRAPH = "https://graph.microsoft.com/v1.0"
LOGIN = "https://login.microsoftonline.com"


def _proxy_opener():
    """Opener honor HTTPS_PROXY (mạng công ty); proxy rỗng → no-proxy rõ ràng. TLS verify giữ bật."""
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    ph = urllib.request.ProxyHandler({"https": proxy, "http": proxy}) if proxy else urllib.request.ProxyHandler({})
    return urllib.request.build_opener(ph, urllib.request.HTTPSHandler(context=ssl.create_default_context())), bool(proxy)


def _save_bytes(data, src="URL"):
    """Lưu bytes ra temp + tự nhận định dạng theo magic. Trả (path, kind)."""
    if data[:4] == b"PK\x03\x04":          # zip magic → .xlsx
        kind, suffix = "xlsx", ".xlsx"
    else:
        head = data.lstrip()[:1]
        kind, suffix = ("json", ".json") if head in (b"[", b"{") else ("csv", ".csv")
    fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="kora-excel-")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    print(f"ℹ️  Đã tải {len(data)//1024}KB ← {src} (định dạng: {kind})")
    return tmp, kind


def download_to_temp(url):
    """Tải file (.xlsx/.csv/.json) từ URL về temp — SharePoint downloadUrl / Google publish-CSV. Honor proxy + timeout."""
    opener, _ = _proxy_opener()
    try:
        with opener.open(url, timeout=120) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        die(f"Tải URL lỗi HTTP {e.code} (downloadUrl có thể đã hết hạn — lấy lại từ read_resource).")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        die(f"Không tải được URL ({e}). Nếu mạng công ty chặn, đặt HTTPS_PROXY=http://proxy.hcm.fpt.vn:80 rồi thử lại.")
    return _save_bytes(data, "URL")


# ── Microsoft Graph 365 (quyền READ) — tải Excel trên SharePoint/OneDrive về parse ô chuẩn ──
def _env_or_file(*keys):
    """Đọc creds từ os.getenv → tools/sharepoint-sync/.env.local (bỏ PASTE_)."""
    envf = {}
    p = os.path.join(os.getcwd(), "tools", "sharepoint-sync", ".env.local")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                envf[k.strip()] = v.strip()
    for k in keys:
        v = os.getenv(k) or envf.get(k)
        if v and not v.strip().startswith("PASTE_"):
            return v.strip()
    return None


def graph_token():
    """Lấy Graph access token (READ). Ưu tiên token thô (MS_GRAPH_TOKEN) → app-only client-credentials
    (SHAREPOINT_TENANT_ID/CLIENT_ID/CLIENT_SECRET, cần admin consent Sites.Read.All) → device-flow token file."""
    raw = _env_or_file("MS_GRAPH_TOKEN", "GRAPH_TOKEN", "SHAREPOINT_TOKEN")
    if raw:
        return raw
    tenant = _env_or_file("SHAREPOINT_TENANT_ID", "AZURE_TENANT_ID")
    client = _env_or_file("SHAREPOINT_CLIENT_ID", "AZURE_CLIENT_ID")
    secret = _env_or_file("SHAREPOINT_CLIENT_SECRET", "AZURE_CLIENT_SECRET")
    if tenant and client and secret:
        data = urllib.parse.urlencode({
            "client_id": client, "client_secret": secret,
            "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials",
        }).encode("ascii")
        req = urllib.request.Request(f"{LOGIN}/{tenant}/oauth2/v2.0/token", data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        opener, _ = _proxy_opener()
        try:
            with opener.open(req, timeout=30) as r:
                tok = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            die(f"Lấy Graph token (client-credentials) lỗi HTTP {e.code} — kiểm tra TENANT/CLIENT/SECRET + "
                "admin consent quyền **Sites.Read.All** (Application).")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            die(f"Không lấy được Graph token ({e}). Đặt HTTPS_PROXY nếu mạng công ty chặn.")
        if tok.get("access_token"):
            return tok["access_token"]
        die(f"Graph không trả access_token: {tok.get('error_description', tok)}")
    # device-flow token file (sync_sharepoint.py --login)
    df = os.path.join(os.getcwd(), "tools", "sharepoint-sync", ".oauth-token.json")
    if os.path.exists(df):
        t = (json.load(open(df, encoding="utf-8")) or {}).get("access_token")
        if t:
            return t
    die("Chưa cấu hình Graph 365. Đặt **SHAREPOINT_TENANT_ID/CLIENT_ID/CLIENT_SECRET** (app Azure AD có quyền "
        "**Sites.Read.All** + admin consent) ở ~/.zshrc hoặc tools/sharepoint-sync/.env.local; hoặc chạy device-flow "
        "`python3 tools/sharepoint-sync/sync_sharepoint.py --login`.")


def graph_download(drive_id, item_id):
    """Tải bytes file qua Graph: GET /drives/{driveId}/items/{itemId}/content (Bearer). Honor proxy."""
    token = graph_token()
    url = f"{GRAPH}/drives/{drive_id}/items/{item_id}/content"
    opener, _ = _proxy_opener()
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with opener.open(req, timeout=120) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        die(f"Tải file qua Graph lỗi HTTP {e.code} — token thiếu quyền Sites.Read.All, hoặc driveId/itemId sai.")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        die(f"Không tải được qua Graph ({e}). Đặt HTTPS_PROXY nếu mạng công ty chặn.")
    return _save_bytes(data, "Graph 365")


# ── Mapping header → field ────────────────────────────────────────────────────
def build_field_map(headers, override):
    """Trả dict {field_đích: header_thực}. Ưu tiên override (header→field), rồi synonyms mặc định."""
    field_of_header = {}   # header(lower) → field (từ override, đảo chiều)
    for h, fld in (override or {}).items():
        field_of_header[h.strip().lower()] = fld
    fmap = {}
    for h in headers:
        hl = (h or "").strip().lower()
        if not hl:
            continue
        if hl in field_of_header:
            fmap.setdefault(field_of_header[hl], h)
    # synonyms mặc định cho field chưa map
    for field, syns in DEFAULT_SYNONYMS.items():
        if field in fmap:
            continue
        for h in headers:
            hl = (h or "").strip().lower()
            if hl in syns or any(hl == s for s in syns):
                fmap[field] = h
                break
    return fmap


def to_date(v):
    s = str(v).strip()
    if not s:
        return ""
    if re.fullmatch(r"\d+(\.0+)?", s):   # serial-date Excel
        try:
            return (XLSX_EPOCH + timedelta(days=int(float(s)))).isoformat()
        except (ValueError, OverflowError):
            return ""
    m = re.search(r"\d{4}-\d{2}-\d{2}", s)   # đã là ISO
    if m:
        return m.group(0)
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return s[:10]


def to_num(v):
    s = str(v).strip().replace(",", ".")
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        f = float(s)
        return int(f) if f.is_integer() else f
    return None


def row_to_note(row, fmap, default_project, src_id, idx):
    g = lambda fld: str(row.get(fmap[fld], "")).strip() if fld in fmap else ""
    key = g("excel_key") or f"{src_id}-{idx}"
    key = re.sub(r"[^\w.-]+", "-", key).strip("-") or f"{src_id}-{idx}"
    summary = g("summary") or key
    itype = norm_type(g("type"))
    status = g("status")
    project = g("project") or default_project or src_id
    cat = g("status_category").lower() if "status_category" in fmap else ""
    if cat not in ("todo", "in_progress", "done"):
        cat = infer_status_category(status)

    fm = ["---", f"type: {itype}", "source: excel", f"excel_key: {key}",
          f"jira_key: {key}",            # chuẩn hoá: build_report downstream dùng jira_key
          f"source_id: {src_id}", f"project: {project}", f"status: {status}"]
    if cat:
        fm.append(f"status_category: {cat}")
    for fld in ("assignee", "reporter", "sprint_name", "sprint_state"):
        val = g(fld)
        if val:
            fm.append(f"{fld}: {json.dumps(val, ensure_ascii=False)}")
    for fld in ("duedate", "sprint_end", "updated"):
        val = to_date(g(fld)) if g(fld) else ""
        if val:
            fm.append(f"{fld}: {json.dumps(val, ensure_ascii=False) if fld == 'sprint_end' else val}")
    for fld in ("story_points", "complexity"):
        n = to_num(g(fld))
        if n is not None:
            fm.append(f"{fld}: {n}")
    for hours_fld, sec_fld in HOURS_FIELDS.items():
        n = to_num(g(hours_fld))
        if n is not None:
            fm.append(f"{sec_fld}: {int(float(n) * 3600)}")
    fm += [f"imported_at: {NOW}", "---", "",
           f"# {key} — {summary}", "",
           "## Metadata", "",
           f"- Loại: {itype}", f"- Trạng thái: {status}",
           f"- Nguồn: Excel/Sheet ({src_id})", ""]
    return key, itype, "\n".join(fm) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Nạp bảng Excel/Sheet/CSV → note vault (gộp báo cáo với Jira).")
    ap.add_argument("--file", help="Đường dẫn .xlsx local.")
    ap.add_argument("--sheet", help="Tên sheet (mặc định: sheet đầu).")
    ap.add_argument("--from-rows", dest="from_rows", help="File rows đã chuẩn hoá: .csv hoặc .json (list[dict]).")
    ap.add_argument("--from-url", dest="from_url", help="Tải file .xlsx/.csv/.json từ URL (SharePoint downloadUrl từ read_resource, hoặc Google publish-CSV). Honor HTTPS_PROXY.")
    ap.add_argument("--graph-item", dest="graph_item", help="Tải Excel trên SharePoint/OneDrive qua Microsoft Graph 365 (quyền READ). Dạng '<driveId>/<itemId>' (lấy từ sharepoint_search). Cần creds SHAREPOINT_* (app Azure AD, Sites.Read.All).")
    ap.add_argument("--map", dest="map_arg", help="Mapping header→field: JSON inline hoặc đường dẫn .json.")
    ap.add_argument("--project", help="Mã project mặc định gán cho mọi dòng (nếu không có cột project).")
    ap.add_argument("--source-id", dest="source_id", help="ID nguồn (mặc định theo tên file). Quyết định thư mục + marker.")
    ap.add_argument("--vault", help="Đường dẫn vault (mặc định đọc vault_path trong config).")
    args = ap.parse_args()

    if not args.file and not args.from_rows and not args.from_url and not args.graph_item:
        die("Cần --file <x.xlsx> HOẶC --from-rows <rows.csv|.json> HOẶC --from-url <url> HOẶC --graph-item <driveId>/<itemId>.")

    override = {}
    if args.map_arg:
        raw = args.map_arg
        if os.path.exists(raw):
            raw = open(raw, encoding="utf-8").read()
        try:
            override = json.loads(raw)
        except json.JSONDecodeError:
            die("--map không phải JSON hợp lệ (cần {\"Tên cột\":\"field\"}).")

    tmp_dl = None
    if args.graph_item:
        if "/" not in args.graph_item:
            die("--graph-item phải dạng '<driveId>/<itemId>' (lấy từ sharepoint_search → URI file:///{driveId}/{itemId}).")
        drive_id, item_id = args.graph_item.rsplit("/", 1)
        tmp_dl, kind = graph_download(drive_id, item_id)
        headers, rows = parse_xlsx(tmp_dl, args.sheet) if kind == "xlsx" else read_rows_file(tmp_dl)
        default_src = "sharepoint-graph"
    elif args.from_url:
        tmp_dl, kind = download_to_temp(args.from_url)
        if kind == "xlsx":
            headers, rows = parse_xlsx(tmp_dl, args.sheet)
        else:
            headers, rows = read_rows_file(tmp_dl)
        default_src = "sharepoint-excel"
    elif args.from_rows:
        headers, rows = read_rows_file(args.from_rows)
        default_src = Path(args.from_rows).stem
    else:
        headers, rows = parse_xlsx(args.file, args.sheet)
        default_src = Path(args.file).stem
    src_id = re.sub(r"[^\w.-]+", "-", (args.source_id or default_src)).strip("-") or "excel"

    fmap = build_field_map(headers, override)
    if "status" not in fmap and "summary" not in fmap:
        die(f"Không map được cột nào quan trọng (status/summary). Header: {headers}\n"
            f"   Dùng --map '{{\"Tên cột\":\"status\", \"Tên cột\":\"summary\", ...}}'.")
    print(f"ℹ️  Map cột: " + ", ".join(f"{f}←'{h}'" for f, h in fmap.items()))

    vault = resolve_vault(args.vault)
    out_dir = os.path.join(vault, IMPORT_ROOT, src_id)
    # Idempotent: xoá sạch note CŨ của nguồn này rồi ghi lại (sheet = trạng thái hiện tại đầy đủ).
    if os.path.isdir(out_dir):
        for fn in os.listdir(out_dir):
            if fn.endswith(".md"):
                os.remove(os.path.join(out_dir, fn))
    os.makedirs(out_dir, exist_ok=True)

    n = 0
    for i, row in enumerate(rows, 1):
        if not any(str(v).strip() for v in row.values()):
            continue
        key, _itype, text = row_to_note(row, fmap, args.project, src_id, i)
        fn = safe_name(key, str(row.get(fmap.get("summary", ""), "")))[:120] + ".md"
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(text)
        n += 1

    # Marker last-import cho nguồn (build_report đọc để biết độ tươi).
    sysdir = os.path.join(vault, "_system")
    os.makedirs(sysdir, exist_ok=True)
    with open(os.path.join(sysdir, f"last-import-excel-{src_id}.txt"), "w", encoding="utf-8") as fh:
        fh.write(TODAY + "\n")

    if tmp_dl:
        try:
            os.remove(tmp_dl)
        except OSError:
            pass

    print(f"✅ Đã nạp {n} dòng từ nguồn '{src_id}' → {out_dir}")
    print(f"   Vault: {vault}")
    print(f"   → reindex: python3 tools/kb-indexer/build_index.py --root .  rồi build_report.py")


if __name__ == "__main__":
    main()
