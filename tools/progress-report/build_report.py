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
import calendar
import glob
import html
import json
import math
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
                "project": i.get("project", "—"), "type": i.get("type", "issue"),
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

    # ── Năng lực giờ công (giờ chuẩn) + thời gian OT — THÁNG hiện tại: 5 ngày/tuần × 8 giờ/ngày ──
    try:
        ty, tmo = int(today[:4]), int(today[5:7])
    except Exception:  # noqa: BLE001
        ty, tmo = datetime.now().year, datetime.now().month
    working_days = sum(1 for d in range(1, calendar.monthrange(ty, tmo)[1] + 1)
                       if date(ty, tmo, d).weekday() < 5)
    std_person = working_days * 8 * 3600          # giờ công chuẩn / người (giây)
    for a in by_assignee:
        sp = a["time"]["spent_s"]
        a["std_seconds"] = std_person
        a["ot_seconds"] = max(0, sp - std_person)        # log vượt chuẩn = OT
        a["under_seconds"] = max(0, std_person - sp)      # log thiếu so với chuẩn
        a["pct_capacity"] = pct(sp, std_person)
    members = [a for a in by_assignee if a["assignee"] not in ("(chưa giao)", "—", "")]
    team_std = len(members) * std_person
    capacity = {
        "month": f"{tmo:02d}/{ty}", "working_days": working_days,
        "std_hours_person": working_days * 8, "std_seconds_person": std_person,
        "num_members": len(members), "team_std_seconds": team_std,
        "logged_seconds": tsum["spent_s"],
        "ot_seconds": max(0, tsum["spent_s"] - team_std),
        "under_seconds": max(0, team_std - tsum["spent_s"]),
        "pct_capacity": pct(tsum["spent_s"], team_std),
    }

    # ── Logtime theo LOẠI — chỉ Task/Sub-task/Bug thực sự log; Epic/Story/Request thường KHÔNG log ──
    LOG_TYPES = {"task", "sub-task", "subtask", "bug"}
    logged_by_type, est_by_type = {}, {}
    for i in issues:
        tt = i.get("type") or "issue"
        logged_by_type[tt] = logged_by_type.get(tt, 0) + int(i.get("time_spent_s") or 0)
        est_by_type[tt] = est_by_type.get(tt, 0) + int(i.get("time_estimate_s") or 0)
    work_no_log = [{"key": i.get("jira_key"), "summary": i.get("_summary", ""),
                    "type": i.get("type"), "assignee": i.get("assignee", "—")}
                   for i in issues
                   if (i.get("type") or "") in LOG_TYPES
                   and not int(i.get("time_spent_s") or 0) and issue_group(i, smap) != "done"]

    # Rủi ro
    overdue, no_assignee, no_est = [], [], []
    for i in issues:
        dd = str(i.get("duedate") or "")[:10]
        if dd and dd < today and issue_group(i, smap) != "done":
            overdue.append({"key": i.get("jira_key"), "summary": i.get("_summary", ""),
                            "assignee": i.get("assignee", "—"), "duedate": dd, "status": i.get("status", ""),
                            "project": i.get("project", "—")})
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
        "capacity": capacity, "logged_by_type": logged_by_type, "est_by_type": est_by_type,
        "log_types": sorted(LOG_TYPES), "work_no_log": work_no_log[:50],
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


def svg_donut(segments, size=132):
    """Donut chart inline SVG (không phụ thuộc JS/CDN). segments=[(label,value,color)]."""
    total = sum(v for _, v, _ in segments) or 1
    r = size / 2 - 13
    cx = cy = size / 2
    circ = 2 * math.pi * r
    off = 0.0
    arcs = []
    for _label, v, color in segments:
        dash = circ * (v / total)
        arcs.append(f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" stroke="{color}" stroke-width="15" '
                    f'stroke-dasharray="{dash:.2f} {circ - dash:.2f}" stroke-dashoffset="{-off:.2f}" '
                    f'transform="rotate(-90 {cx} {cy})"/>')
        off += dash
    legend = "".join(
        f'<div style="display:flex;align-items:center;gap:7px;font-size:12px;margin:3px 0;color:{PAL["mut"]}">'
        f'<span style="width:11px;height:11px;border-radius:3px;background:{c};display:inline-block"></span>'
        f'{esc(l)} <b style="color:{PAL["ink"]}">{v}</b></div>' for l, v, c in segments)
    return (f'<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">'
            f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{"".join(arcs)}'
            f'<text x="{cx}" y="{cy - 1}" text-anchor="middle" font-size="23" font-weight="800" fill="{PAL["ink"]}">{total}</text>'
            f'<text x="{cx}" y="{cy + 15}" text-anchor="middle" font-size="10" fill="{PAL["mut"]}">issue</text></svg>'
            f'<div>{legend}</div></div>')


def svg_bars(rows, color, maxn=8, w=360):
    """Bar chart ngang inline SVG. rows=[(label,value)] (đã sort giảm dần)."""
    rows = [r for r in rows if r[1]][:maxn]
    if not rows:
        return f'<div style="color:{PAL["mut"]};font-size:12px">(chưa có dữ liệu)</div>'
    mx = max(v for _, v in rows) or 1
    lbl_w, gap = 110, 26
    barmax = w - lbl_w - 40
    parts = []
    for i, (label, v) in enumerate(rows):
        bw = barmax * v / mx
        y = i * gap
        parts.append(
            f'<text x="0" y="{y + 14}" font-size="11.5" fill="{PAL["mut"]}">{esc(str(label))[:15]}</text>'
            f'<rect x="{lbl_w}" y="{y + 3}" width="{bw:.1f}" height="15" rx="4" fill="{color}"/>'
            f'<text x="{lbl_w + bw + 5:.0f}" y="{y + 15}" font-size="11" font-weight="700" fill="{PAL["ink"]}">{v}</text>')
    h = len(rows) * gap + 4
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(parts)}</svg>'


def render_fragment(m, vault):
    t = m["time"]
    cards = "".join([
        kpi("Tổng issue", m["total"], color="ink"),
        kpi("Hoàn thành", f'{m["pct_done"]}%', f'{m["by_status_group"]["done"]}/{m["total"]}', "green"),
        kpi("Ước tính", human_seconds(t["estimate_s"]), color="blue"),
        kpi("Đã log", human_seconds(t["spent_s"]), f'{t["pct_logged"]}% ước tính', "teal"),
        kpi("Còn lại", human_seconds(t["remaining_s"]), color="orange"),
        kpi("Sprint đang chạy", len(m["active_sprints"]), color="vio"),
        kpi("Giờ công chuẩn (nhóm)", human_seconds(m["capacity"]["team_std_seconds"]),
            f'{m["capacity"]["working_days"]} ngày làm việc · {m["capacity"]["num_members"]} thành viên', "blue"),
        kpi("Thời gian OT" if m["capacity"]["ot_seconds"] else "Thiếu so với chuẩn",
            human_seconds(m["capacity"]["ot_seconds"] or m["capacity"]["under_seconds"]),
            f'Đạt {m["capacity"]["pct_capacity"]}% giờ chuẩn',
            "red" if m["capacity"]["ot_seconds"] else "orange"),
    ])

    sprint_html = ""
    for s in m["active_sprints"]:
        rows = "".join(
            f'<tr class="pr-row" data-assignee="{esc(i["assignee"])}" data-status="{i["group"]}" '
            f'data-project="{esc(i["project"])}" data-type="{esc(i["type"])}">'
            f'<td class="pr-k">{esc(i["key"])}</td><td>{esc(i["summary"])[:70]}</td>'
            f'<td>{esc(i["assignee"])}</td>'
            f'<td><span class="pr-pill pr-{i["group"]}">{esc(i["status"])}</span></td>'
            f'<td>{human_seconds(i["spent_s"])} / {human_seconds(i["est_s"])}</td>'
            f'<td>{esc(i["story_points"])}</td></tr>' for i in s["issues"])
        sprint_html += (
            f'<div class="pr-card"><div class="pr-card-h"><b>🏃 {esc(s["name"])}</b>'
            f'<span class="pr-mut">{esc(s["end"]) and "đến " + esc(s["end"])} · {s["done"]}/{s["total"]} done · '
            f'log {human_seconds(s["time"]["spent_s"])}/{human_seconds(s["time"]["estimate_s"])}</span></div>'
            f'{bar(s["pct_done"], "green")}'
            f'<table class="pr-t"><thead><tr><th>Mã</th><th>Tóm tắt</th><th>Thành viên</th>'
            f'<th>Trạng thái</th><th>Đã log / Ước tính</th><th>Story Points</th></tr></thead><tbody>{rows}</tbody></table></div>')
    if not m["active_sprints"]:
        sprint_html = '<div class="pr-card pr-mut">Không có sprint đang chạy (active) — kiểm tra field Sprint trên Jira.</div>'

    def _ot_cell(a):
        if a.get("ot_seconds"):
            return f'<span style="color:{PAL["red"]}">+{human_seconds(a["ot_seconds"])}</span>'
        return f'<span class="pr-mut">−{human_seconds(a.get("under_seconds", 0))}</span>'
    arows = "".join(
        f'<tr class="pr-row" data-assignee="{esc(a["assignee"])}"><td>{esc(a["assignee"])}</td><td>{a["total"]}</td>'
        f'<td>{a["todo"]}</td><td>{a["in_progress"]}</td><td>{a["done"]}</td>'
        f'<td style="min-width:90px">{bar(a["pct_done"], "green")}</td>'
        f'<td>{human_seconds(a["time"]["spent_s"])} / {human_seconds(a["time"]["estimate_s"])}</td>'
        f'<td>{human_seconds(a.get("std_seconds", 0))}</td><td>{_ot_cell(a)}</td>'
        f'<td>{a.get("pct_capacity", 0)}%</td>'
        f'<td>{a["story_points"] or ""}</td></tr>' for a in m["by_assignee"])
    assignee_html = (
        f'<table class="pr-t"><thead><tr><th>Thành viên</th><th>Tổng</th><th>Chưa làm</th><th>Đang làm</th>'
        f'<th>Hoàn thành</th><th>% Hoàn thành</th><th>Đã log / Ước tính</th><th>Giờ chuẩn</th>'
        f'<th>OT / Thiếu</th><th>% Năng suất</th><th>Story Points</th></tr></thead><tbody>{arows}</tbody></table>')

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

    # By project (panel — chỉ hiện khi >1 project)
    proj_html = ""
    if len(m.get("by_project", [])) > 1:
        prows = "".join(
            f'<tr><td>{esc(p["project"])}</td><td>{p["total"]}</td><td>{p["done"]}</td>'
            f'<td style="min-width:90px">{bar(p["pct_done"], "teal")}</td>'
            f'<td>{human_seconds(p["time"]["spent_s"])}/{human_seconds(p["time"]["estimate_s"])}</td></tr>'
            for p in m["by_project"])
        proj_html = ('<table class="pr-t"><thead><tr><th>Dự án</th><th>Tổng</th><th>Hoàn thành</th>'
                     f'<th>% Hoàn thành</th><th>Đã log / Ước tính</th></tr></thead><tbody>{prows}</tbody></table>')

    # Log giờ theo loại + cảnh báo (Epic/User Story/Request không log; chỉ Task/Sub-task/Bug)
    lbt, ebt = m.get("logged_by_type", {}), m.get("est_by_type", {})
    _ltkeys = sorted(set(lbt) | set(ebt), key=lambda k: -lbt.get(k, 0))
    lt_rows = "".join(
        f'<tr><td>{esc(_type_label(k))}</td><td>{human_seconds(ebt.get(k, 0))}</td>'
        f'<td>{human_seconds(lbt.get(k, 0))}</td></tr>' for k in _ltkeys)
    n_nolog = len(m.get("work_no_log", []))
    logtype_html = (
        '<div class="pr-card"><div class="pr-card-h"><b>⏱ Log giờ theo loại</b>'
        '<span class="pr-mut">Epic / User Story / Request thường KHÔNG log giờ — chỉ Task / Sub-task / Bug</span></div>'
        f'<table class="pr-t"><thead><tr><th>Loại</th><th>Ước tính</th><th>Đã log</th></tr></thead><tbody>{lt_rows}</tbody></table>'
        f'<div class="pr-warn" style="margin-top:8px"><b>{n_nolog} Task / Sub-task</b> chưa làm xong nhưng '
        'chưa log giờ → nguy cơ thiếu dữ liệu nỗ lực thực tế.</div></div>')
    # Filter bar (người + trạng thái) — lọc tương tác trên bảng
    assignees = sorted({a["assignee"] for a in m["by_assignee"]})
    projects = sorted({p["project"] for p in m.get("by_project", [])})
    types = sorted(set(m.get("logged_by_type", {})) | set(m.get("by_type", {})))
    _opt = lambda v, lbl=None: f'<option value="{esc(v)}">{esc(lbl if lbl is not None else v)}</option>'
    proj_sel = (('<select id="kr-fp" onchange="krFilter()"><option value="">Tất cả dự án</option>'
                 + "".join(_opt(p) for p in projects) + '</select>') if projects else '')
    type_sel = ('<select id="kr-ft" onchange="krFilter()"><option value="">Mọi loại</option>'
                + "".join(_opt(tk, _type_label(tk)) for tk in types) + '</select>')
    filter_bar = (
        '<div class="pr-filter"><span>🔎 Lọc:</span>' + proj_sel +
        '<select id="kr-fa" onchange="krFilter()"><option value="">Tất cả thành viên</option>'
        + "".join(_opt(a) for a in assignees) + '</select>' + type_sel +
        '<select id="kr-fs" onchange="krFilter()"><option value="">Mọi trạng thái</option>'
        '<option value="todo">Chưa làm</option><option value="in_progress">Đang làm</option>'
        '<option value="done">Hoàn thành</option></select></div>')
    ai_anchor = ('<section class="pr-card pr-ai" id="kr-ai"><b style="color:#c9b8ff">🤖 Phân tích AI</b>'
                 '<div class="pr-mut" style="margin-top:6px">Khu vực này được Claude điền khi chạy báo cáo: '
                 'phân loại rủi ro theo mức · dự đoán nguy cơ trượt timeline mỗi sprint (kèm lý do) · giải pháp '
                 'cho từng rủi ro · đề xuất theo từng thành viên · tổng kết điều hành.</div></section>')
    krscript = ('<script>function krV(id){var e=document.getElementById(id);return e?e.value:"";}'
                'function krFilter(){var a=krV("kr-fa"),s=krV("kr-fs"),p=krV("kr-fp"),t=krV("kr-ft");'
                'document.querySelectorAll(".pr-row").forEach(function(r){var d=r.dataset;'
                'var ok=(!a||d.assignee===a)&&(!s||!d.status||d.status===s)'
                '&&(!p||!d.project||d.project===p)&&(!t||!d.type||d.type===t);'
                'r.style.display=ok?"":"none";});}</script>')

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
.pr-filter{{display:flex;gap:8px;align-items:center;margin:10px 0 4px;flex-wrap:wrap;font-size:12.5px;color:{PAL['mut']};position:sticky;top:0;z-index:5;background:{PAL['deep']};padding:8px 0}}
.pr-filter select{{background:{PAL['card']};color:{PAL['ink']};border:1px solid {PAL['line']};border-radius:8px;padding:5px 9px;font-size:12.5px}}
.pr-charts{{display:flex;gap:28px;flex-wrap:wrap;align-items:flex-start}}
.pr-t tbody tr:nth-child(even){{background:rgba(255,255,255,.025)}}
.pr-t tbody tr:hover{{background:rgba(45,212,191,.09)}}
.pr-ai{{border-left:3px solid {PAL['vio']};margin-top:12px}}
</style>"""
    proj_section = f'<h2>Theo dự án</h2><div class="pr-card">{proj_html}</div>' if proj_html else ''
    _bp = [p for p in m.get('by_project', []) if p.get('project') not in (None, '', '—')]
    _scope = f"{len(_bp)} dự án" if len(_bp) > 1 else (esc(_bp[0]['project']) if _bp else '—')
    # 📈 Biểu đồ (inline SVG — donut trạng thái + bar theo người/dự án)
    bsg = m["by_status_group"]
    donut = svg_donut([("Hoàn thành", bsg["done"], PAL["green"]),
                       ("Đang làm", bsg["in_progress"], PAL["blue"]),
                       ("Chưa làm", bsg["todo"], PAL["mut"])])
    asg_bars = svg_bars([(a["assignee"], a["total"]) for a in m["by_assignee"]
                         if a["assignee"] not in ("(chưa giao)", "—", "")], PAL["teal"])
    charts_inner = (f'<div><div class="pr-mut" style="margin-bottom:6px">Trạng thái</div>{donut}</div>'
                    f'<div><div class="pr-mut" style="margin-bottom:6px">Khối lượng theo người</div>{asg_bars}</div>')
    if len(_bp) > 1:
        charts_inner += ('<div><div class="pr-mut" style="margin-bottom:6px">Khối lượng theo dự án</div>'
                         + svg_bars([(p["project"], p["total"]) for p in _bp], PAL["vio"]) + '</div>')
    charts_html = f'<div class="pr-card pr-charts">{charts_inner}</div>'
    return f"""{style}<div class="pr">
<h1>📊 Báo cáo tiến độ dự án</h1>
<div class="pr-sub">{_scope} · Vault: {esc(os.path.basename(vault.rstrip('/')))} · cập nhật {esc(gen)} (giờ UTC) · {m['total']} issue</div>
{stale}
{note}
{filter_bar}
<div class="pr-kpis">{cards}</div>
{ai_anchor}
<h2>Tiến độ tổng thể</h2><div class="pr-card">{stacked(m['by_status_group'])}</div>
<h2>📈 Biểu đồ</h2>{charts_html}
{proj_section}
<h2>Sprint đang chạy</h2>{sprint_html}
<h2>Theo người phụ trách (giờ công &amp; OT)</h2><div class="pr-card">{assignee_html}</div>
<h2>Log giờ theo loại</h2>{logtype_html}
<h2>Rủi ro &amp; lỗ hổng</h2><div class="pr-grid2">{risk_html}</div>
{krscript}
</div>"""


def standalone(fragment):
    return ('<!doctype html><html lang="vi"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Báo cáo tiến độ</title></head><body style="margin:0;background:{PAL["deep"]}">'
            f'{fragment}</body></html>')


# ── Render EMAIL BODY (tĩnh, email-safe, responsive cho điện thoại — để GỬI MAIL) ──
EPAL = {"bg": "#eef1f6", "card": "#ffffff", "ink": "#0b1f44", "mut": "#6b7891",
        "green": "#1a9e63", "amber": "#b7791f", "red": "#c0392b", "vio": "#6b46c1",
        "orange": "#ef7d23", "chip": "#f4f7fb", "blue": "#0a4aa0", "blue2": "#1463c4",
        "cream": "#fff8ec", "creambd": "#ffe2b0", "line": "#e6eaf0"}


def _ecard(label, value, unit="", highlight=False):
    bg = "#fff6ec" if highlight else "#f7f9fc"
    bd = EPAL["orange"] if highlight else EPAL["line"]
    vc = EPAL["orange"] if highlight else EPAL["blue"]
    return (f'<td class="kc" width="33.33%" valign="top" style="padding:5px"><div style="background:{bg};'
            f'border:1px solid {bd};border-radius:12px;padding:14px 8px;text-align:center">'
            f'<div style="font-size:10.5px;font-weight:700;color:{EPAL["mut"]};text-transform:uppercase;'
            f'letter-spacing:.03em;line-height:1.3;min-height:26px">{esc(label)}</div>'
            f'<div style="font-size:30px;font-weight:800;color:{vc};margin:3px 0 0">{value}</div>'
            f'<div style="font-size:11.5px;color:{EPAL["mut"]}">{esc(unit)}</div></div></td>')


_TYPE_LABELS = {"epic": "Epic", "story": "User Story", "user_story": "User Story",
                "task": "Task", "sub-task": "Sub-task", "subtask": "Sub-task",
                "bug": "Bug", "request": "Request", "issue": "Issue"}


def _type_label(t):
    return _TYPE_LABELS.get((t or "issue").lower(), (t or "Issue").title())


def render_email_body(m, vault, banner_url=""):
    """HTML tĩnh, email-safe, responsive. Chừa khối AI giữa <!--KR-AI-START--> ... <!--KR-AI-END-->
    để Claude THAY bằng phân tích CHI TIẾT (rủi ro · dự đoán · đề xuất) trước khi gửi."""
    t, g = m["time"], m["by_status_group"]
    tot = max(m["total"], 1)
    risks = m["risks"]
    od = "".join(
        f'<li style="margin:3px 0"><b>{esc(x["key"])}</b> · {esc(x["summary"])[:60]} '
        f'<span style="color:{EPAL["red"]}">(quá hạn {esc(x["duedate"])}'
        + (f' · {esc(x["project"])}' if x.get("project") not in (None, "", "—") else "")
        + f')</span> — {esc(x["assignee"])}</li>'
        for x in risks["overdue"][:6])
    od = od or '<li style="margin:3px 0;color:#5b7a4f">Không có issue quá hạn 👍</li>'
    gen = m["generated_at"][:16].replace("T", " ")
    sp = lambda k: 100 * g[k] / tot
    # Phạm vi báo cáo = theo DỰ ÁN (lọc node rỗng 1 lần → dùng cho cả scope + tiering, nhất quán).
    bp = [p for p in m.get("by_project", []) if p.get("project") not in (None, "", "—")]
    scope = f"{len(bp)} dự án" if len(bp) > 1 else (esc(bp[0]["project"]) if bp else "—")
    banner_row = (f'<tr><td style="padding:0;line-height:0"><img src="{banner_url}" '
                  f'alt="Cập nhật tiến độ dự án mỗi ngày" width="600" style="display:block;width:100%;'
                  f'max-width:600px;height:auto;border:0"></td></tr>') if banner_url else ""
    # ── Năng suất & giờ công + lưu ý logtime theo loại ──
    cap = m.get("capacity", {})
    hs = human_seconds
    if cap.get("ot_seconds"):
        ot_txt = f'<span style="color:{EPAL["red"]}"><b>Thời gian OT (vượt giờ chuẩn): +{hs(cap["ot_seconds"])}</b></span>'
    else:
        ot_txt = f'<span style="color:{EPAL["amber"]}">Còn thiếu so với giờ chuẩn: {hs(cap.get("under_seconds", 0))}</span>'
    lbt = m.get("logged_by_type", {})
    log_rows = "".join(
        f'<tr><td style="padding:3px 0;font-size:13px;color:{EPAL["ink"]}">{esc(_type_label(k))}</td>'
        f'<td style="padding:3px 0;font-size:13px;color:#39465c;text-align:right">{hs(v)}</td></tr>'
        for k, v in sorted(lbt.items(), key=lambda kv: -kv[1]) if v) or \
        f'<tr><td style="font-size:13px;color:{EPAL["mut"]}">Chưa có dữ liệu log giờ.</td></tr>'
    n_nolog = len(m.get("work_no_log", []))
    cap_block = f'''<tr><td class="kpad" style="padding:8px 22px 2px">
      <div style="font-size:12px;color:{EPAL['mut']};text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">Năng suất &amp; giờ công — tháng {esc(cap.get('month', ''))}</div>
      <div style="font-size:13.5px;color:{EPAL['ink']};line-height:1.75">
        • Số ngày làm việc trong tháng: <b>{cap.get('working_days', 0)} ngày</b> (5 ngày mỗi tuần × 8 giờ mỗi ngày).<br>
        • Giờ công chuẩn mỗi thành viên: <b>{cap.get('std_hours_person', 0)} giờ</b> · cả nhóm ({cap.get('num_members', 0)} thành viên): <b>{hs(cap.get('team_std_seconds', 0))}</b>.<br>
        • Tổng thời gian đã log: <b>{hs(cap.get('logged_seconds', 0))}</b> → đạt <b>{cap.get('pct_capacity', 0)}%</b> giờ công chuẩn của cả nhóm.<br>
        • {ot_txt}.
      </div>
      <div style="background:#fff8ec;border:1px solid #ffe2b0;border-radius:10px;padding:11px 13px;margin-top:10px;font-size:12.5px;color:#7a5b16">
        ⚠️ <b>Lưu ý về log giờ theo loại:</b> Epic / User Story / Request thường <b>KHÔNG log giờ</b> — chỉ <b>Task / Sub-task</b> (và Bug) mới log giờ.
        Vì vậy giờ công ở trên chỉ phản ánh phần Task / Sub-task. Hiện có <b>{n_nolog} Task / Sub-task chưa làm xong nhưng chưa log giờ</b> — nguy cơ thiếu dữ liệu nỗ lực thực tế.
        <table role="presentation" width="100%" style="margin-top:7px;border-top:1px solid #ffe2b0">{log_rows}</table>
      </div></td></tr>'''
    # ── Phân tầng THEO DỰ ÁN (chỉ hiện khi quản lý nhiều dự án) — ngay trong BODY mail ──
    proj_block = ""
    if len(bp) > 1:
        od_by_proj = {}
        for x in risks["overdue"]:
            od_by_proj[x.get("project", "—")] = od_by_proj.get(x.get("project", "—"), 0) + 1
        prows = ""
        for p in sorted(bp, key=lambda z: -z["total"]):
            pt = p["time"]
            nod = od_by_proj.get(p["project"], 0)
            od_cell = (f'<span style="color:{EPAL["red"]};font-weight:700">{nod}</span>'
                       if nod else f'<span style="color:{EPAL["mut"]}">0</span>')
            prows += (
                f'<tr>'
                f'<td style="padding:7px 9px;font-size:13px;color:{EPAL["ink"]};font-weight:700;border-top:1px solid #eef1f6">{esc(p["project"])}</td>'
                f'<td style="padding:7px 9px;font-size:13px;color:#39465c;text-align:center;border-top:1px solid #eef1f6">{p["total"]}</td>'
                f'<td style="padding:7px 9px;font-size:13px;color:{EPAL["green"]};font-weight:700;text-align:center;border-top:1px solid #eef1f6">{p["pct_done"]}%</td>'
                f'<td style="padding:7px 9px;font-size:12.5px;color:#39465c;text-align:right;border-top:1px solid #eef1f6">{hs(pt["spent_s"])} / {hs(pt["estimate_s"])}</td>'
                f'<td style="padding:7px 9px;font-size:12.5px;color:{EPAL["orange"]};text-align:right;border-top:1px solid #eef1f6">{hs(pt["remaining_s"])}</td>'
                f'<td style="padding:7px 9px;font-size:13px;text-align:center;border-top:1px solid #eef1f6">{od_cell}</td>'
                f'</tr>')
        proj_block = f'''<tr><td class="kpad" style="padding:8px 22px 2px">
      <div style="font-size:12px;color:{EPAL['mut']};text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">Theo dự án ({len(bp)})</div>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e6eaf0;border-radius:10px;overflow:hidden">
        <tr style="background:{EPAL['chip']}">
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-transform:uppercase;letter-spacing:.03em">Dự án</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:center">Issue</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:center">% xong</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:right">Đã log / Ước tính</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:right">Còn lại</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:center">Quá hạn</td>
        </tr>{prows}
      </table>
      <div style="font-size:11.5px;color:{EPAL['mut']};margin-top:6px">Lọc &amp; drill-down chi tiết từng dự án có trong dashboard đính kèm.</div></td></tr>'''
    return f"""<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><meta charset="utf-8">
<style>@media only screen and (max-width:600px){{.kc{{display:block!important;width:100%!important;box-sizing:border-box}}.kpad{{padding:16px!important}}}}</style>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{EPAL['bg']};padding:16px 8px;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif">
<tr><td align="center"><table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:{EPAL['card']};border-radius:14px;overflow:hidden">
  {banner_row}
  <tr><td class="kpad" style="padding:18px 22px 2px">
    <span style="display:inline-block;background:{EPAL['cream']};border:1px solid {EPAL['creambd']};color:#b45309;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;padding:6px 13px;border-radius:999px">⏱️ Cập nhật tiến độ · {scope}</span></td></tr>
  <tr><td class="kpad" style="padding:10px 22px 0">
    <div style="font-size:15px;color:{EPAL['ink']};font-weight:700;font-style:italic">Kính gửi Anh/Chị,</div>
    <div style="font-size:13.5px;color:#33405a;line-height:1.7;margin-top:6px">Trợ lý <b>KORA AI</b> – FPT Telecom xin cập nhật <b>tiến độ dự án</b> ({scope}) tới <b>{esc(gen)}</b> (UTC) như sau:</div></td></tr>
  <tr><td class="kpad" style="padding:14px 17px 2px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
    {_ecard("Tổng số issue", m['total'], "issue")}{_ecard("Đã hoàn thành", g['done'], "issue")}{_ecard("Còn lại", m['total'] - g['done'], "issue", True)}
  </tr></table></td></tr>
  <tr><td class="kpad" style="padding:8px 22px">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e9edf3;border-radius:999px;overflow:hidden"><tr style="height:12px">
      <td width="{sp('done'):.0f}%" bgcolor="{EPAL['green']}"></td><td bgcolor="#e9edf3"></td></tr></table>
    <table role="presentation" width="100%" style="margin-top:7px"><tr>
      <td style="font-size:12.5px;color:{EPAL['mut']}">Tiến độ hoàn thành</td>
      <td style="font-size:12.5px;text-align:right;color:#39465c"><b style="color:{EPAL['green']}">{m['pct_done']}%</b> · còn lại {m['total'] - g['done']} issue · <span style="color:{EPAL['amber']}">đang làm {g['in_progress']}</span></td>
    </tr></table></td></tr>
  {proj_block}
  {cap_block}
  <tr><td class="kpad" style="padding:12px 22px 4px">
    <div style="background:{EPAL['cream']};border:1px solid {EPAL['creambd']};border-radius:12px;padding:14px 16px">
      <div style="font-size:13px;font-weight:800;color:#b45309;text-transform:uppercase;letter-spacing:.03em;margin-bottom:8px">⚠️ Lưu ý quan trọng</div>
      <ul style="margin:0;padding-left:18px;font-size:12.8px;color:#7a5b16;line-height:1.6">
        <li style="margin:3px 0"><b>Quá hạn ({len(risks['overdue'])}):</b></li>
        {od}
        <li style="margin:7px 0 3px"><b>Log giờ theo loại:</b> Epic / User Story / Request thường <b>KHÔNG log giờ</b> — chỉ Task / Sub-task / Bug. Hiện <b>{len(m.get('work_no_log', []))} Task/Sub-task chưa xong nhưng chưa log giờ</b>.</li>
      </ul></div></td></tr>
  <tr><td class="kpad" style="padding:12px 22px 4px">
    <div style="font-size:13px;font-weight:800;color:{EPAL['blue']};text-transform:uppercase;letter-spacing:.03em;margin-bottom:6px">🤖 Phân tích &amp; khuyến nghị (AI)</div>
    <!--KR-AI-START-->
    <div style="font-size:12.5px;color:{EPAL['mut']};line-height:1.6">(Claude điền phân tích chi tiết khi gửi: mức rủi ro · dự đoán trượt timeline + lý do · đề xuất từng bước · theo từng thành viên · tổng kết điều hành.)</div>
    <!--KR-AI-END--></td></tr>
  <tr><td class="kpad" style="padding:8px 22px 16px">
    <div style="font-size:13px;color:#33405a;line-height:1.7">Để xem chi tiết từng issue / sprint / thành viên (có bộ lọc), vui lòng mở <b>Dashboard đính kèm</b>. Mọi thông tin cần hỗ trợ, vui lòng liên hệ đầu mối bên dưới.</div>
    <div style="font-size:13.5px;color:{EPAL['ink']};font-weight:700;margin-top:10px">Trân trọng!</div></td></tr>
  <tr><td style="background:linear-gradient(135deg,#0b2a5e,#15428f);padding:16px 22px;text-align:center">
    <div style="color:#ffffff;font-size:13px;font-weight:700">KORA AI · Trợ lý tiến độ dự án — FPT Telecom</div>
    <div style="color:#a9c2ee;font-size:11.5px;margin-top:4px">Báo cáo tạo tự động mỗi ngày · Dữ liệu cập nhật {esc(gen)} (UTC)</div></td></tr>
</table></td></tr></table>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", help="Đường dẫn vault (mặc định đọc config/factory-config.yaml)")
    ap.add_argument("--out", help="Thư mục xuất (mặc định reports/)")
    ap.add_argument("--projects", default="", help="Lọc báo cáo theo project key, cách nhau phẩy "
                    "(vd PROJ1,PROJ2). Rỗng = tất cả project trong vault.")
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
    if args.projects:
        keys = {k.strip() for k in args.projects.split(",") if k.strip()}
        issues = [i for i in issues if (i.get("project") or "") in keys]
        if not issues:
            die(f"Không có note Jira cho project {sorted(keys)} trong vault {vault}. Hãy quét project đó trước.")
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
    banner_url = ""
    if os.path.exists(cfg_path):
        bm = re.search(r'banner_url:\s*"([^"]*)"', open(cfg_path, encoding="utf-8").read())
        if bm:
            banner_url = bm.group(1).strip()
    if not banner_url:  # mặc định → email LUÔN có banner (asset trên nhánh main)
        banner_url = "https://raw.githubusercontent.com/isc-fkit/Kora-Framework/main/assets/banner-daily-report.png"
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

    # Email body (tĩnh, mobile) để gửi mail — Claude điền khối AI giữa <!--KR-AI-START/END-->
    ebody = render_email_body(m, vault, banner_url)
    ebody_p = os.path.join(out, f"email-body-{day}.html")
    ebody_latest = os.path.join(out, "email-body-latest.html")
    open(ebody_p, "w", encoding="utf-8").write(ebody)
    open(ebody_latest, "w", encoding="utf-8").write(ebody)

    print(f"Report tiến độ đã tạo từ {len(issues)} issue.")
    print(f"  - Email body (mobile, để gửi mail): {ebody_latest}")
    print(f"  - Dashboard (mở trình duyệt): {html_p}")
    print(f"  - Bản mới nhất: {latest_p}")
    print(f"  - Dữ liệu (cho UI Cowork inline): {json_p}")
    print(f"Tổng: {m['total']} issue · {m['pct_done']}% done · "
          f"{len(m['active_sprints'])} sprint active · log {human_seconds(m['time']['spent_s'])}/"
          f"{human_seconds(m['time']['estimate_s'])}")


if __name__ == "__main__":
    main()
