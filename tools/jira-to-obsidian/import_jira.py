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

Re-scan IDEMPOTENT: mỗi issue chỉ 1 file (`{KEY}_{slug}.md`). Ghi đè theo path; nếu issue đổi tiêu đề
(đổi slug) hoặc đổi loại (đổi thư mục) thì file CŨ cùng key được dọn (_purge_stale) → không nhân bản rác.
(Issue bị XOÁ trên Jira vẫn không tự mất khỏi vault — định kỳ quét full nếu cần.)

Bảo mật: chỉ dùng JIRA_PAT từ .env.local. Không in token ra log.
"""

import argparse
import base64
import glob
import json
import os
import re
import shlex
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# Chỉ dùng thư viện chuẩn Python — KHÔNG cần pip install gì.


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# SCRIPT_DIR đã là THƯ MỤC tools/jira-to-obsidian → root = lên 2 cấp (KHÁC build_report tính 3 cấp từ FILE).
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))


def data_root():
    """Thư mục DỮ LIỆU project user đang chạy (giống build_report.data_root) — để ghi vault ĐÚNG project.

    Bản CÀI (`~/.claude/kora-framework/tools/...`) chạy trong PROJECT (cwd): neo theo SCRIPT_DIR sẽ ghi vault vào
    KF chứ không phải project. Vì vậy: cwd nếu là project Kora thật (có `config/factory-config.yaml`) → dùng cwd;
    ngược lại → REPO_ROOT (bản dev cwd==REPO_ROOT, hoặc lịch nền)."""
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, "config", "factory-config.yaml")):
        return cwd
    return REPO_ROOT


def _cfg_vault_path(data):
    """Đọc `vault_path` từ <data>/config/factory-config.yaml (regex như build_report — KHÔNG cần pyyaml)."""
    cfg_path = os.path.join(data, "config", "factory-config.yaml")
    if os.path.exists(cfg_path):
        try:
            mm = re.search(r"^\s*vault_path:\s*(.+)$", open(cfg_path, encoding="utf-8").read(), re.M)
            if mm:
                return mm.group(1).strip().strip('"').strip("'")
        except OSError:
            pass
    return ""


def _resolve_vault(raw, data):
    """Đường dẫn vault: tuyệt đối giữ nguyên; tương đối → neo theo DATA (project), KHÔNG SCRIPT_DIR."""
    return raw if os.path.isabs(raw) else os.path.normpath(os.path.join(data, raw))


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
# Vault: GHI ĐÚNG vault của PROJECT. Ưu tiên: OBSIDIAN_VAULT env > `vault_path` trong config project >
# "./KB-Vault". Đường dẫn tương đối neo theo DATA (project hiện tại, qua data_root) — KHÔNG theo SCRIPT_DIR
# (bản cài SCRIPT_DIR=KF sẽ ghi nhầm KF; và phải KHỚP vault build_report đọc từ config). --vault override ở main().
DATA = data_root()
_vault_raw = os.getenv("OBSIDIAN_VAULT") or _cfg_vault_path(DATA) or "./KB-Vault"
VAULT = _resolve_vault(_vault_raw, DATA)
PROJECT_KEYS = [k.strip() for k in (os.getenv("PROJECT_KEYS") or "").split(",") if k.strip()]
AC_FIELD = os.getenv("JIRA_AC_FIELD") or ""
BR_FIELD = os.getenv("JIRA_BR_FIELD") or ""
# Custom field "effort/estimate theo GIỜ" (vd FMC: customfield_10867 "Effort Plan (h)") — gộp vào
# ước tính khi issue KHÔNG có time-tracking chuẩn. Giá trị field tính bằng giờ → x3600 ra giây.
EFFORT_FIELD = os.getenv("JIRA_EFFORT_FIELD") or ""
# Custom field "Complexity" (độ phức tạp; số càng lớn càng phức tạp, >=7 = cao). Ưu tiên id cấu hình; nếu rỗng,
# tự dò field tên "Complexity" trong FIELD_MAP. Ghi frontmatter máy-đọc `complexity` để report lấy làm trọng tâm.
COMPLEXITY_FIELD = os.getenv("JIRA_COMPLEXITY_FIELD") or ""
# Custom field "Start date" (ngày BẮT ĐẦU được phép logwork). Ưu tiên id cấu hình; rỗng → tự dò field tên
# "Start date"/"Start" trong FIELD_MAP. Ghi frontmatter máy-đọc `startdate` (YYYY-MM-DD) cho workflow kiểm tra worklog.
START_FIELD = os.getenv("JIRA_START_FIELD") or ""
# Custom field "Type" phân loại worklog (Normal / OT / Effort). Ưu tiên id cấu hình; rỗng → tự dò field tên
# "Type"/"Work Type" HOẶC field option có giá trị ∈ {Normal,OT,Effort}. Ghi frontmatter `work_type` (ràng buộc 8h/ngày chỉ áp Normal).
WORKTYPE_FIELD = os.getenv("JIRA_WORKTYPE_FIELD") or ""
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
FROM_MCP = False  # True khi nạp qua --from-mcp (không có token → bỏ qua việc gọi API lấy thêm comment)
SOURCE_ID = ""    # token nguồn ghi vào frontmatter note (mặc định jira__<host>; override bằng --source-id) — tách Jira đa instance khi báo cáo
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
        # marker máy-đọc: mạng/sandbox chặn → skill BÀN GIAO lệnh bash cho Terminal (KHÁC 401/auth ở trên).
        print("NETWORK_UNREACHABLE", file=sys.stderr)
        die(f"Không kết nối được Jira ({e.reason}). Kiểm tra VPN/LAN/proxy "
            "(hoặc Cowork sandbox chặn mạng → chạy lệnh ở Terminal).")
    except (TimeoutError, OSError) as e:   # timeout/socket-level KHÔNG bọc trong URLError
        print("NETWORK_UNREACHABLE", file=sys.stderr)
        die(f"Không kết nối được Jira ({e}). Kiểm tra VPN/LAN/proxy "
            "(hoặc Cowork sandbox chặn mạng → chạy lệnh ở Terminal).")


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
# Lưu ý: "sub" đặt TRƯỚC "task" để "Sub-task" khớp sub-task (không rơi vào task).
# FMC-riêng: "improvement"→task, "feature" (gồm "New Feature")→user_story.
_TYPE_MAP = {"epic": "epic", "story": "user_story", "sub": "sub-task",
             "bug": "bug", "defect": "bug", "improvement": "task",
             "feature": "user_story", "task": "task"}
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
        return "*all,comment"  # CÀO HẾT: tất cả field + ÉP comment (vài Jira *all bỏ sót comment)
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


# ── Field MÁY-ĐỌC cho report tiến độ (numeric/structured, để cộng dồn & nhóm) ──
def _sprint_objs(f):
    """Chuẩn hoá field sprint (Cloud dict / Server serialize) → list {name,state,start,end}."""
    for fid in f:
        if fid == "status":
            continue
        v = f.get(fid)
        if not _looks_like_sprint(v):
            continue
        out = []
        for it in (v if isinstance(v, list) else [v]):
            if isinstance(it, dict):
                out.append({"name": it.get("name", ""), "state": (it.get("state") or "").lower(),
                            "start": it.get("startDate"), "end": it.get("endDate")})
            elif isinstance(it, str) and "name=" in it:
                mn = _SPRINT_RE.search(it)
                kv = {k.lower(): val for k, val in _SPRINT_KV.findall(it)}
                out.append({"name": mn.group("name") if mn else "", "state": kv.get("state", "").lower(),
                            "start": kv.get("startdate"), "end": kv.get("enddate")})
        return out
    return []


def _active_sprint(f):
    objs = _sprint_objs(f)
    if not objs:
        # Fallback: nhiều team đặt "Sprint XX" trong fixVersions (released=false ⇒ đang chạy)
        for fv in f.get("fixVersions") or []:
            nm = fv.get("name", "")
            if nm.lower().startswith("sprint") and not fv.get("released"):
                return {"name": nm, "state": "active", "start": None, "end": (fv.get("releaseDate") or "")[:10]}
        return None
    for s in objs:
        if s["state"] == "active":
            return s
    return objs[-1]  # không có active → sprint gần nhất


def _time_seconds(f):
    """(est, spent, remaining) tính bằng GIÂY — từ timetracking hoặc field giây top-level."""
    tt = f.get("timetracking") if isinstance(f.get("timetracking"), dict) else {}
    def g(tt_key, top_key):
        if tt.get(tt_key) is not None:
            return tt.get(tt_key)
        v = f.get(top_key)
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    est = g("originalEstimateSeconds", "timeoriginalestimate")
    spent = g("timeSpentSeconds", "timespent")
    rem = g("remainingEstimateSeconds", "timeestimate")
    if est is None and EFFORT_FIELD:  # gộp field effort tùy biến (giờ) khi thiếu ước tính chuẩn
        ev = f.get(EFFORT_FIELD)
        if isinstance(ev, (int, float)) and not isinstance(ev, bool) and ev > 0:
            est = int(ev * 3600)
            if rem is None and spent is not None:  # suy ra còn lại nếu có log
                rem = max(est - spent, 0)
    return (est, spent, rem)


def _story_points(f):
    for fid, val in f.items():
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if "story point" in (FIELD_MAP.get(fid, "") or "").lower():
                return val
    return None


def _complexity(f):
    """Giá trị field Complexity (số). Ưu tiên COMPLEXITY_FIELD; rỗng → dò field tên 'complexity' trong FIELD_MAP."""
    fid = COMPLEXITY_FIELD
    if not fid:
        for k, name in FIELD_MAP.items():
            if (name or "").strip().lower() == "complexity":
                fid = k
                break
    if not fid:
        return None
    v = f.get(fid)
    if isinstance(v, dict):              # custom field dạng option {value:"7"} / {name:"7"}
        v = v.get("value") or v.get("name")
    if isinstance(v, bool) or v is None or str(v).strip() == "":
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _norm_date(v):
    """Trả 'YYYY-MM-DD' từ chuỗi date/datetime Jira; None nếu không nhận dạng được."""
    if isinstance(v, dict):
        v = v.get("value") or v.get("name") or v.get("date")
    if not isinstance(v, str):
        return None
    s = v.strip()[:10]
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            int(s[:4]); int(s[5:7]); int(s[8:10])
            return s
        except ValueError:
            return None
    return None


def _start_date(f):
    """Ngày BẮT ĐẦU (YYYY-MM-DD). Ưu tiên START_FIELD; rỗng → dò field tên 'start date'/'start' trong FIELD_MAP."""
    fid = START_FIELD
    if not fid:
        for k, name in FIELD_MAP.items():
            if (name or "").strip().lower() in ("start date", "start", "planned start", "start time", "ngày bắt đầu"):
                fid = k
                break
    if not fid:
        return _norm_date(f.get("startdate") or f.get("start"))  # vài bản expose tên thẳng
    return _norm_date(f.get(fid))


_WORKTYPE_VALUES = {"normal", "ot", "effort"}


def _work_type(f):
    """Giá trị field phân loại worklog (Normal/OT/Effort). Ưu tiên WORKTYPE_FIELD; rỗng → dò field tên
    'type'/'work type' HOẶC field option có giá trị ∈ {Normal,OT,Effort}."""
    def _val(raw):
        if isinstance(raw, list):
            raw = raw[0] if raw else None
        if isinstance(raw, dict):
            raw = raw.get("value") or raw.get("name")
        return raw.strip() if isinstance(raw, str) and raw.strip() else None
    if WORKTYPE_FIELD:
        return _val(f.get(WORKTYPE_FIELD))
    for k, name in FIELD_MAP.items():        # 1) khớp theo TÊN field
        if (name or "").strip().lower() in ("type", "work type", "worklog type", "task type", "loại"):
            val = _val(f.get(k))
            if val:
                return val
    for k in f:                              # 2) khớp theo TẬP GIÁ TRỊ {Normal,OT,Effort}
        if k in ("issuetype", "status", "priority"):
            continue
        val = _val(f.get(k))
        if val and val.lower() in _WORKTYPE_VALUES:
            return val
    return None


def _machine_progress_fields(f):
    """Dòng frontmatter MÁY-ĐỌC cho report: status_category, time(giây), story_points, sprint active, complexity, startdate, work_type."""
    lines = []
    sc = ((f.get("status") or {}).get("statusCategory") or {}).get("key", "")  # new|indeterminate|done
    cat = {"new": "todo", "indeterminate": "in_progress", "done": "done"}.get(sc, "")
    if cat:
        lines.append(f"status_category: {cat}")
    est, spent, rem = _time_seconds(f)
    if est is not None:
        lines.append(f"time_estimate_s: {int(est)}")
    if spent is not None:
        lines.append(f"time_spent_s: {int(spent)}")
    if rem is not None:
        lines.append(f"time_remaining_s: {int(rem)}")
    sp = _story_points(f)
    if sp is not None:
        lines.append(f"story_points: {sp}")
    sprint = _active_sprint(f)
    if sprint and sprint.get("name"):
        lines.append(f"sprint_name: {json.dumps(sprint['name'], ensure_ascii=False)}")
        if sprint.get("state"):
            lines.append(f"sprint_state: {sprint['state']}")
        if sprint.get("end"):
            lines.append(f"sprint_end: {json.dumps((sprint['end'] or '')[:10], ensure_ascii=False)}")
    cx = _complexity(f)
    if cx is not None:
        lines.append(f"complexity: {cx}")
    sd = _start_date(f)
    if sd:
        lines.append(f"startdate: {sd}")
    wt = _work_type(f)
    if wt:
        lines.append(f"work_type: {json.dumps(wt, ensure_ascii=False)}")
    return lines


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


def _purge_stale(base, key, keep):
    """Re-scan idempotent: xoá mọi note CŨ cùng issue key (đổi tiêu đề → đổi slug; đổi loại →
    đổi thư mục type) ≠ file đích `keep`, để mỗi issue chỉ còn ĐÚNG 1 file (không nhân bản rác).
    Dấu '_' trong '{key}_*' ngăn khớp nhầm key có cùng tiền tố (PROJ-1 vs PROJ-12)."""
    k = glob.escape(key)
    keep_abs = os.path.abspath(keep)
    for pat in (os.path.join(base, "*", f"{k}_*.md"), os.path.join(base, f"{k}_*.md")):
        for p in glob.glob(pat):
            if os.path.abspath(p) != keep_abs:
                try:
                    os.remove(p)
                except OSError:
                    pass  # fallback an toàn (rule §1.9) — không fail cứng nếu không xoá được


def fetch_all_comments(key):
    """Best-effort: lấy HẾT comment của 1 issue qua phân trang /issue/{key}/comment.
    Trả list comment đầy đủ; None nếu không lấy được (MCP/không token/lỗi) → giữ comment sẵn có."""
    if FROM_MCP or not BASE_URL:
        return None
    out, start = [], 0
    try:
        while True:
            url = (f"{BASE_URL}/rest/api/2/issue/{key}/comment?"
                   + urllib.parse.urlencode({"startAt": start, "maxResults": 100}))
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            cs = data.get("comments", [])
            out.extend(cs)
            start += len(cs)
            if not cs or start >= int(data.get("total", len(out))):
                break
        return out
    except Exception:
        return None


def issue_note(issue, project_key, fname_map):
    key = issue["key"]
    f = issue["fields"]
    itype = norm_type(issue)
    parent = get_parent(issue)
    status = (f.get("status") or {}).get("name", "")
    summary = f.get("summary", "")

    fm = [
        "---",
        f"type: {itype}", "source: jira", f"source_id: {SOURCE_ID}", f"jira_key: {key}",
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
    fm += _machine_progress_fields(f)  # time_*_s, story_points, sprint_name/state/end (cho report)
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
    cobj = f.get("comment") or {}
    comments = cobj.get("comments", [])
    if cobj.get("total", len(comments)) > len(comments):  # search giới hạn số comment → lấy HẾT (phân trang)
        full = fetch_all_comments(key)
        if full is not None:
            comments = full
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
    target = os.path.join(vault_base(pkey), folder, f"{fname_map[key]}.md")
    _purge_stale(vault_base(pkey), key, target)   # dọn file cũ cùng key (đổi tiêu đề/đổi loại) → 1 file/issue
    write(target, issue_note(issue, pkey, fname_map))

    nodes.append({"id": key, "type": itype, "title": issue["fields"].get("summary", ""),
                  "status": status, "project": pkey,
                  "issue_type": issue["fields"]["issuetype"]["name"]})
    edges.append({"from": pkey, "to": key, "relation": "has_issue"})
    if parent:
        edges.append({"from": parent, "to": key, "relation": "parent_of"})
    for ln in issue["fields"].get("issuelinks", []):
        out = ln.get("outwardIssue")
        other = out or ln.get("inwardIssue")
        if other:
            # GIỮ tên loại link (outward/inward) + chiều → /claude-knowledge-sync nhận diện CR↔US (versioning).
            ltype = (ln.get("type") or {}).get("outward" if out else "inward", "related")
            edges.append({"from": key, "to": other["key"], "relation": "linked",
                          "link_type": ltype, "direction": "outward" if out else "inward"})
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


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _daily_success_path():
    return os.path.join(VAULT, DIRS["system"], f"daily-sync-{_source_id()}-{_today()}.txt")


def has_daily_success():
    """Hôm nay đã đồng bộ thành công chưa (idempotent-per-day)."""
    return os.path.exists(_daily_success_path())


def mark_daily_success():
    os.makedirs(os.path.dirname(_daily_success_path()), exist_ok=True)
    with open(_daily_success_path(), "w", encoding="utf-8") as f:
        f.write(datetime.now().isoformat())


def freshness_info():
    """{last_import, is_stale, age_days, done_today} — so mốc last-import với hôm nay."""
    last = read_last_import()
    info = {"last_import": last or None, "is_stale": True, "age_days": None,
            "done_today": has_daily_success(), "today": _today()}
    if last:
        d = last[:10]
        info["is_stale"] = d < _today()
        try:
            from datetime import date
            info["age_days"] = (date.today() - date.fromisoformat(d)).days
        except ValueError:
            pass
    return info


def load_mcp_issues(path):
    """Đọc issues từ file MCP đã lưu: {issues:{nodes:[...]}} | {issues:[...]} | {nodes:[...]} | [...]."""
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        iss = data.get("issues")
        if isinstance(iss, dict):
            return iss.get("nodes", [])
        if isinstance(iss, list):
            return iss
        if isinstance(data.get("nodes"), list):
            return data["nodes"]
    return []


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


_TYPE_LABEL = {"epic": "Epic", "user_story": "User Story", "story": "User Story",
               "task": "Task", "bug": "Bug", "sub-task": "Sub-task", "subtask": "Sub-task",
               "raw": "Khác", "issue": "Khác"}
_TYPE_ORDER = ["Epic", "User Story", "Task", "Bug", "Sub-task", "Khác"]


def type_breakdown(issues):
    """Đếm theo LOẠI (Epic/User Story/Task/Bug/Sub-task/Khác) → list 'Nhãn: N' (Epic trước, Khác cuối).
    Để báo cáo PHÂN LOẠI RÕ — KHÔNG gộp chung gọi 'issue'."""
    from collections import Counter
    c = Counter(norm_type(i) for i in issues)
    seen = {}
    for k, v in c.items():
        lbl = _TYPE_LABEL.get(k, k.replace("_", " ").title())
        seen[lbl] = seen.get(lbl, 0) + v
    parts = [f"{lbl}: {seen[lbl]}" for lbl in _TYPE_ORDER if lbl in seen]
    parts += [f"{lbl}: {n}" for lbl, n in seen.items() if lbl not in _TYPE_ORDER]
    return parts


def run_single(jql):
    """Chế độ quét lẻ: --keys / --jql. Chỉ tạo/cập nhật note liên quan, merge graph."""
    print(f"Đang quét theo điều kiện: {jql}")
    global FIELD_MAP
    if ALL_FIELDS and not FIELD_MAP:
        FIELD_MAP = fetch_field_map()
    issues = fetch_by_jql(jql)
    if not issues:
        die("Không tìm thấy hạng mục công việc nào khớp. Kiểm tra key/JQL và quyền xem.")
    run_from_issues(issues)


def run_from_issues(issues):
    """Ghi danh sách issue (shape Jira REST 'fields') vào vault + merge graph. Dùng CHUNG cho
    token (fetch_by_jql) lẫn MCP (--from-mcp) — issues đã có sẵn, KHÔNG fetch lại."""
    bd = type_breakdown(issues)
    print(f"  → {len(issues)} hạng mục công việc — phân loại: " + " · ".join(bd))
    fname_map = {i["key"]: safe_name(i["key"], i["fields"].get("summary", "")) for i in issues}
    nodes, edges, registry = [], [], []
    for i in issues:
        proj = i["fields"].get("project") or {}
        pkey = proj.get("key", "") or i["key"].split("-")[0]
        if proj.get("name"):
            PROJECT_NAMES[pkey] = proj["name"]
        write_issue(i, pkey, fname_map, nodes, edges, registry)
        print(f"  ✓ [{_TYPE_LABEL.get(norm_type(i), norm_type(i))}] {i['key']} — {i['fields'].get('summary', '')}")
    root_dirs = [DIRS["index"], DIRS["system"]] if PER_PROJECT else ALL_DIRS
    for d in root_dirs:
        os.makedirs(os.path.join(VAULT, d), exist_ok=True)
    merge_system(nodes, edges, registry)
    print("\nHoàn tất — đã PHÂN LOẠI vào thư mục theo loại + tạo liên kết quan hệ:")
    print("  " + " · ".join(bd))
    print(f"Vault: {os.path.abspath(VAULT)}  (Epic→02_Epics · US→03_UserStories · Task→04_Tasks · Bug→05_Bugs · Sub-task→06_SubTasks)")


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
        print(f"  → {len(issues)} hạng mục công việc — phân loại: " + " · ".join(type_breakdown(issues)))

        fname_map = {i["key"]: safe_name(i["key"], i["fields"].get("summary", "")) for i in issues}
        proj_fname = f"{pkey}_" + re.sub(r"[^\w-]", "-", pname)
        nodes.append({"id": pkey, "type": "project", "title": pname, "status": "", "project": pkey})

        epics = [i for i in issues if norm_type(i) == "epic"]
        proj_note = ["---", "type: project", "source: jira", f"source_id: {SOURCE_ID}",
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


def _emit_command(args) -> str:
    """Sinh 1 DÒNG LỆNH terminal để QUÉT tiếp (bàn giao khi Cowork sandbox chặn mạng API). Path → TUYỆT ĐỐI để chạy
    từ cwd bất kỳ; token KHÔNG in (vẫn ở .env.local — chỉ truyền JIRA_ENV_FILE trỏ tới file đó). Tái dựng từ args đã truyền."""
    env_file = os.environ.get("JIRA_ENV_FILE") or os.path.join(SCRIPT_DIR, ".env.local")
    env_file = os.path.abspath(os.path.expanduser(env_file))
    parts = [f"JIRA_ENV_FILE={shlex.quote(env_file)}",
             "python3", shlex.quote(os.path.abspath(__file__))]
    if args.test:
        parts += ["--test"]
    if args.list_projects:
        parts += ["--list-projects"]
    if args.keys:
        parts += ["--keys", shlex.quote(args.keys)]
    if args.jql:
        parts += ["--jql", shlex.quote(args.jql)]
    if args.since is not None:
        parts += ["--since"] + ([] if args.since == "__last__" else [shlex.quote(args.since)])
    if args.per_project:
        parts += ["--per-project"]
    if args.vault:
        parts += ["--vault", shlex.quote(os.path.abspath(os.path.expanduser(args.vault)))]
    if args.force:
        parts += ["--force"]
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="Chỉ test kết nối")
    ap.add_argument("--keys", help="Quét riêng các hạng mục công việc, vd: PROJ-102,PROJ-105")
    ap.add_argument("--jql", help='Quét theo JQL, vd: "parent = PROJ-101"')
    ap.add_argument("--since", nargs="?", const="__last__",
                    help='Chỉ quét issue MỚI/CẬP NHẬT. --since 2026-06-01 theo ngày; '
                         '--since (không tham số) = từ lần quét trước (đọc _system/last-import.txt)')
    ap.add_argument("--per-project", action="store_true",
                    help="Mỗi project một thư mục con trong vault (VAULT/<KEY>/...)")
    ap.add_argument("--from-mcp", help="Nạp issues từ file JSON do MCP lưu (không cần token)")
    ap.add_argument("--names", help="File JSON map field id→tên (cho --from-mcp)")
    ap.add_argument("--check-fresh", action="store_true",
                    help="In độ mới của vault (last-import vs hôm nay) dạng JSON rồi thoát")
    ap.add_argument("--list-projects", action="store_true",
                    help="In danh sách project [{key,name}] dạng JSON (cho /claude-knowledge-scan chọn project)")
    ap.add_argument("--force", action="store_true", help="Bỏ qua guard idempotent-per-day")
    ap.add_argument("--emit-command", action="store_true",
                    help="KHÔNG quét — in 1 DÒNG LỆNH (path tuyệt đối) để chạy ở TERMINAL quét tiếp (bàn giao khi "
                         "Cowork sandbox chặn mạng API). Token KHÔNG in (vẫn ở .env.local; chỉ trỏ JIRA_ENV_FILE).")
    ap.add_argument("--vault", help="Đường dẫn vault (override; mặc định OBSIDIAN_VAULT → config vault_path → ./KB-Vault). "
                                    "Tương đối → neo theo project hiện tại.")
    ap.add_argument("--source-id", dest="source_id", help="Token nguồn ghi vào frontmatter note (mặc định "
                    "jira__<host của JIRA_BASE_URL>). Tách Jira ĐA INSTANCE (Cloud/Server) khi báo cáo --source-ids.")
    args = ap.parse_args()
    if args.emit_command:   # BÀN GIAO: in lệnh chạy ở Terminal (KHÔNG quét, KHÔNG cần token/mạng)
        print(_emit_command(args))
        return
    global PER_PROJECT, FIELD_MAP, VAULT, SOURCE_ID
    if args.per_project:
        PER_PROJECT = True
    if args.vault:   # override cao nhất — neo theo DATA (project)
        VAULT = _resolve_vault(args.vault, DATA)
    SOURCE_ID = args.source_id or f"jira__{_source_id()}"   # token nguồn cho frontmatter (tách đa instance)

    # --check-fresh: chỉ đọc vault, KHÔNG cần token/cấu hình kết nối
    if args.check_fresh:
        print(json.dumps(freshness_info(), ensure_ascii=False))
        return

    # --from-mcp: nạp từ file MCP (Cloud) — KHÔNG cần token; tái dùng toàn bộ logic ghi note
    if args.from_mcp:
        global FROM_MCP, FIELD_MAP
        FROM_MCP = True
        if args.since is not None and has_daily_success() and not args.force:
            print(f"Hôm nay ({_today()}) đã đồng bộ thành công → bỏ qua (dùng --force để ép).")
            return
        if args.names and os.path.exists(args.names):
            try:
                FIELD_MAP = dict(json.load(open(args.names, encoding="utf-8")))
            except Exception:
                pass
        issues = load_mcp_issues(args.from_mcp)
        if not issues:
            die(f"Không có hạng mục công việc nào trong file {args.from_mcp}.")
        print(f"Nạp {len(issues)} issue từ MCP file → vault...")
        run_from_issues(issues)
        save_last_import()
        mark_daily_success()
        return

    check_config()
    if args.list_projects:
        projects = fetch_projects()
        print(json.dumps([{"key": p["key"], "name": p.get("name", p["key"])} for p in projects],
                         ensure_ascii=False))
        return
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
        if has_daily_success() and not args.force:
            print(f"Hôm nay ({_today()}) đã đồng bộ thành công → bỏ qua (dùng --force để ép).")
            return
        since = read_last_import() if args.since == "__last__" else args.since
        if not since:
            die("Chưa có mốc quét trước. Dùng --since YYYY-MM-DD cho lần đầu.")
        scope = ""
        if PROJECT_KEYS:
            scope = "project in (" + ",".join(PROJECT_KEYS) + ") AND "
        print(f"Quét hạng mục công việc cập nhật từ {since}...")
        run_single(f'{scope}updated >= "{since}" ORDER BY updated ASC')
        save_last_import()
        mark_daily_success()
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
