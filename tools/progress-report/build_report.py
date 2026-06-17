#!/usr/bin/env python3
"""
build_report.py — Sinh REPORT TIẾN ĐỘ dự án từ vault Jira (local, KHÔNG cần server).

Đọc các note `source: jira` trong vault (frontmatter máy-đọc do import_jira.py ghi) → tính
metrics tiến độ (trạng thái, % hoàn thành, sprint đang chạy, theo assignee, thời gian est/log/
remaining, rủi ro) → xuất:
  - reports/progress-data-<ngày>.json        (số liệu thô)
  - reports/progress-report-<ngày>.html      (dashboard standalone, mở bằng trình duyệt)
  - reports/progress-report-latest.html       (bản mới nhất)
  - reports/progress-report-fragment.html     (body-only, cho visualize.show_widget render inline Cowork)

Dùng:
  python3 build_report.py                       # vault đọc từ config/factory-config.yaml
  python3 build_report.py --vault <path>        # chỉ định vault
  python3 build_report.py --out <dir>           # thư mục xuất (mặc định reports/)
Chỉ dùng thư viện chuẩn Python 3 — KHÔNG cần pip install gì.
"""

import argparse
import glob
import html
import json
import os
import re
import sys
from datetime import date, datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Nhóm trạng thái mặc định (đổi qua config > reports.status_map nếu cần)
_DONE = ("done", "closed", "resolved", "complete", "completed", "hoàn thành", "xong", "đã xong")
_PROG = ("progress", "review", "doing", "testing", "qa", "đang", "in dev", "developing")

PAL = {  # palette đồng bộ với landing index.html
    "ink": "#eaf4ff", "mut": "#9fb4d6", "blue": "#1e6fc0", "orange": "#f47b20",
    "green": "#1fa84a", "teal": "#2dd4bf", "vio": "#9b6bff", "red": "#ff5f7a",
    "card": "rgba(10,28,54,.62)", "deep": "#02101f", "line": "rgba(255,255,255,.12)",
}


def die(msg):
    print(f"LỖI: {msg}")
    sys.exit(1)


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def pct(a, b):
    return round(100 * a / b) if b else 0


def human_seconds(s):
    try:
        s = int(s)
    except (TypeError, ValueError):
        return "—"
    if s <= 0:
        return "0h"
    h, m = divmod(s // 60, 60)
    parts = [p for p in (f"{h}h" if h else "", f"{m}m" if m else "") if p]
    return " ".join(parts) or "0h"


def status_group(status, status_map=None):
    s = (status or "").strip().lower()
    if status_map:
        for grp, names in status_map.items():
            if any(n.strip().lower() == s for n in names):
                return grp
    if any(k in s for k in _DONE):
        return "done"
    if any(k in s for k in _PROG):
        return "in_progress"
    return "todo"


# ── Đọc vault ─────────────────────────────────────────────────────────────
def parse_frontmatter(text):
    """Tách frontmatter YAML đơn giản (key: value) → dict, ép số khi được."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_raw = text[3:end].strip("\n")
    body = text[end + 4:]
    fm = {}
    for line in fm_raw.splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if v == "":
            continue
        if re.fullmatch(r"-?\d+", v):
            fm[k] = int(v)
        elif re.fullmatch(r"-?\d+\.\d+", v):
            fm[k] = float(v)
        else:
            fm[k] = v
    return fm, body


def issue_summary(fm, body):
    m = re.search(r"^#\s+\S+\s+—\s+(.+)$", body, re.M)
    if m:
        return m.group(1).strip()
    return fm.get("jira_key", "")


def load_issues(vault):
    issues = []
    for root, _dirs, files in os.walk(vault):
        if os.sep + "_system" in root:
            continue
        for fn in files:
            if not fn.endswith(".md"):
                continue
            try:
                text = open(os.path.join(root, fn), encoding="utf-8").read()
            except Exception:
                continue
            fm, body = parse_frontmatter(text)
            if fm.get("source") != "jira" or not fm.get("jira_key"):
                continue
            fm["_summary"] = issue_summary(fm, body)
            issues.append(fm)
    return issues


def vault_freshness(vault, stale_after_days=1):
    """Đọc mọi mốc last-import-*.txt trong vault → mốc mới nhất + cờ CŨ (so hôm nay)."""
    marks = glob.glob(os.path.join(vault, "**", "last-import-*.txt"), recursive=True)
    marks += glob.glob(os.path.join(vault, "**", "last-import.txt"), recursive=True)
    best = ""
    for p in marks:
        try:
            v = open(p, encoding="utf-8").read().strip()
            if v > best:
                best = v
        except Exception:
            pass
    today = datetime.now().strftime("%Y-%m-%d")
    age = None
    if best:
        try:
            age = (date.today() - date.fromisoformat(best[:10])).days
        except ValueError:
            pass
    is_stale = (not best) or (age is not None and age >= stale_after_days) or (best[:10] < today)
    return {"last_import": best or None, "is_stale": is_stale, "age_days": age}


# ── Tính metrics ──────────────────────────────────────────────────────────
def _time_sum(items):
    return {
        "estimate_s": sum(int(i.get("time_estimate_s") or 0) for i in items),
        "spent_s": sum(int(i.get("time_spent_s") or 0) for i in items),
        "remaining_s": sum(int(i.get("time_remaining_s") or 0) for i in items),
    }


def issue_group(i, smap=None):
    """Nhóm trạng thái: ưu tiên status_category (statusCategory Jira — tin cậy) rồi mới đoán theo tên."""
    sc = i.get("status_category")
    if sc in ("todo", "in_progress", "done"):
        return sc
    return status_group(i.get("status"), smap)


def _status_breakdown(items, smap):
    g = {"todo": 0, "in_progress": 0, "done": 0}
    for i in items:
        g[issue_group(i, smap)] += 1
    return g


def compute(issues, smap, today):
    total = len(issues)
    grp = _status_breakdown(issues, smap)
    by_type = {}
    for i in issues:
        by_type[i.get("type", "issue")] = by_type.get(i.get("type", "issue"), 0) + 1
    tsum = _time_sum(issues)
    tsum["pct_logged"] = pct(tsum["spent_s"], tsum["estimate_s"])

    # Sprint đang chạy
    active = [i for i in issues if (i.get("sprint_state") or "").lower() == "active" and i.get("sprint_name")]
    sprints = {}
    for i in active:
        sprints.setdefault(i["sprint_name"], []).append(i)
    active_sprints = []
    for name, items in sorted(sprints.items()):
        g = _status_breakdown(items, smap)
        active_sprints.append({
            "name": name, "end": items[0].get("sprint_end", ""), "total": len(items),
            "done": g["done"], "pct_done": pct(g["done"], len(items)),
            "by_status": g, "time": _time_sum(items),
            "issues": sorted([{
                "key": i.get("jira_key"), "summary": i.get("_summary", ""),
                "assignee": i.get("assignee", "—"), "status": i.get("status", ""),
                "group": issue_group(i, smap),
                "spent_s": int(i.get("time_spent_s") or 0), "est_s": int(i.get("time_estimate_s") or 0),
                "story_points": i.get("story_points", ""),
            } for i in items], key=lambda x: x["group"]),
        })

    # Theo assignee
    who = {}
    for i in issues:
        who.setdefault(i.get("assignee") or "(chưa giao)", []).append(i)
    by_assignee = []
    for name, items in who.items():
        g = _status_breakdown(items, smap)
        by_assignee.append({
            "assignee": name, "total": len(items), "todo": g["todo"],
            "in_progress": g["in_progress"], "done": g["done"], "pct_done": pct(g["done"], len(items)),
            "time": _time_sum(items),
            "story_points": sum(float(i["story_points"]) for i in items if isinstance(i.get("story_points"), (int, float))),
        })
    by_assignee.sort(key=lambda x: (-x["total"], x["assignee"]))

    # Theo project (cho dashboard nhiều project / filter theo dự án)
    proj = {}
    for i in issues:
        proj.setdefault(i.get("project") or "—", []).append(i)
    by_project = []
    for name, items in proj.items():
        g = _status_breakdown(items, smap)
        by_project.append({"project": name, "total": len(items), "done": g["done"],
                           "pct_done": pct(g["done"], len(items)), "time": _time_sum(items)})
    by_project.sort(key=lambda x: -x["total"])

    # Rủi ro
    overdue, no_assignee, no_est = [], [], []
    for i in issues:
        dd = str(i.get("duedate") or "")[:10]
        if dd and dd < today and issue_group(i, smap) != "done":
            overdue.append({"key": i.get("jira_key"), "summary": i.get("_summary", ""),
                            "assignee": i.get("assignee", "—"), "duedate": dd, "status": i.get("status", "")})
    for i in active:
        if not i.get("assignee"):
            no_assignee.append({"key": i.get("jira_key"), "summary": i.get("_summary", "")})
        if not i.get("time_estimate_s"):
            no_est.append({"key": i.get("jira_key"), "summary": i.get("_summary", "")})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "total": total,
        "by_status_group": grp, "pct_done": pct(grp["done"], total), "by_type": by_type,
        "time": tsum, "active_sprints": active_sprints, "by_assignee": by_assignee, "by_project": by_project,
        "risks": {"overdue": overdue[:50], "active_sprint_no_assignee": no_assignee[:50],
                  "active_sprint_no_estimate": no_est[:50]},
        "with_time": sum(1 for i in issues if i.get("time_estimate_s") or i.get("time_spent_s")),
    }


# ── Render HTML ───────────────────────────────────────────────────────────
def kpi(label, value, sub="", color="teal"):
    return (f'<div class="pr-kpi"><div class="pr-kpi-v" style="color:{PAL[color]}">{value}</div>'
            f'<div class="pr-kpi-l">{esc(label)}</div>'
            f'{f"<div class=pr-kpi-s>{esc(sub)}</div>" if sub else ""}</div>')


def stacked(grp):
    t = max(grp["todo"] + grp["in_progress"] + grp["done"], 1)
    seg = lambda n, c: f'<span style="width:{100*grp[n]/t:.1f}%;background:{PAL[c]}"></span>' if grp[n] else ""
    return (f'<div class="pr-stack">{seg("done","green")}{seg("in_progress","blue")}{seg("todo","mut")}</div>'
            f'<div class="pr-legend"><b style="color:{PAL["green"]}">●</b> Done {grp["done"]} '
            f'<b style="color:{PAL["blue"]}">●</b> Đang làm {grp["in_progress"]} '
            f'<b style="color:{PAL["mut"]}">●</b> Chưa làm {grp["todo"]}</div>')


def bar(p, color="teal"):
    return f'<div class="pr-bar"><span style="width:{min(p,100)}%;background:{PAL[color]}"></span></div>'


def render_fragment(m, vault):
    t = m["time"]
    cards = "".join([
        kpi("Tổng issue", m["total"], color="ink"),
        kpi("Hoàn thành", f'{m["pct_done"]}%', f'{m["by_status_group"]["done"]}/{m["total"]}', "green"),
        kpi("Ước tính", human_seconds(t["estimate_s"]), color="blue"),
        kpi("Đã log", human_seconds(t["spent_s"]), f'{t["pct_logged"]}% ước tính', "teal"),
        kpi("Còn lại", human_seconds(t["remaining_s"]), color="orange"),
        kpi("Sprint đang chạy", len(m["active_sprints"]), color="vio"),
    ])

    sprint_html = ""
    for s in m["active_sprints"]:
        rows = "".join(
            f'<tr><td class="pr-k">{esc(i["key"])}</td><td>{esc(i["summary"])[:70]}</td>'
            f'<td>{esc(i["assignee"])}</td>'
            f'<td><span class="pr-pill pr-{i["group"]}">{esc(i["status"])}</span></td>'
            f'<td>{human_seconds(i["spent_s"])}/{human_seconds(i["est_s"])}</td>'
            f'<td>{esc(i["story_points"])}</td></tr>' for i in s["issues"])
        sprint_html += (
            f'<div class="pr-card"><div class="pr-card-h"><b>🏃 {esc(s["name"])}</b>'
            f'<span class="pr-mut">{esc(s["end"]) and "đến " + esc(s["end"])} · {s["done"]}/{s["total"]} done · '
            f'log {human_seconds(s["time"]["spent_s"])}/{human_seconds(s["time"]["estimate_s"])}</span></div>'
            f'{bar(s["pct_done"], "green")}'
            f'<table class="pr-t"><thead><tr><th>Key</th><th>Tóm tắt</th><th>Assignee</th>'
            f'<th>Trạng thái</th><th>Log/Ước tính</th><th>SP</th></tr></thead><tbody>{rows}</tbody></table></div>')
    if not m["active_sprints"]:
        sprint_html = '<div class="pr-card pr-mut">Không có sprint đang chạy (active) — kiểm tra field Sprint trên Jira.</div>'

    arows = "".join(
        f'<tr><td>{esc(a["assignee"])}</td><td>{a["total"]}</td>'
        f'<td>{a["todo"]}</td><td>{a["in_progress"]}</td><td>{a["done"]}</td>'
        f'<td style="min-width:90px">{bar(a["pct_done"], "green")}</td>'
        f'<td>{human_seconds(a["time"]["spent_s"])}/{human_seconds(a["time"]["estimate_s"])}</td>'
        f'<td>{a["story_points"] or ""}</td></tr>' for a in m["by_assignee"])
    assignee_html = (
        f'<table class="pr-t"><thead><tr><th>Assignee</th><th>Tổng</th><th>Chưa</th><th>Đang</th>'
        f'<th>Done</th><th>% Done</th><th>Log/Ước tính</th><th>SP</th></tr></thead><tbody>{arows}</tbody></table>')

    def risk_list(items, fmt):
        return "".join(f"<li>{fmt(x)}</li>" for x in items) or '<li class="pr-mut">(không có)</li>'
    risks = m["risks"]
    risk_html = (
        f'<div class="pr-card"><b style="color:{PAL["red"]}">⚠ Quá hạn ({len(risks["overdue"])})</b><ul class="pr-ul">'
        + risk_list(risks["overdue"], lambda x: f'<span class="pr-k">{esc(x["key"])}</span> {esc(x["summary"])[:60]} '
                    f'<span class="pr-mut">— {esc(x["assignee"])}, hạn {esc(x["duedate"])}</span>') + '</ul></div>'
        f'<div class="pr-card"><b style="color:{PAL["orange"]}">Sprint active thiếu assignee ({len(risks["active_sprint_no_assignee"])}) / thiếu ước tính ({len(risks["active_sprint_no_estimate"])})</b>'
        f'<ul class="pr-ul">'
        + risk_list(risks["active_sprint_no_assignee"], lambda x: f'<span class="pr-k">{esc(x["key"])}</span> {esc(x["summary"])[:60]} <span class="pr-mut">— chưa giao</span>')
        + '</ul></div>')

    gen = m["generated_at"][:16].replace("T", " ")
    note = "" if m["with_time"] else ('<div class="pr-warn">Chưa thấy dữ liệu thời gian — '
                                      'hãy <b>quét jira</b> lại bằng bản mới (v1.1.0+) để có est/log/remaining.</div>')
    fresh = m.get("freshness") or {}
    stale = ""
    if fresh.get("is_stale"):
        li = fresh.get("last_import") or "chưa rõ"
        ag = fresh.get("age_days")
        agtxt = f" ({ag} ngày trước)" if isinstance(ag, int) and ag > 0 else ""
        stale = (f'<div class="pr-stale">⚠ DỮ LIỆU ĐÃ CŨ — cập nhật cuối: {esc(li)}{agtxt}. '
                 f'Hãy làm mới dữ liệu rồi chạy lại "báo cáo tiến độ".</div>')
    style = f"""<style>
.pr{{font-family:"Segoe UI",system-ui,-apple-system,sans-serif;color:{PAL['ink']};background:{PAL['deep']};
 padding:20px;border-radius:16px;line-height:1.5;font-size:14px}}
.pr h2{{font-size:18px;margin:22px 0 10px}}.pr h1{{font-size:21px;margin:0 0 4px}}
.pr .pr-sub{{color:{PAL['mut']};font-size:12.5px;margin-bottom:8px}}
.pr-kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:8px}}
.pr-kpi{{background:{PAL['card']};border:1px solid {PAL['line']};border-radius:13px;padding:14px 16px}}
.pr-kpi-v{{font-size:25px;font-weight:800}}.pr-kpi-l{{color:{PAL['mut']};font-size:12px;margin-top:3px}}
.pr-kpi-s{{font-size:11px;color:{PAL['teal']};margin-top:2px}}
.pr-card{{background:{PAL['card']};border:1px solid {PAL['line']};border-radius:13px;padding:14px 16px;margin-top:12px}}
.pr-card-h{{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:8px}}
.pr-mut{{color:{PAL['mut']};font-size:12px;font-weight:400}}
.pr-stack{{display:flex;height:14px;border-radius:7px;overflow:hidden;background:rgba(255,255,255,.06)}}
.pr-stack span{{display:block}}.pr-legend{{font-size:12px;color:{PAL['mut']};margin-top:6px}}
.pr-bar{{height:8px;border-radius:5px;background:rgba(255,255,255,.08);overflow:hidden}}.pr-bar span{{display:block;height:100%}}
.pr-t{{width:100%;border-collapse:collapse;margin-top:8px;font-size:12.5px}}
.pr-t th{{text-align:left;color:{PAL['mut']};font-weight:600;padding:5px 8px;border-bottom:1px solid {PAL['line']}}}
.pr-t td{{padding:5px 8px;border-bottom:1px solid rgba(255,255,255,.05);vertical-align:top}}
.pr-k{{font-family:ui-monospace,monospace;color:{PAL['teal']};white-space:nowrap}}
.pr-pill{{font-size:10.5px;padding:2px 8px;border-radius:999px;white-space:nowrap}}
.pr-done{{background:rgba(31,168,74,.22);color:#7ee2a0}}.pr-in_progress{{background:rgba(30,111,192,.25);color:#8fc6ff}}
.pr-todo{{background:rgba(159,180,214,.18);color:{PAL['mut']}}}
.pr-ul{{margin:6px 0 0;padding-left:18px}}.pr-ul li{{margin:3px 0;font-size:12.5px}}
.pr-warn{{background:rgba(244,123,32,.12);border-left:3px solid {PAL['orange']};border-radius:0 8px 8px 0;padding:8px 12px;margin-top:10px;font-size:12.5px;color:#f0ddc4}}
.pr-stale{{background:rgba(255,95,122,.14);border-left:3px solid {PAL['red']};border-radius:0 8px 8px 0;padding:9px 13px;margin:8px 0;font-size:13px;color:#ffc9d3;font-weight:600}}
.pr-grid2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}@media(max-width:680px){{.pr-grid2{{grid-template-columns:1fr}}}}
</style>"""
    return f"""{style}<div class="pr">
<h1>📊 Báo cáo tiến độ dự án</h1>
<div class="pr-sub">Vault: {esc(os.path.basename(vault.rstrip('/')))} · cập nhật {esc(gen)} (giờ UTC) · {m['total']} issue</div>
{stale}
{note}
<div class="pr-kpis">{cards}</div>
<h2>Tiến độ tổng thể</h2><div class="pr-card">{stacked(m['by_status_group'])}</div>
<h2>Sprint đang chạy</h2>{sprint_html}
<h2>Theo người phụ trách</h2><div class="pr-card">{assignee_html}</div>
<h2>Rủi ro & lỗ hổng</h2><div class="pr-grid2">{risk_html}</div>
</div>"""


def standalone(fragment):
    return ('<!doctype html><html lang="vi"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Báo cáo tiến độ</title></head><body style="margin:0;background:{PAL["deep"]}">'
            f'{fragment}</body></html>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", help="Đường dẫn vault (mặc định đọc config/factory-config.yaml)")
    ap.add_argument("--out", help="Thư mục xuất (mặc định reports/)")
    args = ap.parse_args()

    vault = args.vault
    smap = None
    cfg_path = os.path.join(REPO_ROOT, "config", "factory-config.yaml")
    if os.path.exists(cfg_path):
        cfg = open(cfg_path, encoding="utf-8").read()
        if not vault:
            mm = re.search(r"^\s*vault_path:\s*(.+)$", cfg, re.M)
            if mm:
                vault = mm.group(1).strip().strip('"').strip("'")
    if not vault:
        die("Không tìm thấy vault. Truyền --vault <path> hoặc đặt vault_path trong config/factory-config.yaml.")
    if not os.path.isabs(vault):
        vault = os.path.normpath(os.path.join(REPO_ROOT, vault))
    if not os.path.isdir(vault):
        die(f"Vault không tồn tại: {vault}")

    issues = load_issues(vault)
    if not issues:
        die(f"Vault chưa có note Jira nào (source: jira) tại {vault}. Hãy 'quét jira' trước.")

    today = datetime.now().strftime("%Y-%m-%d")
    m = compute(issues, smap, today)
    stale_after = 1
    if os.path.exists(cfg_path):
        sm = re.search(r"stale_after_days:\s*(\d+)", open(cfg_path, encoding="utf-8").read())
        if sm:
            stale_after = int(sm.group(1))
    m["freshness"] = vault_freshness(vault, stale_after)
    fragment = render_fragment(m, vault)

    out = args.out or os.path.join(REPO_ROOT, "reports")
    os.makedirs(out, exist_ok=True)
    day = datetime.now().strftime("%Y-%m-%d")
    json_p = os.path.join(out, f"progress-data-{day}.json")
    html_p = os.path.join(out, f"progress-report-{day}.html")
    latest_p = os.path.join(out, "progress-report-latest.html")
    open(json_p, "w", encoding="utf-8").write(json.dumps(m, ensure_ascii=False, indent=2))
    open(html_p, "w", encoding="utf-8").write(standalone(fragment))
    open(latest_p, "w", encoding="utf-8").write(standalone(fragment))

    print(f"Report tiến độ đã tạo từ {len(issues)} issue.")
    print(f"  - Dashboard (mở trình duyệt): {html_p}")
    print(f"  - Bản mới nhất: {latest_p}")
    print(f"  - Dữ liệu (cho UI Cowork inline): {json_p}")
    print(f"Tổng: {m['total']} issue · {m['pct_done']}% done · "
          f"{len(m['active_sprints'])} sprint active · log {human_seconds(m['time']['spent_s'])}/"
          f"{human_seconds(m['time']['estimate_s'])}")


if __name__ == "__main__":
    main()
