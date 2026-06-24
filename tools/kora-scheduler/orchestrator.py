#!/usr/bin/env python3
"""
orchestrator.py — Chu trình lịch chạy NỀN của Kora (không cần app Claude).

Một lần `--run <id>`: SCAN/auto-get các nguồn (KHÔNG gác — luôn chạy) → reindex → **CỔNG MẬT
KHẨU (KORA_OPS_PW)** mới gác bước GHI/PHÁT RA NGOÀI → ĐẨY (post) Confluence → đánh dấu độ mới →
sinh report → gửi mail (nếu HOST) → có lỗi thì TẠO TICKET ISSUE + email người phụ trách.
Cổng sai/thiếu → CHỈ chạy scan (kéo tri thức về), BỎ post/report/mail/sync, chỉ cảnh báo.
KHÔNG fail im — exit code ok(0)/partial(2)/failed(1).

Đọc cấu hình từ config/factory-config.yaml + lịch từ tools/kora-scheduler/schedules.json.
Chỉ thư viện chuẩn Python 3. KHÔNG in secret.

Token map:
  scan_list / post_list dùng token "type:name":
    jira:<name>        → import_jira.py --since với JIRA_ENV_FILE=.env.<name> (name=local → .env.local)
    confluence:<space> → sync_confluence.py --pull (scan) / --push (post) --space <space>
    github:<owner/repo>→ sync_github.py --pull (scan; KÉO KB host về local) [--repo nếu có owner/repo]
    gitlab:<group/repo>→ sync_gitlab.py --pull (scan; KÉO KB host về local) [--repo nếu có group/repo]
    sharepoint:<site>  → sync_sharepoint.py --pull (scan) / --push (post) --site <site>
"""
import argparse
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
CONFIG = REPO_ROOT / "config" / "factory-config.yaml"
REGISTRY = HERE / "schedules.json"
JIRA_DIR = REPO_ROOT / "tools" / "jira-to-obsidian"
CONFL_DIR = REPO_ROOT / "tools" / "confluence-sync"
GITHUB_DIR = REPO_ROOT / "tools" / "github-sync"
GITLAB_DIR = REPO_ROOT / "tools" / "gitlab-sync"
SHAREPOINT_DIR = REPO_ROOT / "tools" / "sharepoint-sync"
MAILER = REPO_ROOT / "tools" / "report-mailer" / "send_report.py"
MAILER_ENV = REPO_ROOT / "tools" / "report-mailer" / ".env.local"   # truyền qua KORA_MAILER_ENV
BANNER_PNG = REPO_ROOT / "assets" / "banner-daily-report.jpg"        # truyền --banner → nhúng CID inline
PY = sys.executable or "python3"


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today():
    return datetime.now().strftime("%Y-%m-%d")


def log(msg):
    print(f"[{now_iso()}] {msg}", flush=True)


def load_env(path: Path) -> dict:
    env = {}
    if path and path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def load_config(path: Path) -> dict:
    """factory-config.yaml → dict dotted-key -> scalar (cùng logic với sync_confluence)."""
    result, stack = {}, []
    if not path.exists():
        return result
    import re
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or raw.lstrip().startswith("- "):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if ":" not in raw.strip():
            continue
        key, _, rawval = raw.strip().partition(":")
        key, rawval = key.strip(), rawval.strip()
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
        if val == "" and not quoted:
            stack.append((indent, key))
            continue
        result[dotted] = val
    return result


def load_schedule(sid: str):
    if not REGISTRY.exists():
        return None
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for s in data.get("schedules", []):
        if s.get("id") == sid:
            return s
    return None


def run_tool(script: Path, args, extra_env=None, cwd=None):
    """Chạy 1 tool Python con; trả (rc, stdout, stderr). KHÔNG raise."""
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    try:
        p = subprocess.run([PY, str(script), *args], cwd=str(cwd or REPO_ROOT),
                           env=env, capture_output=True, text=True, timeout=1800)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)


GATE_SCRIPT = REPO_ROOT / "tools" / "archive-gate" / "verify_ops_password.py"

# File mật khẩu vận hành cho LỊCH NỀN — vì launchd/cron/schtasks KHÔNG có shell env tương tác.
# Đặt 1 lần: ghi `KORA_OPS_PW=<mật khẩu>` vào file dưới (chmod 600). orchestrator TỰ nạp lúc chạy.
OPS_ENV_FILES = [
    Path.home() / ".config" / "claude-knowledge" / "ops-pw.env",   # MỚI macOS/Linux (khuyến nghị)
    Path.home() / ".claude-knowledge" / "ops-pw.env",              # MỚI Windows: %USERPROFILE%\.claude-knowledge\
    Path.home() / ".config" / "kora" / "ops-pw.env",               # CŨ — backward-compat (máy đặt trước rename)
    Path.home() / ".kora" / "ops-pw.env",                          # CŨ Windows: %USERPROFILE%\.kora\
]


def load_ops_env():
    """Nạp KORA_OPS_PW (và biến khác) từ file env vào os.environ cho lịch nền.

    launchd/cron/schtasks chạy orchestrator TRỰC TIẾP (không qua shell login) nên KORA_OPS_PW
    không có sẵn → cổng mật khẩu sẽ fail và bỏ cả lượt. Hàm này nạp từ OPS_ENV_FILES, CHỈ đặt
    biến CHƯA có trong môi trường (không ghi đè khi chạy tay đã export). KHÔNG in giá trị."""
    for p in OPS_ENV_FILES:
        try:
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if s.startswith("export "):
                    s = s[7:].strip()
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
        except OSError:
            continue


def ops_gate() -> bool:
    """Cổng mật khẩu vận hành cho bước GHI/PHÁT ra ngoài (POST/MAIL/SYNC) trong lịch nền.
    Mật khẩu lấy từ env KORA_OPS_PW (orchestrator tự nạp từ ~/.config/claude-knowledge/ops-pw.env). KHÔNG in mật khẩu."""
    rc, _o, _e = run_tool(GATE_SCRIPT, [])
    return rc == 0


# ───────────────────────────── ticket issue ────────────────────────────────
def create_ticket(cfg, title, body_md):
    """Tạo ticket sự cố khi lịch lỗi. target: confluence | jira | none. Trả (created, url|err)."""
    target = (cfg.get("scheduler.ticket_issue.target") or "confluence").lower()
    if target == "none" or (cfg.get("scheduler.ticket_issue.enabled") or "true") in ("false", "False"):
        return False, "ticket_issue tắt"
    try:
        if target == "confluence":
            return _ticket_confluence(cfg, title, body_md)
        if target == "jira":
            return _ticket_jira(cfg, title, body_md)
    except Exception as e:  # noqa: BLE001
        return False, f"tạo ticket lỗi: {e}"
    return False, "target không hợp lệ"


def _ticket_confluence(cfg, title, body_md):
    sys.path.insert(0, str(CONFL_DIR))
    import sync_confluence as sc  # noqa: E402
    env = sc.load_env(CONFL_DIR / ".env.local")
    client = sc.build_client(env, cfg)  # die nếu thiếu creds → bắt ở caller
    space = cfg.get("scheduler.ticket_issue.space_key") or cfg.get("confluence.space_key")
    if not space:
        return False, "thiếu ticket_issue.space_key"
    storage = sc.md_to_storage(body_md)
    # idempotent theo ngày: nhận trang cùng title nếu đã có
    found = sc.find_page_by_title(client, space, title)
    if found:
        pid = found["id"]
        _st, cur = client.get(f"/rest/api/content/{pid}", {"expand": "version"})
        ver = cur.get("version", {}).get("number", 1)
        client.put(f"/rest/api/content/{pid}", {
            "id": pid, "type": "page", "title": title, "space": {"key": space},
            "version": {"number": ver + 1}, "body": {"storage": {"value": storage, "representation": "storage"}}})
        return True, f"{client.base}/spaces/{space}/pages/{pid}"
    _st, res = client.post("/rest/api/content", {
        "type": "page", "title": title, "space": {"key": space},
        "metadata": {"labels": [{"name": "kora-incident"}]},
        "body": {"storage": {"value": storage, "representation": "storage"}}})
    return True, f"{client.base}/spaces/{space}/pages/{res.get('id')}"


def _ticket_jira(cfg, title, body_md):
    import base64
    env = load_env(JIRA_DIR / ".env.local")
    base = (env.get("JIRA_BASE_URL") or "").rstrip("/")
    project = cfg.get("scheduler.ticket_issue.jira_project")
    if not (base and project):
        return False, "thiếu JIRA_BASE_URL hoặc ticket_issue.jira_project"
    email, token = env.get("JIRA_EMAIL"), env.get("JIRA_PAT")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if email and token:  # Cloud
        headers["Authorization"] = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
    elif token:           # Server
        headers["Authorization"] = f"Bearer {token}"
    else:
        return False, "thiếu token Jira"
    payload = {"fields": {"project": {"key": project}, "summary": title[:250],
                          "description": body_md, "issuetype": {"name": "Bug"}}}
    req = urllib.request.Request(base + "/rest/api/2/issue",
                                 data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=45) as r:
        res = json.loads(r.read())
    return True, f"{base}/browse/{res.get('key')}"


def send_error_email(cfg, schedule, subject, body):
    """Mail báo SỰ CỐ (issue ticket) khi lịch nền lỗi — cấu hình tập trung qua /claude-knowledge-alert-mail.

    OVERRIDE: scheduler.error_recipients (khi != rỗng) ÁP cho MỌI lịch, ĐÈ người nhận của
    từng lịch. Đọc config lúc chạy → sửa 1 lần áp cho mọi lịch, KHÔNG cần tạo lại lịch nào.
    Tắt toàn cục bằng scheduler.error_email.enabled=false (vẫn có thể tạo ticket riêng).
    """
    if (cfg.get("scheduler.error_email.enabled") or "true").strip().lower() == "false":
        log("  (mail sự cố đang TẮT toàn cục: scheduler.error_email.enabled=false)")
        return
    override = (cfg.get("scheduler.error_recipients") or "").strip("[]").replace('"', "").replace("'", "")
    recips = [x.strip() for x in override.split(",") if x.strip()]          # 1) override toàn cục
    if not recips:
        recips = schedule.get("email", {}).get("to") or []                  # 2) người nhận của lịch
    if not recips:
        recips = [x.strip() for x in (cfg.get("reports.email.to") or "").split(",") if x.strip()]  # 3) fallback
    if not recips or not MAILER.exists():
        log("  (không gửi được error email: thiếu người nhận hoặc mailer)")
        return
    run_tool(MAILER, ["--to", ",".join(recips), "--subject", subject, "--body", body],
             extra_env={"KORA_MAILER_ENV": str(MAILER_ENV)})


# ──────────────────────────────── pipeline ─────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Chu trình lịch nền Kora.")
    ap.add_argument("--run", metavar="ID", required=True, help="id lịch trong schedules.json")
    ap.add_argument("--once", action="store_true", help="Bỏ qua guard idempotent theo ngày.")
    ap.add_argument("--dry-run", action="store_true", help="In kế hoạch, không thực thi.")
    args = ap.parse_args()

    load_ops_env()  # nạp KORA_OPS_PW từ file cho lịch nền (launchd/cron không có shell env)
    cfg = load_config(CONFIG)
    sch = load_schedule(args.run)
    if not sch:
        log(f"❌ Không thấy lịch id='{args.run}' trong {REGISTRY.name}")
        sys.exit(1)
    if sch.get("enabled") is False:
        log(f"⏸  Lịch '{args.run}' đang TẮT (inactive) → bỏ qua.")
        sys.exit(0)

    log_dir = REPO_ROOT / (cfg.get("scheduler.log_dir") or "reports/scheduler-logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    lock = log_dir / f"{args.run}.lock"
    if lock.exists() and not args.once:
        log("⏭  Lượt trước còn chạy (.lock) → bỏ qua để tránh chồng.")
        sys.exit(0)
    lock.write_text(now_iso(), encoding="utf-8")

    run_errors, sources, posted = [], [], []
    is_user_pkg = (cfg.get("package.type") or "host").lower() == "user" or \
        (REPO_ROOT / ".claude-knowledge-user").exists() or (REPO_ROOT / ".kora-user").exists()  # marker mới + cũ (backward-compat)
    started = now_iso()
    try:
        # 0) CỔNG MẬT KHẨU vận hành — chỉ gác bước GHI/PHÁT RA NGOÀI (post · report · mail · sync).
        #    SCAN/auto-get (kéo tri thức VỀ local) KHÔNG bị gác → vẫn chạy khi thiếu/sai mật khẩu.
        gate_ok = True
        if not args.dry_run:
            gate_ok = ops_gate()
        wants_outward = bool(sch.get("post_list") or (sch.get("report") or {}).get("enabled")
                             or (sch.get("email") or {}).get("enabled") or (sch.get("sync") or {}).get("enabled"))
        if not gate_ok:
            log("🔒 Thiếu/sai KORA_OPS_PW → CHỈ chạy SCAN (kéo tri thức về). "
                "BỎ QUA post · report · mail · sync.")
            if wants_outward:
                run_errors.append({"step": "gate",
                                   "reason": "Thiếu KORA_OPS_PW — đã chạy scan, BỎ QUA post/report/mail/sync"})

        # 1) SCAN (auto-get) — LUÔN chạy (KHÔNG gác): kéo tri thức mới về local.
        for tok in sch.get("scan_list", []):
            kind, _, name = tok.partition(":")
            log(f"SCAN {tok}")
            if args.dry_run:
                sources.append({"name": tok, "fresh": None, "error": "(dry)"}); continue
            if kind == "jira":
                envfile = ".env.local" if name in ("", "local", "default") else f".env.{name}"
                rc, out, err = run_tool(JIRA_DIR / "import_jira.py", ["--since"],
                                        extra_env={"JIRA_ENV_FILE": envfile}, cwd=JIRA_DIR)
            elif kind == "confluence":
                rc, out, err = run_tool(CONFL_DIR / "sync_confluence.py",
                                        ["--pull"] + (["--space", name] if name else []))
            elif kind == "github":
                # Kéo KB host từ repo GitHub private về local (vd máy USER pull KB chung).
                # token "github:owner/repo" → --repo; "github:" → dùng repo trong config + .env.local.
                rc, out, err = run_tool(GITHUB_DIR / "sync_github.py",
                                        ["--pull"] + (["--repo", name] if name and "/" in name else []))
            elif kind == "gitlab":
                # Kéo KB host từ repo GitLab private về local. "gitlab:group/repo" → --repo; "gitlab:" → config.
                rc, out, err = run_tool(GITLAB_DIR / "sync_gitlab.py",
                                        ["--pull"] + (["--repo", name] if name and "/" in name else []))
            elif kind == "sharepoint":
                rc, out, err = run_tool(SHAREPOINT_DIR / "sync_sharepoint.py",
                                        ["--pull"] + (["--site", name] if name else []))
            else:
                rc, out, err = 1, "", f"loại nguồn không hỗ trợ: {kind}"
            if rc not in (0, 2):
                run_errors.append({"step": "scan", "source": tok, "reason": (err or out)[:300]})
                sources.append({"name": tok, "fresh": False, "error": (err or out)[:200]})
            else:
                sources.append({"name": tok, "fresh": True, "error": None})

        # 2) REINDEX — LUÔN (sau scan, để index/graph khớp dữ liệu mới). Local, không gác.
        if not args.dry_run:
            run_tool(REPO_ROOT / "tools" / "kb-indexer" / "build_index.py", ["--root", "."])

        # 3) POST (đẩy lên Confluence chung) — chỉ khi qua cổng
        for tok in (sch.get("post_list", []) if (gate_ok or args.dry_run) else []):
            kind, _, name = tok.partition(":")
            log(f"POST {tok}")
            if args.dry_run:
                posted.append({"target": tok, "result": "(dry)"}); continue
            if kind == "confluence":
                rc, out, err = run_tool(CONFL_DIR / "sync_confluence.py",
                                        ["--push"] + (["--space", name] if name else []))
                posted.append({"target": tok, "result": out.strip()[-200:] or err[-200:]})
                if rc not in (0,):
                    run_errors.append({"step": "post", "target": tok, "reason": (err or out)[:300]})
            elif kind == "sharepoint":
                rc, out, err = run_tool(SHAREPOINT_DIR / "sync_sharepoint.py",
                                        ["--push"] + (["--site", name] if name else []))
                posted.append({"target": tok, "result": out.strip()[-200:] or err[-200:]})
                if rc not in (0,):
                    run_errors.append({"step": "post", "target": tok, "reason": (err or out)[:300]})
            else:
                run_errors.append({"step": "post", "target": tok, "reason": f"loại đích không hỗ trợ: {kind}"})

        # 4) REPORT + MAIL — chỉ HOST (gói user không có) và CHỈ khi qua cổng.
        # Report SCOPE đúng project của lịch (đã được SCAN ở bước 1 → dữ liệu mới nhất).
        report = None
        if gate_ok and not is_user_pkg and not args.dry_run:
            rep_cfg = sch.get("report") or {}
            rep_projs = [p for p in (rep_cfg.get("projects") or []) if p]
            scope = (rep_cfg.get("scope") or "all").lower()
            rdays = int(rep_cfg.get("recent_days") or 30)
            # FULL-scan (status/comment MỚI NHẤT, GHI ĐÈ) project báo cáo từ MỌI nguồn Jira API trong scan_list
            # (đa nguồn / đa domain) — mỗi nguồn CHỈ quét project NÓ CÓ (list-projects ∩ rep_projs) để tránh JQL lỗi
            # vì key lạ. (Nguồn MCP KHÔNG có trong scan_list → nền không kéo được; cần kết nối Jira đó qua API.)
            if rep_projs:
                for tok in sch.get("scan_list", []):
                    if tok.partition(":")[0] != "jira":
                        continue
                    nm = tok.partition(":")[2]
                    ef = ".env.local" if nm in ("", "local", "default") else f".env.{nm}"
                    rc_lp, out_lp, _ = run_tool(JIRA_DIR / "import_jira.py", ["--list-projects"],
                                                extra_env={"JIRA_ENV_FILE": ef}, cwd=JIRA_DIR)
                    here = set()
                    if rc_lp == 0:
                        try:
                            here = {p.get("key") for p in json.loads(out_lp or "[]") if isinstance(p, dict)}
                        except Exception:  # noqa: BLE001
                            here = set()
                    want = [k for k in rep_projs if k in here] if here else rep_projs  # list-projects lỗi → thử tất cả
                    if not want:
                        continue
                    # Dự án lớn: scope != all → bound fetch theo 'updated >= -Nd' (nhẹ); all → full.
                    jql = f"project in ({','.join(want)})"
                    if scope != "all":
                        jql += f" AND updated >= -{rdays}d"
                    log(f"Scan report projects {want} từ jira:{nm} (scope={scope}, {rdays}d nếu giới hạn)")
                    rc_s, o_s, e_s = run_tool(JIRA_DIR / "import_jira.py", ["--jql", jql],
                                              extra_env={"JIRA_ENV_FILE": ef}, cwd=JIRA_DIR)
                    if rc_s != 0:
                        run_errors.append({"step": "report-scan", "source": nm, "reason": (e_s or o_s)[:200]})
                run_tool(REPO_ROOT / "tools" / "kb-indexer" / "build_index.py", ["--root", "."])
            rep_args = (["--projects", ",".join(rep_projs)] if rep_projs else [])
            if scope != "all":
                rep_args += ["--scope", scope, "--recent-days", str(rdays)]
            rc, out, err = run_tool(REPO_ROOT / "tools" / "progress-report" / "build_report.py", rep_args)
            if rc != 0:
                run_errors.append({"step": "report", "reason": (err or out)[:300]})
            else:
                report = "reports/progress-report-latest.html"
                # AI risk analysis (headless, best-effort)
                _ai_analysis(cfg, log_dir)
                em = sch.get("email", {})
                mail_on = (em.get("enabled") or
                           (cfg.get("reports.email.enabled") or "false").lower() == "true")
                provider = (em.get("provider") or cfg.get("reports.email.provider") or "smtp").lower()
                recips = em.get("to") or [x.strip() for x in
                                          (cfg.get("reports.email.to") or "").split(",") if x.strip()]
                if mail_on and provider != "smtp":
                    log(f"  (mail provider={provider} cần gửi tương tác qua connector — "
                        f"lịch nền chỉ gửi SMTP → bỏ qua)")
                elif mail_on and recips and MAILER.exists():
                    subj = (cfg.get("reports.email.subject") or "Báo cáo tiến độ {date}").replace("{date}", today())
                    # report vừa build ở 4) (vài giây trước) → guard --stale-after-min của send_report (mặc định 30')
                    # KHÔNG chặn; nếu build lỗi/bỏ qua thì file -latest cũ → guard CHẶN, không gửi bản cũ. File đính
                    # kèm tự đổi tên có ngày-giờ (progress-report-<stamp>.html) → mỗi mail một bản khác.
                    rc2, o2, e2 = run_tool(MAILER, ["--to", ",".join(recips), "--subject", subj,
                                                    "--html-file", "reports/email-body-latest.html",
                                                    "--no-attach-html", "--banner", str(BANNER_PNG),
                                                    "--attach", "reports/progress-report-latest.html",
                                                    "--split"],   # mỗi người nhận 1 mail riêng
                                           extra_env={"KORA_MAILER_ENV": str(MAILER_ENV)})
                    if rc2 != 0:
                        run_errors.append({"step": "email", "reason": (e2 or o2)[:300]})

        # 4.5) SYNC KB lên target (versioning + push) — chỉ khi bật & qua cổng. Áp cả gói USER.
        sy = sch.get("sync", {})
        if sy.get("enabled") and (gate_ok or args.dry_run):
            targets = sy.get("targets", [])
            log(f"SYNC targets={targets}")
            if not args.dry_run:
                run_tool(REPO_ROOT / "tools" / "kb-sync" / "version_mark.py", ["--root", ".", "--apply"])
                run_tool(REPO_ROOT / "tools" / "kb-indexer" / "build_index.py", ["--root", "."])
                if "confluence" in targets:
                    rc, out, err = run_tool(CONFL_DIR / "sync_confluence.py", ["--push"])
                    posted.append({"target": "sync:confluence", "result": (out.strip()[-150:] or err[-150:])})
                    if rc not in (0,):
                        run_errors.append({"step": "sync", "target": "confluence", "reason": (err or out)[:300]})
                if "github" in targets:
                    rc, out, err = run_tool(GITHUB_DIR / "sync_github.py", ["--push"])
                    posted.append({"target": "sync:github", "result": (out.strip()[-150:] or err[-150:])})
                    if rc not in (0,):
                        run_errors.append({"step": "sync", "target": "github", "reason": (err or out)[:300]})
                if "gitlab" in targets:
                    rc, out, err = run_tool(GITLAB_DIR / "sync_gitlab.py", ["--push"])
                    posted.append({"target": "sync:gitlab", "result": (out.strip()[-150:] or err[-150:])})
                    if rc not in (0,):
                        run_errors.append({"step": "sync", "target": "gitlab", "reason": (err or out)[:300]})
                if "sharepoint" in targets:
                    rc, out, err = run_tool(SHAREPOINT_DIR / "sync_sharepoint.py", ["--push"])
                    posted.append({"target": "sync:sharepoint", "result": (out.strip()[-150:] or err[-150:])})
                    if rc not in (0,):
                        run_errors.append({"step": "sync", "target": "sharepoint", "reason": (err or out)[:300]})

        # 5) TICKET + ERROR EMAIL nếu có lỗi
        ticket = {"created": False, "url": None}
        if run_errors and not args.dry_run:
            title = f"Sự cố lịch {args.run} — {today()}"
            body = _incident_body(args.run, run_errors, sources)
            try:
                created, url = create_ticket(cfg, title, body)
                ticket = {"created": created, "url": url}
            except SystemExit:
                ticket = {"created": False, "url": "thiếu creds tạo ticket"}
            except Exception as e:  # noqa: BLE001
                ticket = {"created": False, "url": str(e)}
            send_error_email(cfg, sch, title, body)

        status = "failed" if (run_errors and not sources) else ("partial" if run_errors else "ok")
        record = {"id": args.run, "started_at": started, "finished_at": now_iso(),
                  "status": status, "sources": sources, "posted": posted,
                  "report": report, "ticket_issue": ticket, "errors": run_errors}
        if not args.dry_run:
            (log_dir / f"last-run-{args.run}.json").write_text(
                json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"DONE status={status} errors={len(run_errors)} ticket={ticket.get('created')}")
        sys.exit({"ok": 0, "partial": 2, "failed": 1}[status])
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


def _incident_body(sid, errors, sources):
    lines = [f"Lịch Kora `{sid}` gặp lỗi lúc {now_iso()}.", "", "## Lỗi"]
    for e in errors:
        loc = e.get("source") or e.get("target") or e.get("step")
        lines.append(f"- **{e.get('step')}** ({loc}): {e.get('reason')}")
    lines += ["", "## Nguồn đã quét"]
    for s in sources:
        lines.append(f"- {s['name']}: {'OK' if s.get('fresh') else 'LỖI — ' + str(s.get('error'))}")
    return "\n".join(lines)


def _ai_analysis(cfg, log_dir):
    mode = (cfg.get("scheduler.ai_risk_analysis.mode") or "auto").lower()
    if mode == "off":
        return
    claude = cfg.get("scheduler.ai_risk_analysis.claude_bin") or "auto"
    if claude == "auto":
        from shutil import which
        claude = which("claude")
    if not claude:
        log("  (AI analysis: không thấy 'claude' bin — bỏ qua, report vẫn có dữ liệu)")
        return
    data = REPO_ROOT / "reports" / f"progress-data-{today()}.json"
    if not data.exists():
        return
    prompt = (
        "Bạn là trợ lý phân tích tiến độ dự án. Đọc JSON tiến độ ở cuối và viết phân tích CHI TIẾT (tiếng Việt) "
        "cho quản lý, dùng markdown — MỖI MỤC bắt đầu bằng '## ' theo ĐÚNG thứ tự sau:\n"
        "## 🔴 Rủi ro cao (blocker)\n"
        "   - <mã hạng mục> — <vấn đề> (<assignee>): <tác động> → <đề xuất xử lý>\n"
        "## 🟡 Rủi ro vừa / Cần theo dõi\n"
        "   - tương tự nhưng mức nhẹ hơn\n"
        "## 🟢 Điểm tích cực\n"
        "   - thành tựu, velocity tốt, hạng mục đã sạch lỗi (kèm SỐ)\n"
        "## 🧩 Độ phức tạp (TRỌNG TÂM)\n"
        "   - đọc `complexity` trong JSON: nêu hạng mục PHỨC TẠP CAO (điểm >= ngưỡng, số càng lớn càng phức tạp) — "
        "ai phụ trách, rủi ro/đề xuất ưu tiên review + nguồn lực cho nhóm điểm cao\n"
        "## 👥 Phân tích theo thành viên\n"
        "   Một BẢNG markdown: | Thành viên | Tổng | Done | Đang làm | Ghi chú |\n"
        "   rồi 1–2 dòng nêu ai quá tải / đa nhiệm, ai còn dư công, gợi ý cân bằng.\n"
        "## 📅 Dự đoán sprint / timeline\n"
        "   - nguy cơ trượt (theo NGÀY LÀM VIỆC), lý do BẰNG SỐ, mốc tới hạn cụ thể\n"
        "## 🎯 Hành động ưu tiên\n"
        "   1. việc cần làm ngay (ai · khi nào)\n"
        "## 📌 Tóm tắt điều hành\n"
        "   2–3 câu cho lãnh đạo.\n\n"
        "QUY ƯỚC: 8h = 1 ngày công; bỏ Thứ 7/CN; so với 'expected_so_far' (số NGÀY LÀM VIỆC ĐÃ trôi qua) — log đủ "
        "8h/ngày là ĐÚNG TIẾN ĐỘ, KHÔNG phải OT; duedate tính ĐẾN HẾT NGÀY (start 15 / due 16 = 1 ngày). Trích số "
        "liệu CỤ THỂ (mã hạng mục, tên người, số giờ/ngày) từ JSON — TUYỆT ĐỐI không nói chung chung.\n\n"
        + data.read_text(encoding='utf-8')[:9000])
    # Bypass quyền → headless/cron KHÔNG kẹt prompt (bật/tắt qua config; mặc định bật).
    skip = (cfg.get("scheduler.ai_risk_analysis.skip_permissions") or "true").strip().lower() != "false"
    cmd = [claude, "-p", prompt] + (["--dangerously-skip-permissions"] if skip else [])
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if p.returncode == 0 and p.stdout.strip():
            md_file = REPO_ROOT / "reports" / "ai-analysis-latest.md"
            md_file.write_text(p.stdout, encoding="utf-8")
            (log_dir / f"ai-analysis-{today()}.md").write_text(p.stdout, encoding="utf-8")
            # render CARD MÀU + chèn vào email — DÙNG renderer build_report (thống nhất path nền & tương tác)
            run_tool(REPO_ROOT / "tools" / "progress-report" / "build_report.py", ["--inject-ai", str(md_file)])
            log("  (AI analysis: đã ghi + chèn card màu vào email)")
        else:
            log(f"  (AI analysis: claude rc={p.returncode} — email giữ placeholder)")
    except Exception as e:  # noqa: BLE001
        log(f"  (AI analysis bỏ qua: {e})")


if __name__ == "__main__":
    main()
