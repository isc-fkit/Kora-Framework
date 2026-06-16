#!/usr/bin/env python3
"""
import_jira.py — Quét Jira → Obsidian Vault có backlink + relation graph.

Theo spec: CLAUDE_CODE_JIRA_TO_OBSIDIAN_SETUP.md (Bước 1→7).

Dùng:
  python import_jira.py                    # quét toàn bộ (theo PROJECT_KEYS)
  python import_jira.py --test             # chỉ test kết nối
  python import_jira.py --keys PROJ-102,PROJ-105   # quét riêng vài issue (merge vào vault)
  python import_jira.py --jql "parent = PROJ-101" # quét theo JQL (merge vào vault)
  python import_jira.py --per-project            # mỗi project 1 thư mục con (hoặc GROUP_BY_PROJECT=true trong .env.local)
  python import_jira.py --since 2026-06-01       # chỉ quét issue tạo/sửa từ 2026-06-01 (merge vào vault)
  python import_jira.py --since                  # quét incremental từ lần chạy trước (tự đọc mốc)

Bảo mật: chỉ dùng JIRA_PAT từ .env.local. Không in token ra log.
"""

import argparse
import base64
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# Chỉ dùng thư viện chuẩn Python — KHÔNG cần pip install gì.


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_env_local(path=None):
    """Đọc .env.local nằm CẠNH script (KEY=VALUE từng dòng), không ghi đè biến env đã có.

    Dùng đường dẫn theo vị trí FILE script — KHÔNG theo thư mục đang đứng (cwd) — để chạy
    được từ BẤT KỲ đâu (Cowork/sandbox, cron, Terminal) mà vẫn nạp đúng cấu hình. Trước đây
    path mặc định là ".env.local" tương đối theo cwd → Cowork gọi từ thư mục khác là mất config."""
    if path is None:
        # JIRA_ENV_FILE cho phép chỉ định file cấu hình khác → ĐA NGUỒN Jira: mỗi nguồn một
        # file (.env.company, .env.cloud...) và lịch sync riêng. Mặc định ".env.local".
        # Đường dẫn tương đối → neo theo thư mục script.
        path = os.environ.get("JIRA_ENV_FILE") or ".env.local"
        if not os.path.isabs(path):
            path = os.path.join(SCRIPT_DIR, path)
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env_local()

BASE_URL = (os.getenv("JIRA_BASE_URL") or "").rstrip("/")
PAT = os.getenv("JIRA_PAT") or ""
EMAIL = (os.getenv("JIRA_EMAIL") or "").strip()
# auto = tự nhận diện: có JIRA_EMAIL hoặc URL *.atlassian.net → Cloud (Basic email:token);
# còn lại → Server/DC (Bearer PAT). Ép bằng JIRA_AUTH_MODE = cloud | server
AUTH_MODE = (os.getenv("JIRA_AUTH_MODE") or "auto").strip().lower()
# Vault: đường dẫn tương đối → neo theo thư mục script (tools/jira-to-obsidian/), KHÔNG
# theo cwd — để Cowork chạy từ đâu cũng GHI đúng chỗ như khi chạy bằng quet-jira.command.
_vault_raw = os.getenv("OBSIDIAN_VAULT") or "./KB-Vault"
VAULT = _vault_raw if os.path.isabs(_vault_raw) else os.path.normpath(os.path.join(SCRIPT_DIR, _vault_raw))
PROJECT_KEYS = [k.strip() for k in (os.getenv("PROJECT_KEYS") or "").split(",") if k.strip()]
AC_FIELD = os.getenv("JIRA_AC_FIELD") or ""
BR_FIELD = os.getenv("JIRA_BR_FIELD") or ""
# Mặc định BẬT gom theo project; chỉ tắt khi user ghi rõ GROUP_BY_PROJECT=false
PER_PROJECT = (os.getenv("GROUP_BY_PROJECT") or "true").strip().lower() not in ("0", "false", "no")
# Mặc định CÀO HẾT mọi field (fields=*all + map tên custom field). Tắt: JIRA_FETCH_ALL_FIELDS=false
ALL_FIELDS = (os.getenv("JIRA_FETCH_ALL_FIELDS") or "true").strip().lower() not in ("0", "false", "no")
FIELD_MAP = {}  # id field -> tên người-đọc (điền từ /rest/api/2/field khi chạy quét)

def _is_cloud():
    if AUTH_MODE == "cloud":
        return True
    if AUTH_MODE == "server":
        return False
    return bool(EMAIL) or "atlassian.net" in BASE_URL


def _auth_header():
    if _is_cloud():
        # Atlassian Cloud: Basic base64(email:api_token)
        token = base64.b64encode(f"{EMAIL}:{PAT}".encode()).decode()
        return f"Basic {token}"
    return f"Bearer {PAT}"  # Jira Server / Data Center: Bearer PAT


HEADERS = {"Authorization": _auth_header(), "Accept": "application/json"}
NOW = datetime.now(timezone.utc).isoformat()

# --- Cấu trúc thư mục vault: mặc định bên dưới, override được bằng env (dynamic) ---
# VAULT_DIRS trong .env.local = JSON, vd: {"epic":"Epics","user_story":"Stories","index":"_Index"}
_DEFAULT_DIRS = {
    "index": "00_Index", "projects": "01_Projects", "epic": "02_Epics",
    "story": "03_UserStories", "user_story": "03_UserStories", "task": "04_Tasks",
    "bug": "05_Bugs", "sub-task": "06_SubTasks", "subtask": "06_SubTasks",
    "raw": "08_RawIssues", "system": "_system",
}
try:
    _DEFAULT_DIRS.update(json.loads(os.getenv("VAULT_DIRS") or "{}"))
except json.JSONDecodeError:
    print("Cảnh báo: VAULT_DIRS trong .env.local không phải JSON hợp lệ — dùng tên mặc định.")

DIRS = _DEFAULT_DIRS
TYPE_DIRS = {k: DIRS[k] for k in ("epic", "story", "user_story", "task", "bug", "sub-task", "subtask")}
ALL_DIRS = sorted(set(DIRS.values()))


def die(msg):
    print(f"LỖI: {msg}")
    sys.exit(1)


def check_config():
    if not BASE_URL:
        die("Thiếu JIRA_BASE_URL trong .env.local")
    if not PAT or PAT == "PASTE_TOKEN_MOI_VAO_DAY":
        die("Thiếu JIRA_PAT trong .env.local (tự dán token vào file, không dán vào chat)")
    if _is_cloud() and not EMAIL:
        die("Jira Cloud (*.atlassian.net) cần JIRA_EMAIL trong .env.local "
            "(email tài khoản Atlassian) + JIRA_PAT là API token.")


def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            die("401 Unauthorized — token sai/hết hạn. Tạo token mới trong Jira.")
        if e.code == 403:
            die("403 Forbidden — account không có quyền xem. Cần quyền Browse Project.")
        if e.code == 404:
            die(f"404 Not Found — kiểm tra JIRA_BASE_URL hoặc key/JQL ({path}).")
        if e.code == 410:
            die("410 Gone — endpoint Jira đã bị gỡ. Cloud đã bỏ /rest/api/2/search; "
                "script dùng /rest/api/3/search/jql cho Cloud. Nếu vẫn gặp, cập nhật tool.")
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:500]
        except Exception:
            pass
        die(f"Jira trả về {e.code}: {body}")
    except urllib.error.URLError as e:
        die(f"Không kết nối được Jira ({e.reason}). Kiểm tra VPN/LAN/proxy.")


def md_escape(v):
    """Chuyển giá trị Jira (string / dict ADF / list) thành text an toàn cho Markdown."""
    if v is None:
        return ""
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, indent=2)
    if isinstance(v, list):
        return "\n".join(str(x) for x in v)
    return str(v)


def safe_name(key, summary, maxlen=80):
    s = (summary or "untitled").strip()
    s = re.sub(r'[\\/:*?"<>|#\[\]^]', "", s)
    s = re.sub(r"\s+", "-", s)
    s = unicodedata.normalize("NFC", s)
    return f"{key}_{s[:maxlen].rstrip('-')}"


# Mapping tên loại issue → loại chuẩn. Override/bổ sung qua JIRA_TYPE_MAP trong .env.local
# (JSON, substring không phân biệt hoa thường), vd Jira tiếng Việt:
# JIRA_TYPE_MAP={"câu chuyện":"user_story","lỗi":"bug","công việc":"task","sử thi":"epic"}
_TYPE_MAP = {"epic": "epic", "story": "user_story", "sub": "sub-task",
             "bug": "bug", "task": "task", "defect": "bug", "improvement": "task"}
try:
    _TYPE_MAP.update({k.lower(): v for k, v in json.loads(os.getenv("JIRA_TYPE_MAP") or "{}").items()})
except json.JSONDecodeError:
    print("Cảnh báo: JIRA_TYPE_MAP không phải JSON hợp lệ — dùng mapping mặc định.")


def norm_type(issue):
    t = (issue["fields"]["issuetype"]["name"] or "").lower()
    for pat, ntype in _TYPE_MAP.items():
        if pat in t:
            return ntype
    return "issue"  # không nhận diện được → 08_RawIssues


def get_parent(issue):
    f = issue["fields"]
    if f.get("parent"):
        return f["parent"]["key"]
    for k, v in f.items():
        if k.startswith("customfield") and isinstance(v, str) and re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", v):
            return v
    return ""


def issue_fields():
    if ALL_FIELDS:
        return "*all"  # CÀO HẾT: lấy TẤT CẢ field (gồm mọi custom field)
    fields = "summary,description,issuetype,status,parent,issuelinks,comment,attachment,project"
    if AC_FIELD:
        fields += f",{AC_FIELD}"
    if BR_FIELD:
        fields += f",{BR_FIELD}"
    return fields


def fetch_field_map():
    """Map id field → tên người-đọc (gồm cả custom field). TOLERANT: lỗi thì trả {} (không die)."""
    try:
        url = f"{BASE_URL}/rest/api/2/field"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {fd["id"]: (fd.get("name") or fd["id"])
                for fd in data if isinstance(fd, dict) and fd.get("id")}
    except Exception:
        return {}  # không lấy được tên → vẫn quét, hiển thị id thô


def adf_to_text(node):
    """Flatten Atlassian Document Format (Cloud API v3 trả rich-text dạng dict) → text đọc được."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(n) for n in node)
    if not isinstance(node, dict):
        return str(node)
    t = node.get("type")
    content = node.get("content")
    if t == "text":
        txt = node.get("text", "")
        for m in node.get("marks", []):
            if m.get("type") == "link":
                href = (m.get("attrs") or {}).get("href")
                if href:
                    txt = f"{txt} ({href})"
        return txt
    if t == "hardBreak":
        return "\n"
    if t == "mention":
        return "@" + (node.get("attrs") or {}).get("text", "").lstrip("@")
    if t == "emoji":
        a = node.get("attrs") or {}
        return a.get("text") or a.get("shortName") or ""
    if t in ("inlineCard", "blockCard"):
        return (node.get("attrs") or {}).get("url", "")
    if t == "paragraph":
        return adf_to_text(content) + "\n"
    if t == "heading":
        lvl = (node.get("attrs") or {}).get("level", 1)
        return "#" * lvl + " " + adf_to_text(content).strip() + "\n"
    if t in ("bulletList", "orderedList"):
        return adf_to_text(content)
    if t == "listItem":
        return "- " + adf_to_text(content).strip() + "\n"
    if t == "codeBlock":
        return "```\n" + adf_to_text(content).strip() + "\n```\n"
    if t == "blockquote":
        return "> " + adf_to_text(content).strip() + "\n"
    if t == "rule":
        return "\n---\n"
    if t in ("table", "tableRow"):
        return adf_to_text(content)
    if t in ("tableCell", "tableHeader"):
        return adf_to_text(content).strip() + " | "
    if content is not None:  # doc + node lạ → đệ quy content
        return adf_to_text(content)
    return ""


def _seconds_to_human(s):
    """Đổi giây → 'Xh Ym' (thời gian thực) cho est / log / remaining time."""
    try:
        s = int(s)
    except (TypeError, ValueError):
        return str(s)
    if s <= 0:
        return "0"
    h, rem = divmod(s, 3600)
    m = rem // 60
    parts = [p for p in (f"{h}h" if h else "", f"{m}m" if m else "") if p]
    return " ".join(parts) or f"{s}s"


def _format_timetracking(tt):
    """Field 'timetracking' → tóm tắt: Ước tính gốc / Còn lại / Đã log."""
    def pick(human_key, sec_key):
        return tt.get(human_key) or (_seconds_to_human(tt[sec_key]) if tt.get(sec_key) else None)
    orig = pick("originalEstimate", "originalEstimateSeconds")
    rem = pick("remainingEstimate", "remainingEstimateSeconds")
    spent = pick("timeSpent", "timeSpentSeconds")
    parts = []
    if orig:
        parts.append(f"Ước tính gốc {orig}")
    if rem:
        parts.append(f"Còn lại {rem}")
    if spent:
        parts.append(f"Đã log {spent}")
    return " · ".join(parts)


# Sprint trên Jira Server trả về chuỗi serialize: ...Sprint@x[id=..,name=..,state=..,startDate=..,endDate=..]
_SPRINT_RE = re.compile(r"name=(?P<name>[^,\]]+)", re.I)
_SPRINT_KV = re.compile(r"(state|startDate|endDate)=([^,\]]+)", re.I)


def _format_sprint_one(v):
    if isinstance(v, dict):
        name, state = v.get("name", "Sprint"), v.get("state", "")
        sd, ed = v.get("startDate"), v.get("endDate")
    elif isinstance(v, str) and "name=" in v:
        mn = _SPRINT_RE.search(v)
        name = mn.group("name") if mn else v
        kv = {k.lower(): val for k, val in _SPRINT_KV.findall(v)}
        state, sd, ed = kv.get("state", ""), kv.get("startdate", ""), kv.get("enddate", "")
    else:
        return ""
    extra = []
    if state and state.lower() not in ("none", "<null>", ""):
        extra.append(state.lower())
    sd = "" if sd in (None, "<null>") else (sd or "")
    ed = "" if ed in (None, "<null>") else (ed or "")
    if sd or ed:
        extra.append(f"{(sd or '?')[:10]} → {(ed or '?')[:10]}")
    return name + (f" ({', '.join(extra)})" if extra else "")


def _looks_like_sprint(v):
    item = v[0] if isinstance(v, list) and v else v
    if isinstance(item, dict):
        return "state" in item and any(k in item for k in ("boardId", "originBoardId", "startDate", "completeDate"))
    if isinstance(item, str):
        return "name=" in item and "state=" in item
    return False


def _format_sprint(v):
    items = v if isinstance(v, list) else [v]
    return "; ".join(p for p in (_format_sprint_one(x) for x in items) if p)


def format_field_value(v):
    """Chuẩn hoá MỌI kiểu giá trị field Jira → text gọn (cho phần 'Tất cả field')."""
    if v is None:
        return ""
    if _looks_like_sprint(v):  # Sprint (Cloud object / Server serialize) → tên (state, start → end)
        return _format_sprint(v)
    if isinstance(v, dict) and any(k in v for k in ("timeSpentSeconds", "originalEstimateSeconds", "remainingEstimateSeconds")):
        return _format_timetracking(v)  # timetracking → est/log/remaining
    if isinstance(v, bool):
        return "có" if v else "không"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        if v.get("type") == "doc":
            return adf_to_text(v).strip()
        for k in ("displayName", "name", "value", "label", "emailAddress"):
            if v.get(k):
                return str(v[k])
        if v.get("key") and "fields" in v:  # nested issue
            return v["key"]
        if "amount" in v:
            return str(v.get("amount"))
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        parts = [format_field_value(x) for x in v]
        return "; ".join(p for p in parts if p)
    return str(v)


# Field đã render ở section riêng → KHÔNG lặp lại trong "Tất cả field"
_RENDERED_KEYS = {"summary", "description", "issuetype", "status", "parent",
                  "issuelinks", "attachment", "comment", "project"}
# Field thường, đưa lên frontmatter cho dễ tra (chỉ khi có giá trị, 1 dòng)
_FM_FIELDS = [("priority", "priority"), ("assignee", "assignee"), ("reporter", "reporter"),
              ("labels", "labels"), ("components", "components"), ("fixVersions", "fix_versions"),
              ("created", "created"), ("updated", "updated"), ("resolution", "resolution"),
              ("duedate", "duedate"), ("timetracking", "time_tracking")]
# Field thời gian tính bằng GIÂY → đổi sang 'Xh Ym' khi hiển thị
_TIME_SECOND_FIELDS = {"timespent", "timeoriginalestimate", "timeestimate",
                       "aggregatetimespent", "aggregatetimeoriginalestimate", "aggregatetimeestimate"}


def _field_display(fid, raw):
    """Giá trị field để hiển thị: field thời-gian-giây → human; còn lại → format_field_value."""
    if fid in _TIME_SECOND_FIELDS and isinstance(raw, (int, float)):
        return _seconds_to_human(raw)
    return format_field_value(raw)


def fetch_by_jql(jql):
    """Server/DC: /rest/api/2/search (phân trang startAt/total).
    Cloud: /rest/api/3/search/jql (phân trang nextPageToken) — Atlassian đã GỠ
    /rest/api/2/search trên Cloud (HTTP 410, CHANGE-2046), nên phải tách đường."""
    if _is_cloud():
        return _fetch_jql_cloud(jql)
    return _fetch_jql_server(jql)


def _fetch_jql_server(jql):
    issues, start = [], 0
    while True:
        data = api_get("/rest/api/2/search", {
            "jql": jql, "startAt": start, "maxResults": 100, "fields": issue_fields(),
        })
        issues += data.get("issues", [])
        start += 100
        if start >= data.get("total", 0):
            return issues


def _fetch_jql_cloud(jql):
    # Endpoint mới: phân trang bằng nextPageToken (không có 'total'); lặp tới khi hết token.
    issues, token = [], None
    while True:
        params = {"jql": jql, "maxResults": 100, "fields": issue_fields()}
        if token:
            params["nextPageToken"] = token
        data = api_get("/rest/api/3/search/jql", params)
        batch = data.get("issues", [])
        issues += batch
        token = data.get("nextPageToken")
        if not token or not batch:
            return issues


def fetch_projects():
    data = api_get("/rest/api/2/project")
    if PROJECT_KEYS:
        data = [p for p in data if p["key"] in PROJECT_KEYS]
    return data


PROJECT_NAMES = {}  # key -> tên project (điền khi quét, dùng đặt tên thư mục đầy đủ)

# Mẫu tên thư mục project — đổi trong .env.local, placeholder: {key}, {name}
# Vd: PROJECT_FOLDER_PATTERN={key}_{name}  →  PROJ_MyApp
#     PROJECT_FOLDER_PATTERN={name}        →  MyApp
#     PROJECT_FOLDER_PATTERN={key}         →  FA
FOLDER_PATTERN = os.getenv("PROJECT_FOLDER_PATTERN") or "{key}_{name}"


def project_folder_name(pkey):
    name = re.sub(r"[^\w-]", "-", PROJECT_NAMES.get(pkey, ""))
    if not name:
        return pkey
    return FOLDER_PATTERN.replace("{key}", pkey).replace("{name}", name).strip("_-") or pkey


def vault_base(pkey):
    """Thư mục gốc notes của 1 project: VAULT/<KEY_Tên-đầy-đủ>/ nếu gom theo project."""
    return os.path.join(VAULT, project_folder_name(pkey)) if PER_PROJECT else VAULT


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def issue_note(issue, project_key, fname_map):
    key = issue["key"]
    f = issue["fields"]
    itype = norm_type(issue)
    parent = get_parent(issue)
    status = (f.get("status") or {}).get("name", "")
    summary = f.get("summary", "")

    fm = [
        "---",
        f"type: {itype}", "source: jira", f"jira_key: {key}",
        f"jira_issue_type: {f['issuetype']['name']}", f"project: {project_key}",
        f"status: {status}", f"parent: {parent}",
    ]
    for fid, label in _FM_FIELDS:  # enrich frontmatter các field hay tra (chỉ khi có, 1 dòng)
        val = _field_display(fid, f.get(fid))
        if val and "\n" not in val:
            fm.append(f"{label}: {json.dumps(val, ensure_ascii=False)}")
    for fid in f:  # Sprint (id custom field đổi theo Jira) → đưa lên frontmatter cho dễ tra
        if fid != "status" and _looks_like_sprint(f.get(fid)):
            sv = _format_sprint(f.get(fid))
            if sv:
                fm.append(f"sprint: {json.dumps(sv, ensure_ascii=False)}")
            break
    fm += [f"imported_at: {NOW}", "---", "",
           f"# {key} — {summary}", "",
           "## Metadata", "",
           f"- Loại: {f['issuetype']['name']}", f"- Trạng thái: {status}",
           f"- Link Jira: {BASE_URL}/browse/{key}", ""]
    if f.get("description"):
        fm += ["## Description", "", format_field_value(f["description"]), ""]
    if AC_FIELD and f.get(AC_FIELD):
        fm += ["## Acceptance Criteria Raw", "", format_field_value(f[AC_FIELD]), ""]
    if BR_FIELD and f.get(BR_FIELD):
        fm += ["## Business Rule Raw", "", format_field_value(f[BR_FIELD]), ""]
    if parent:
        fm += ["## Parent", "", f"- [[{fname_map.get(parent, parent)}]]", ""]
    links = []
    for ln in f.get("issuelinks", []):
        other = ln.get("outwardIssue") or ln.get("inwardIssue")
        if other:
            rel = ln["type"].get("outward" if ln.get("outwardIssue") else "inward", "related")
            links.append(f"- {rel}: [[{fname_map.get(other['key'], other['key'])}]]")
    if links:
        fm += ["## Linked Issues", ""] + links + [""]
    atts = [f"- {a['filename']} ({a.get('size', '?')} bytes) — {a.get('content', '')}".rstrip(" —")
            for a in f.get("attachment", [])]
    if atts:
        fm += ["## Attachments Metadata", ""] + atts + [""]
    comments = (f.get("comment") or {}).get("comments", [])
    if comments:
        fm += ["## Comments", ""]
        for c in comments:
            who = (c.get("author") or {}).get("displayName", "?")
            fm.append(f"- **{who}** ({(c.get('created') or '')[:10]}): {format_field_value(c.get('body', ''))}")
        fm.append("")
    # ── CÀO HẾT: dump MỌI field còn lại (priority, labels, components, sprint, custom field…) ──
    skip = set(_RENDERED_KEYS)
    if AC_FIELD:
        skip.add(AC_FIELD)
    if BR_FIELD:
        skip.add(BR_FIELD)
    extra = []
    for fid in sorted(f.keys()):
        if fid in skip:
            continue
        val = _field_display(fid, f.get(fid))
        if not val:
            continue
        label = FIELD_MAP.get(fid, fid)
        if "\n" in val:
            extra.append(f"- **{label}** (`{fid}`):")
            extra += ["  " + line for line in val.splitlines()]
        else:
            extra.append(f"- **{label}** (`{fid}`): {val}")
    if extra:
        fm += ["## Tất cả field (đầy đủ)", ""] + extra + [""]
    fm += ["## Source", "", f"- SRC-JIRA-{key}", ""]
    return "\n".join(fm)


def write_issue(issue, pkey, fname_map, nodes, edges, registry):
    key, itype = issue["key"], norm_type(issue)
    parent = get_parent(issue)
    status = (issue["fields"].get("status") or {}).get("name", "")
    folder = TYPE_DIRS.get(itype, DIRS["raw"])  # mọi loại nhận diện được giữ đúng thư mục,
    # kể cả khi thiếu parent (đã đóng hay chưa vẫn quét — JQL không lọc status)
    write(os.path.join(vault_base(pkey), folder, f"{fname_map[key]}.md"), issue_note(issue, pkey, fname_map))

    nodes.append({"id": key, "type": itype, "title": issue["fields"].get("summary", ""),
                  "status": status, "project": pkey})
    edges.append({"from": pkey, "to": key, "relation": "has_issue"})
    if parent:
        edges.append({"from": parent, "to": key, "relation": "parent_of"})
    for ln in issue["fields"].get("issuelinks", []):
        other = ln.get("outwardIssue") or ln.get("inwardIssue")
        if other:
            edges.append({"from": key, "to": other["key"], "relation": "linked"})
    registry.append({
        "source_id": f"SRC-JIRA-{key}", "source_type": "jira_issue", "jira_key": key,
        "project": pkey, "issue_type": issue["fields"]["issuetype"]["name"],
        "title": issue["fields"].get("summary", ""), "status": status, "imported_at": NOW,
    })


def _source_id():
    """Định danh nguồn theo host của JIRA_BASE_URL — mỗi Jira một mốc đồng bộ riêng, để
    đa nguồn (Server + Cloud) không đè mốc --since của nhau."""
    host = urllib.parse.urlparse(BASE_URL).netloc or "default"
    return re.sub(r"[^\w.-]", "_", host)


def _last_import_path():
    return os.path.join(VAULT, DIRS["system"], f"last-import-{_source_id()}.txt")


def read_last_import():
    p = _last_import_path()
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    # Tương thích ngược: mốc cũ dùng chung "last-import.txt" (trước khi tách theo nguồn).
    legacy = os.path.join(VAULT, DIRS["system"], "last-import.txt")
    if os.path.exists(legacy):
        return open(legacy, encoding="utf-8").read().strip()
    return ""


def save_last_import():
    # Lưu theo định dạng JQL hiểu được: "YYYY-MM-DD HH:MM"
    os.makedirs(os.path.dirname(_last_import_path()), exist_ok=True)
    with open(_last_import_path(), "w", encoding="utf-8") as f:
        f.write(datetime.now().strftime("%Y-%m-%d %H:%M"))


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def merge_system(nodes, edges, registry):
    """Merge (không ghi đè toàn bộ) vào _system của vault — dùng cho chế độ quét lẻ."""
    gpath = os.path.join(VAULT, DIRS["system"], "relation-graph.json")
    rpath = os.path.join(VAULT, DIRS["system"], "source-registry.json")
    graph = load_json(gpath, {"generated_at": NOW, "nodes": [], "edges": []})
    reg = load_json(rpath, [])

    by_id = {n["id"]: n for n in graph["nodes"]}
    for n in nodes:
        by_id[n["id"]] = n
    seen = {(e["from"], e["to"], e["relation"]) for e in graph["edges"]}
    for e in edges:
        if (e["from"], e["to"], e["relation"]) not in seen:
            graph["edges"].append(e)
            seen.add((e["from"], e["to"], e["relation"]))
    graph["nodes"] = list(by_id.values())
    graph["generated_at"] = NOW

    by_src = {r["source_id"]: r for r in reg}
    for r in registry:
        by_src[r["source_id"]] = r

    write(gpath, json.dumps(graph, ensure_ascii=False, indent=2))
    write(rpath, json.dumps(list(by_src.values()), ensure_ascii=False, indent=2))


def run_single(jql):
    """Chế độ quét lẻ: --keys / --jql. Chỉ tạo/cập nhật note liên quan, merge graph."""
    print(f"Đang quét theo điều kiện: {jql}")
    global FIELD_MAP
    if ALL_FIELDS and not FIELD_MAP:
        FIELD_MAP = fetch_field_map()
    issues = fetch_by_jql(jql)
    if not issues:
        die("Không tìm thấy issue nào khớp. Kiểm tra key/JQL và quyền xem.")
    print(f"  → {len(issues)} issues")

    fname_map = {i["key"]: safe_name(i["key"], i["fields"].get("summary", "")) for i in issues}
    nodes, edges, registry = [], [], []
    for i in issues:
        proj = i["fields"].get("project") or {}
        pkey = proj.get("key", "") or i["key"].split("-")[0]
        if proj.get("name"):
            PROJECT_NAMES[pkey] = proj["name"]
        write_issue(i, pkey, fname_map, nodes, edges, registry)
        print(f"  ✓ {i['key']} — {i['fields'].get('summary', '')}")

    root_dirs = [DIRS["index"], DIRS["system"]] if PER_PROJECT else ALL_DIRS
    for d in root_dirs:
        os.makedirs(os.path.join(VAULT, d), exist_ok=True)
    merge_system(nodes, edges, registry)
    print(f"\nHoàn tất (chế độ quét lẻ, đã merge vào vault).\nVault: {os.path.abspath(VAULT)}")


def run_full():
    print("Đang lấy danh sách project...")
    global FIELD_MAP
    if ALL_FIELDS and not FIELD_MAP:
        FIELD_MAP = fetch_field_map()
    projects = fetch_projects()
    print(f"Tìm thấy {len(projects)} project.")

    nodes, edges, registry = [], [], []
    index_lines = ["# Jira Knowledge Base", "", f"Import lúc: {NOW}", ""]

    for p in projects:
        pkey, pname = p["key"], p["name"]
        PROJECT_NAMES[pkey] = pname
        print(f"Đang quét project {pkey} — {pname}")
        issues = fetch_by_jql(f"project={pkey} ORDER BY key ASC")
        from collections import Counter
        cnt = Counter(norm_type(i) for i in issues)
        detail = ", ".join(f"{k}: {v}" for k, v in sorted(cnt.items()))
        print(f"  → {len(issues)} issues ({detail})")

        fname_map = {i["key"]: safe_name(i["key"], i["fields"].get("summary", "")) for i in issues}
        proj_fname = f"{pkey}_" + re.sub(r"[^\w-]", "-", pname)
        nodes.append({"id": pkey, "type": "project", "title": pname, "status": "", "project": pkey})

        epics = [i for i in issues if norm_type(i) == "epic"]
        proj_note = ["---", "type: project", "source: jira",
                     f"jira_project_key: {pkey}", f"imported_at: {NOW}", "---", "",
                     f"# {pname}", "", "## Epics", ""]
        proj_note += [f"- [[{fname_map[e['key']]}]]" for e in epics] or ["- (chưa có epic)"]
        proj_note += ["", "## Tất cả issue", ""]
        proj_note += [f"- [[{fname_map[i['key']]}]]" for i in issues]
        write(os.path.join(vault_base(pkey), DIRS["projects"], f"{proj_fname}.md"), "\n".join(proj_note))
        index_lines += [f"## [[{proj_fname}|{pname}]] ({len(issues)} issues)", ""]

        for i in issues:
            write_issue(i, pkey, fname_map, nodes, edges, registry)

    root_dirs = [DIRS["index"], DIRS["system"]] if PER_PROJECT else ALL_DIRS
    for d in root_dirs:
        os.makedirs(os.path.join(VAULT, d), exist_ok=True)
    # MERGE (không ghi đè) vào _system → quét nguồn thứ 2 (vd projectB sau projectA)
    # KHÔNG xoá dữ liệu nguồn cũ. Mỗi project ở thư mục riêng nên notes không đụng nhau.
    merge_system(nodes, edges, registry)
    write(os.path.join(VAULT, DIRS["index"], "Jira-Knowledge-Base.md"), "\n".join(index_lines))
    print(f"\nHoàn tất.\nObsidian Vault đã tạo tại: {os.path.abspath(VAULT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="Chỉ test kết nối")
    ap.add_argument("--keys", help="Quét riêng các issue, vd: PROJ-102,PROJ-105")
    ap.add_argument("--jql", help='Quét theo JQL, vd: "parent = PROJ-101"')
    ap.add_argument("--since", nargs="?", const="__last__",
                    help='Chỉ quét issue MỚI/CẬP NHẬT. --since 2026-06-01 theo ngày; '
                         '--since (không tham số) = từ lần quét trước (đọc _system/last-import.txt)')
    ap.add_argument("--per-project", action="store_true",
                    help="Mỗi project một thư mục con trong vault (VAULT/<KEY>/...)")
    args = ap.parse_args()
    if args.per_project:
        global PER_PROJECT
        PER_PROJECT = True

    check_config()
    if args.test:
        # 1) Token hợp lệ? (gọi /myself — nhẹ, không cần quyền project)
        me = api_get("/rest/api/2/myself")
        who = me.get("displayName") or me.get("name") or "?"
        print(f"Đăng nhập OK: {who}")
        # 2) Thấy được project nào?
        projects = fetch_projects()
        print(f"Kết nối OK. Tìm thấy {len(projects)} project:")
        for p in projects:
            print(f"  - {p['key']}: {p['name']}")
        return
    if args.since is not None:
        since = read_last_import() if args.since == "__last__" else args.since
        if not since:
            die("Chưa có mốc quét trước. Dùng --since YYYY-MM-DD cho lần đầu.")
        scope = ""
        if PROJECT_KEYS:
            scope = "project in (" + ",".join(PROJECT_KEYS) + ") AND "
        print(f"Quét issue cập nhật từ {since}...")
        run_single(f'{scope}updated >= "{since}" ORDER BY updated ASC')
        save_last_import()
    elif args.keys:
        keys = ",".join(k.strip() for k in args.keys.split(",") if k.strip())
        run_single(f"key in ({keys})")
    elif args.jql:
        run_single(args.jql)
    else:
        run_full()
        save_last_import()


if __name__ == "__main__":
    main()
