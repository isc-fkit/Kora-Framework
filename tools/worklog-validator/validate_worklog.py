#!/usr/bin/env python3
"""
validate_worklog.py — KIỂM TRA tính hợp lệ thời gian (start/due/est) của task "Normal" trên
Jira đã quét về vault, và GỢI Ý lịch tạo task mới. CHỈ dùng thư viện chuẩn (không pyyaml).

Quy tắc nghiệp vụ (suy từ yêu cầu user):
  • Ràng buộc áp cho issue type Task / Sub-task có field Type = Normal (OT/Effort KHÔNG bị cap).
  • Mỗi NGÀY LÀM VIỆC (T2–T6) một người chỉ logwork tối đa cap=8h. T7/CN không log.
  • Chỉ được log trong [startTime, dueTime) — dueTime là biên LOẠI TRỪ.
  • dueTime tối thiểu = (ngày-làm-việc cuối cùng cần để log est ở 8h/ngày) + 1 ngày lịch.
      vd: start 01/06 est 8h → due 02/06; start 02/06 est 16h → due 04/06; xong T6 → due T7;
          tràn T6→T2 (2 ngày làm việc) → due thứ Ba (T7/CN ở giữa bị bỏ qua).

Chế độ:
  --validate --month YYYY-MM [--vault PATH] [--project KEYS] [--assignee NAMES] [--cap 8]
  --plan --new-tasks <json> --anchor YYYY-MM-DD --assignee NAME [--month YYYY-MM] [--vault PATH]
  --self-test            # chạy các case ví dụ của user, in PASS/FAIL (không cần vault)

Xuất: reports/worklog-check-<month>.json, reports/worklog-check-latest.html,
      reports/worklog-timeline-<month>.svg  (SVG để render inline qua show_widget)
"""
import argparse
import calendar
import html as _html
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta

CAP_DEFAULT = 8
TASK_TYPES = {"task", "sub-task", "subtask", "sub_task"}

PAL = {
    "ink": "#0f172a", "mut": "#64748b", "line": "#e2e8f0", "head": "#f8fafc",
    "weekend": "#eef2f7", "ok": "#10b981", "err": "#ef4444", "warn": "#f59e0b",
    "new": "#6366f1", "load0": "#f1f5f9", "load_ok": "#bbf7d0", "load_full": "#fcd34d",
    "load_over": "#fca5a5", "okbar": "#34d399",
}

SEVERITY = {  # code → (severity, nhãn tiếng Việt)
    "WINDOW_TOO_SMALL": ("error", "dueTime quá sớm — không đủ ngày log est"),
    "INVALID_WINDOW": ("error", "dueTime ≤ startTime"),
    "DAY_OVERLOAD": ("error", "Quá tải: không xếp đủ giờ ≤8h/ngày"),
    "OVER_CAPACITY": ("error", "Quá năng lực tháng của người này"),
    "MISSING_START": ("warn", "Thiếu Start date"),
    "MISSING_DUE": ("warn", "Thiếu dueTime"),
    "MISSING_EST": ("warn", "Thiếu estimate"),
    "WEEKEND_START": ("warn", "Start rơi vào T7/CN"),
    "DUE_SUGGEST": ("info", "dueTime rộng hơn mức tối thiểu"),
}


# ───────────────────────── ngày & ngày-làm-việc ─────────────────────────
def parse_date(s):
    if isinstance(s, date):
        return s
    if not s:
        return None
    s = str(s)[:10]
    try:
        return date(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except (ValueError, IndexError):
        return None


def working_days_between(d1, d2):
    """Số NGÀY LÀM VIỆC (T2–T6) trong [d1, d2) — biên cuối LOẠI TRỪ. Cùng 1 ngày làm việc → 1.
    (Khớp tools/progress-report/build_report.py:working_days_between.)"""
    a, b = parse_date(d1), parse_date(d2)
    if not a or not b:
        return 0
    if b < a:
        a, b = b, a
    n, cur = 0, a
    while cur < b:
        if cur.weekday() < 5:
            n += 1
        cur += timedelta(days=1)
    if n == 0 and a.weekday() < 5:
        n = 1
    return n


def minimal_due(start, est_h, cap=CAP_DEFAULT):
    """dueTime tối thiểu = ngày-làm-việc cuối + 1 ngày lịch (đủ chứa est ở cap h/ngày, bỏ T7/CN)."""
    start = parse_date(start)
    if not start or not est_h or est_h <= 0:
        return None
    days_needed = max(1, math.ceil(round(est_h / cap, 6)))
    count, last, cur = 0, start, start
    while count < days_needed:
        if cur.weekday() < 5:
            count += 1
            last = cur
        cur += timedelta(days=1)
    return last + timedelta(days=1)


def month_bounds(month):
    y, m = int(month[:4]), int(month[5:7])
    last = calendar.monthrange(y, m)[1]
    return date(y, m, 1), date(y, m, last)


def month_working_days(month):
    ms, me = month_bounds(month)
    out, cur = [], ms
    while cur <= me:
        if cur.weekday() < 5:
            out.append(cur)
        cur += timedelta(days=1)
    return out


def human_h(h):
    if h is None:
        return "—"
    h = round(float(h), 2)
    return (f"{int(h)}h" if abs(h - int(h)) < 1e-9 else f"{h:g}h")


# ───────────────────────── đọc vault ─────────────────────────
def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = {}
    for line in text[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if v == "":
            fm[k] = ""
            continue
        try:
            fm[k] = int(v)
        except ValueError:
            try:
                fm[k] = float(v)
            except ValueError:
                fm[k] = v
    return fm


def load_issues(vault):
    out = []
    for root, _dirs, files in os.walk(vault):
        if "_system" in root.split(os.sep):
            continue
        for fn in files:
            if not fn.endswith(".md"):
                continue
            try:
                with open(os.path.join(root, fn), encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                continue
            fm = parse_frontmatter(text)
            if str(fm.get("source", "")).lower() == "jira":
                fm["_file"] = os.path.join(root, fn)
                out.append(fm)
    return out


def cfg_vault(data_root):
    cfg = os.path.join(data_root, "config", "factory-config.yaml")
    try:
        with open(cfg, encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"\s*vault_path:\s*(.+)", line)
                if m:
                    v = m.group(1).strip().strip('"').strip("'")
                    if v and v != "TODO":
                        return v
    except OSError:
        pass
    return None


def resolve_vault(vault_arg, data_root):
    v = vault_arg or cfg_vault(data_root) or os.getenv("OBSIDIAN_VAULT")
    if not v:
        return None
    return v if os.path.isabs(v) else os.path.join(data_root, v)


# ───────────────────────── dựng task record ─────────────────────────
def is_normal_task(fm):
    """Task/Sub-task có work_type Normal (thiếu work_type → coi như Normal, đánh dấu assumed)."""
    t = str(fm.get("type", "")).strip().lower()
    if t not in TASK_TYPES:
        return False, False
    wt = str(fm.get("work_type", "")).strip().lower()
    if wt == "":
        return True, True          # normal (assumed)
    return wt == "normal", False   # normal nếu đúng Normal


def build_tasks(issues, cap):
    tasks = []
    for fm in issues:
        norm, assumed = is_normal_task(fm)
        t = str(fm.get("type", "")).strip().lower()
        est_s = fm.get("time_estimate_s")
        est_h = round(est_s / 3600, 2) if isinstance(est_s, (int, float)) and est_s > 0 else None
        rec = {
            "key": fm.get("jira_key") or os.path.basename(fm.get("_file", ""))[:24],
            "summary": fm.get("_summary") or "",
            "assignee": (str(fm.get("assignee")).strip() or "—") if fm.get("assignee") else "—",
            "type": t, "work_type": fm.get("work_type") or ("Normal" if assumed else ""),
            "work_type_assumed": assumed,
            "project": fm.get("project") or "—",
            "start": parse_date(fm.get("startdate")),
            "due": parse_date(fm.get("duedate")),
            "created": parse_date(fm.get("created")),
            "updated": parse_date(fm.get("updated")),
            "est_h": est_h,
            "is_normal": norm,
            "spent_h": round(fm.get("time_spent_s", 0) / 3600, 2) if isinstance(fm.get("time_spent_s"), (int, float)) else 0,
            "findings": [],
        }
        tasks.append(rec)
    return tasks


def in_month(t, ms, me):
    s, d = t["start"], t["due"]
    if s and ms <= s <= me:
        return True
    if d and ms <= d <= me:
        return True
    if s and d and s <= me and d > ms:
        return True
    if (not s or not d):  # task thiếu mốc → bám theo created/updated trong tháng
        for k in ("created", "updated"):
            if t[k] and ms <= t[k] <= me:
                return True
    return False


def add_finding(t, code, **extra):
    sev, label = SEVERITY[code]
    f = {"code": code, "severity": sev, "label": label}
    f.update(extra)
    t["findings"].append(f)
    return f


# ───────────────────────── kiểm tra ─────────────────────────
def validate_window(t, cap):
    """Check riêng từng task: thiếu mốc, window đủ rộng, due gợi ý, start cuối tuần."""
    if not t["is_normal"]:
        return
    if t["est_h"] is None:
        add_finding(t, "MISSING_EST")
    if t["start"] is None:
        add_finding(t, "MISSING_START")
    if t["due"] is None:
        add_finding(t, "MISSING_DUE")
    if t["start"] and t["start"].weekday() >= 5:
        add_finding(t, "WEEKEND_START")
    if t["start"] and t["due"]:
        if t["due"] <= t["start"]:
            add_finding(t, "INVALID_WINDOW")
        elif t["est_h"]:
            cap_h = working_days_between(t["start"], t["due"]) * cap
            sug = minimal_due(t["start"], t["est_h"], cap)
            t["suggested_due"] = sug
            if cap_h + 1e-9 < t["est_h"]:
                add_finding(t, "WINDOW_TOO_SMALL", need_h=t["est_h"], window_h=cap_h,
                            suggested_due=sug.isoformat() if sug else None)
            elif sug and t["due"] > sug:
                add_finding(t, "DUE_SUGGEST", suggested_due=sug.isoformat())


def feasible(person_tasks, cap):
    """EDF water-fill các task có đủ start/due/est của MỘT người. → (loads{date:h}, unplaced{key:h})."""
    loads, unplaced = {}, {}
    usable = [t for t in person_tasks if t["start"] and t["due"] and t["est_h"] and t["due"] > t["start"]]
    for t in sorted(usable, key=lambda x: (x["due"], x["start"])):
        remaining, cur = t["est_h"], t["start"]
        while remaining > 1e-9 and cur < t["due"]:
            if cur.weekday() < 5:
                free = cap - loads.get(cur, 0)
                if free > 1e-9:
                    take = min(free, remaining)
                    loads[cur] = loads.get(cur, 0) + take
                    remaining -= take
            cur += timedelta(days=1)
        if remaining > 1e-9:
            unplaced[t["key"]] = round(remaining, 2)
    return loads, unplaced


def validate(tasks, month, cap):
    ms, me = month_bounds(month)
    scope = [t for t in tasks if (t["is_normal"] or not t["is_normal"]) and in_month(t, ms, me)]
    normal = [t for t in scope if t["is_normal"]]
    other = [t for t in scope if not t["is_normal"]]   # OT / Effort → liệt kê riêng
    for t in normal:
        validate_window(t, cap)

    # Theo người: năng lực tháng + khả thi xếp lịch
    wd_month = len(month_working_days(month))
    std_h = wd_month * cap
    people = {}
    for t in normal:
        people.setdefault(t["assignee"], []).append(t)
    person_reports, loads_all = [], {}
    for who, plist in sorted(people.items()):
        sum_est = round(sum(t["est_h"] for t in plist if t["est_h"]), 2)
        pr = {"assignee": who, "tasks": len(plist), "sum_est_h": sum_est,
              "std_h": std_h, "working_days": wd_month, "over_capacity": sum_est > std_h + 1e-9,
              "findings": []}
        if pr["over_capacity"]:
            pr["findings"].append({"code": "OVER_CAPACITY", "severity": "error",
                                   "label": SEVERITY["OVER_CAPACITY"][1],
                                   "sum_est_h": sum_est, "std_h": std_h})
        loads, unplaced = feasible(plist, cap)
        loads_all[who] = loads
        if unplaced:
            pr["findings"].append({"code": "DAY_OVERLOAD", "severity": "error",
                                   "label": SEVERITY["DAY_OVERLOAD"][1], "unplaced": unplaced})
            for t in plist:
                if t["key"] in unplaced:
                    add_finding(t, "DAY_OVERLOAD", unplaced_h=unplaced[t["key"]])
        pr["overloaded_days"] = sorted(d.isoformat() for d, h in loads.items()
                                       if h >= cap - 1e-9 and unplaced)
        person_reports.append(pr)
    return {"month": month, "cap": cap, "month_start": ms.isoformat(), "month_end": me.isoformat(),
            "working_days_month": wd_month, "std_h_person": std_h,
            "normal": normal, "other": other, "people": person_reports, "loads": loads_all}


# ───────────────────────── gợi ý task mới (plan) ─────────────────────────
def plan_new_tasks(new_tasks, anchor, assignee, existing_normal, cap, horizon_days=120):
    """Water-fill task mới vào ngày trống (≤cap/ngày) của 1 người, từ anchor. → list gợi ý + loads."""
    anchor = parse_date(anchor)
    base_loads, _ = feasible([t for t in existing_normal if t["assignee"] == assignee], cap)
    loads = dict(base_loads)
    suggestions = []
    for nt in new_tasks:
        name, est = nt.get("name", "(task)"), float(nt.get("est_h") or 0)
        if est <= 0:
            suggestions.append({"name": name, "est_h": est, "error": "est ≤ 0"})
            continue
        remaining, cur, used = est, anchor, []
        guard = 0
        while remaining > 1e-9 and guard < horizon_days * 2:
            if cur.weekday() < 5:
                free = cap - loads.get(cur, 0)
                if free > 1e-9:
                    take = min(free, remaining)
                    loads[cur] = loads.get(cur, 0) + take
                    remaining -= take
                    used.append(cur)
            cur += timedelta(days=1)
            guard += 1
        if not used:
            suggestions.append({"name": name, "est_h": est, "error": "không còn năng lực trong tầm 120 ngày"})
            continue
        start = used[0]
        due = used[-1] + timedelta(days=1)
        spill = used[-1].month != anchor.month or used[-1].year != anchor.year
        suggestions.append({"name": name, "est_h": est, "assignee": assignee,
                            "start": start.isoformat(), "due": due.isoformat(),
                            "days": len(used), "spill_next_month": spill})
    return suggestions, loads


# ───────────────────────── render SVG timeline ─────────────────────────
def _task_color(t):
    codes = {f["code"] for f in t.get("findings", [])}
    if codes & {"WINDOW_TOO_SMALL", "INVALID_WINDOW", "DAY_OVERLOAD"}:
        return PAL["err"]
    if codes & {"WEEKEND_START", "MISSING_START", "MISSING_DUE", "MISSING_EST"}:
        return PAL["warn"]
    if "DUE_SUGGEST" in codes:
        return PAL["warn"]
    return PAL["ok"]


def render_timeline_svg(report, suggestions=None, sug_assignee=None):
    """Gantt theo ngày trong tháng + dải tải/ngày/người. Trả chuỗi <svg> inline (no JS/CDN)."""
    month = report["month"]
    ms, me = month_bounds(month)
    days = [ms + timedelta(days=i) for i in range((me - ms).days + 1)]
    cap = report["cap"]
    col_w, lbl_w, head_h, row_h = 26, 210, 40, 24
    width = lbl_w + col_w * len(days) + 18

    # gom theo người: task normal + (nếu có) task gợi ý
    by_person = {}
    for t in report["normal"]:
        by_person.setdefault(t["assignee"], {"tasks": [], "sug": []})["tasks"].append(t)
    sug_rows = []
    if suggestions:
        for s in suggestions:
            if s.get("error"):
                continue
            by_person.setdefault(sug_assignee or s.get("assignee", "—"),
                                 {"tasks": [], "sug": []})["sug"].append(s)

    def day_x(d):
        return lbl_w + days.index(d) * col_w if d in days else None

    def clip_x(d, default_idx):
        if d <= ms:
            return lbl_w
        if d > me:
            return lbl_w + len(days) * col_w
        return lbl_w + days.index(d) * col_w

    parts = []
    y = head_h
    # header: cột ngày + tô xám cuối tuần
    for i, d in enumerate(days):
        x = lbl_w + i * col_w
        if d.weekday() >= 5:
            parts.append(f'<rect x="{x}" y="0" width="{col_w}" height="100%" fill="{PAL["weekend"]}"/>')
    for i, d in enumerate(days):
        x = lbl_w + i * col_w
        wd = "T2 T3 T4 T5 T6 T7 CN".split()[d.weekday()]
        parts.append(f'<text x="{x + col_w/2:.0f}" y="16" text-anchor="middle" font-size="9" fill="{PAL["mut"]}">{wd}</text>')
        parts.append(f'<text x="{x + col_w/2:.0f}" y="30" text-anchor="middle" font-size="11" font-weight="700" fill="{PAL["ink"]}">{d.day}</text>')

    def section(label):
        nonlocal y
        parts.append(f'<rect x="0" y="{y}" width="{width}" height="{row_h}" fill="{PAL["head"]}"/>')
        parts.append(f'<text x="8" y="{y + 16}" font-size="12" font-weight="800" fill="{PAL["ink"]}">{_esc(label)}</text>')
        y += row_h

    for who, grp in sorted(by_person.items()):
        loads = report["loads"].get(who, {})
        section(f"👤 {who}")
        # task bars
        for t in grp["tasks"]:
            parts.append(f'<text x="8" y="{y + 16}" font-size="11" fill="{PAL["ink"]}">{_esc((t["key"] or "")[:14])}</text>')
            parts.append(f'<text x="120" y="{y + 16}" font-size="9.5" fill="{PAL["mut"]}">{_esc(human_h(t["est_h"]))}</text>')
            if t["start"] and t["due"] and t["due"] > t["start"]:
                x0 = clip_x(t["start"], 0)
                x1 = clip_x(t["due"], len(days))
                bw = max(col_w - 4, x1 - x0 - 2)
                parts.append(f'<rect x="{x0+1:.0f}" y="{y+3}" width="{bw:.0f}" height="{row_h-7}" rx="4" '
                             f'fill="{_task_color(t)}" opacity="0.88"/>')
            elif t["start"] and t["due"]:   # due ≤ start: vẽ ô đỏ tại ngày start + nhãn
                x0 = clip_x(t["start"], 0)
                parts.append(f'<rect x="{x0+1:.0f}" y="{y+3}" width="{col_w-4}" height="{row_h-7}" rx="4" '
                             f'fill="{PAL["err"]}" opacity="0.5" stroke="{PAL["err"]}" stroke-dasharray="3 2"/>')
                parts.append(f'<text x="{x0+col_w+3:.0f}" y="{y+16}" font-size="10" fill="{PAL["err"]}">⚠ dueTime ≤ startTime</text>')
            else:
                parts.append(f'<text x="{lbl_w+4}" y="{y+16}" font-size="10" fill="{PAL["err"]}">⚠ thiếu mốc start/due</text>')
            y += row_h
        # suggested bars (viền đứt)
        for s in grp["sug"]:
            parts.append(f'<text x="8" y="{y + 16}" font-size="11" fill="{PAL["new"]}">＋ {_esc(s["name"][:13])}</text>')
            parts.append(f'<text x="120" y="{y + 16}" font-size="9.5" fill="{PAL["mut"]}">{_esc(human_h(s["est_h"]))}</text>')
            sd, dd = parse_date(s["start"]), parse_date(s["due"])
            if sd and dd:
                x0, x1 = clip_x(sd, 0), clip_x(dd, len(days))
                bw = max(col_w - 4, x1 - x0 - 2)
                parts.append(f'<rect x="{x0+1:.0f}" y="{y+3}" width="{bw:.0f}" height="{row_h-7}" rx="4" '
                             f'fill="none" stroke="{PAL["new"]}" stroke-width="2" stroke-dasharray="4 3"/>')
            y += row_h
        # dải tải/ngày
        parts.append(f'<text x="8" y="{y + 15}" font-size="10" font-weight="700" fill="{PAL["mut"]}">tải/ngày (h)</text>')
        for i, d in enumerate(days):
            x = lbl_w + i * col_w
            h = round(loads.get(d, 0), 1)
            if d.weekday() >= 5:
                col = PAL["weekend"]
            elif h <= 0:
                col = PAL["load0"]
            elif h > cap + 1e-9:
                col = PAL["load_over"]
            elif h >= cap - 1e-9:
                col = PAL["load_full"]
            else:
                col = PAL["load_ok"]
            parts.append(f'<rect x="{x+1}" y="{y+1}" width="{col_w-2}" height="{row_h-3}" rx="3" fill="{col}"/>')
            if h > 0:
                parts.append(f'<text x="{x+col_w/2:.0f}" y="{y+15}" text-anchor="middle" font-size="9" '
                             f'fill="{PAL["ink"]}">{int(h) if abs(h-int(h))<1e-9 else h}</text>')
        y += row_h + 6

    total_h = y + 6
    svg = (f'<svg width="{width}" height="{total_h}" viewBox="0 0 {width} {total_h}" '
           f'xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Segoe UI,Roboto,sans-serif">'
           f'<rect width="{width}" height="{total_h}" fill="#ffffff"/>'
           + "".join(parts) + '</svg>')
    return svg


def _esc(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


# ───────────────────────── render HTML dashboard ─────────────────────────
def render_html(report, svg, suggestions=None):
    month = report["month"]
    rows_err = []
    for t in report["normal"]:
        if not t["findings"]:
            continue
        for f in t["findings"]:
            extra = ""
            if f["code"] == "WINDOW_TOO_SMALL":
                extra = f'cần {human_h(f.get("need_h"))}, window chỉ {human_h(f.get("window_h"))} → due gợi ý <b>{f.get("suggested_due")}</b>'
            elif f["code"] == "DUE_SUGGEST":
                extra = f'có thể thu hẹp due về <b>{f.get("suggested_due")}</b>'
            elif f["code"] == "DAY_OVERLOAD":
                extra = f'thiếu chỗ xếp {human_h(f.get("unplaced_h"))}'
            color = {"error": PAL["err"], "warn": PAL["warn"], "info": PAL["mut"]}[f["severity"]]
            rows_err.append(
                f'<tr><td><b>{_esc(t["key"])}</b></td><td>{_esc(t["assignee"])}</td>'
                f'<td>{_esc(t["start"].isoformat() if t["start"] else "—")}</td>'
                f'<td>{_esc(t["due"].isoformat() if t["due"] else "—")}</td>'
                f'<td>{_esc(human_h(t["est_h"]))}</td>'
                f'<td style="color:{color};font-weight:600">{_esc(f["label"])}</td><td>{extra}</td></tr>')
    if not rows_err:
        rows_err.append('<tr><td colspan="7" style="color:#10b981;font-weight:600">✓ Không phát hiện lỗi window/quá tải.</td></tr>')

    rows_people = []
    for p in report["people"]:
        codes = ", ".join(f["label"] for f in p["findings"]) or "—"
        col = PAL["err"] if p["findings"] else PAL["ok"]
        rows_people.append(
            f'<tr><td><b>{_esc(p["assignee"])}</b></td><td>{p["tasks"]}</td>'
            f'<td>{human_h(p["sum_est_h"])}</td><td>{human_h(p["std_h"])} ({p["working_days"]} ngày)</td>'
            f'<td style="color:{col};font-weight:600">{_esc(codes)}</td></tr>')

    rows_other = []
    for t in report["other"]:
        rows_other.append(
            f'<tr><td>{_esc(t["key"])}</td><td>{_esc(t["assignee"])}</td>'
            f'<td>{_esc(t["work_type"])}</td><td>{_esc(human_h(t["est_h"]))}</td></tr>')
    other_block = ""
    if rows_other:
        other_block = (f'<h3>Task OT / Effort (ngoài cap 8h/ngày — tham khảo)</h3>'
                       f'<table><tr><th>Key</th><th>Người</th><th>Type</th><th>Est</th></tr>{"".join(rows_other)}</table>')

    sug_block = ""
    if suggestions:
        srows = []
        for s in suggestions:
            if s.get("error"):
                srows.append(f'<tr><td>{_esc(s["name"])}</td><td>{human_h(s["est_h"])}</td>'
                             f'<td colspan="3" style="color:{PAL["err"]}">{_esc(s["error"])}</td></tr>')
            else:
                spill = ' <span style="color:#f59e0b">(tràn tháng sau)</span>' if s.get("spill_next_month") else ""
                srows.append(f'<tr><td><b>{_esc(s["name"])}</b></td><td>{human_h(s["est_h"])}</td>'
                             f'<td>{_esc(s["start"])}</td><td>{_esc(s["due"])}{spill}</td><td>{s["days"]} ngày</td></tr>')
        sug_block = (f'<h3>Gợi ý lịch task mới</h3>'
                     f'<table><tr><th>Tên</th><th>Est</th><th>Start</th><th>Due</th><th>Ngày làm việc</th></tr>'
                     f'{"".join(srows)}</table>')

    n_err = sum(1 for t in report["normal"] for f in t["findings"] if f["severity"] == "error")
    n_over = sum(1 for p in report["people"] if p["findings"])
    css = ("body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#0f172a;margin:18px;background:#fff}"
           "table{border-collapse:collapse;width:100%;margin:8px 0 20px;font-size:13px}"
           "th,td{border:1px solid #e2e8f0;padding:6px 9px;text-align:left}th{background:#f8fafc}"
           "h2{margin:6px 0}h3{margin:18px 0 4px}.kpi{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;"
           "border-radius:10px;padding:8px 14px;margin:4px 8px 12px 0}.kpi b{font-size:20px;display:block}"
           ".tl{overflow-x:auto;border:1px solid #e2e8f0;border-radius:10px;padding:6px}")
    return (f'<!doctype html><meta charset="utf-8"><title>Worklog check {month}</title><style>{css}</style>'
            f'<h2>🕗 Kiểm tra worklog/thời gian task — {month}</h2>'
            f'<div class="kpi">Ngày làm việc<b>{report["working_days_month"]}</b>cap {report["cap"]}h/ngày</div>'
            f'<div class="kpi">Task Normal<b>{len(report["normal"])}</b>trong phạm vi tháng</div>'
            f'<div class="kpi" style="border-color:#fca5a5">Lỗi window<b style="color:#ef4444">{n_err}</b>cần sửa</div>'
            f'<div class="kpi" style="border-color:#fca5a5">Người quá tải<b style="color:#ef4444">{n_over}</b></div>'
            f'<h3>Biểu đồ calendar timeline</h3><div class="tl">{svg}</div>'
            f'<h3>Chi tiết lỗi theo task</h3>'
            f'<table><tr><th>Key</th><th>Người</th><th>Start</th><th>Due</th><th>Est</th><th>Lỗi</th><th>Ghi chú</th></tr>'
            f'{"".join(rows_err)}</table>'
            f'<h3>Năng lực theo người</h3>'
            f'<table><tr><th>Người</th><th>#Task</th><th>Σ Est</th><th>Năng lực tháng</th><th>Cảnh báo</th></tr>'
            f'{"".join(rows_people)}</table>'
            f'{sug_block}{other_block}'
            f'<p style="color:#94a3b8;font-size:11px">Sinh bởi validate_worklog.py — dueTime là biên loại trừ; bỏ T7/CN.</p>')


# ───────────────────────── ghi output ─────────────────────────
def serialize_task(t):
    return {k: (v.isoformat() if isinstance(v, date) else v)
            for k, v in t.items() if k not in ("_file",)}


def write_outputs(report, out_dir, svg, suggestions=None):
    os.makedirs(out_dir, exist_ok=True)
    month = report["month"]
    data = {
        "month": month, "cap": report["cap"], "working_days_month": report["working_days_month"],
        "std_h_person": report["std_h_person"],
        "normal": [serialize_task(t) for t in report["normal"]],
        "other": [serialize_task(t) for t in report["other"]],
        "people": report["people"],
        "loads": {who: {d.isoformat(): round(h, 2) for d, h in lo.items()} for who, lo in report["loads"].items()},
        "suggestions": suggestions or [],
        "timeline_svg": svg,
    }
    json_path = os.path.join(out_dir, f"worklog-check-{month}.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    svg_path = os.path.join(out_dir, f"worklog-timeline-{month}.svg")
    with open(svg_path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    html_path = os.path.join(out_dir, "worklog-check-latest.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(render_html(report, svg, suggestions))
    return json_path, svg_path, html_path


# ───────────────────────── self-test ─────────────────────────
def self_test():
    cases = [
        ("task1 start 01/06 est 8h", date(2026, 6, 1), 8, date(2026, 6, 2)),
        ("task2 start 02/06 est 16h", date(2026, 6, 2), 16, date(2026, 6, 4)),
        ("xong T6 (05/06) est 8h → due T7", date(2026, 6, 5), 8, date(2026, 6, 6)),
        ("tràn T6→T2 (05/06) est 16h → due thứ Ba", date(2026, 6, 5), 16, date(2026, 6, 9)),
        ("est 40h từ T2 01/06 (lấp T2–T6, xong T6) → due T7 06/06", date(2026, 6, 1), 40, date(2026, 6, 6)),
    ]
    ok = True
    for label, start, est, expect in cases:
        got = minimal_due(start, est)
        status = "PASS" if got == expect else "FAIL"
        ok = ok and got == expect
        print(f"[{status}] {label}: minimal_due={got} (kỳ vọng {expect})")
    # feasibility: 2 task chồng nhau cùng người, mỗi task 8h/ngày trên cùng ngày → quá tải
    t_a = {"key": "A", "start": date(2026, 6, 1), "due": date(2026, 6, 3), "est_h": 16}
    t_b = {"key": "B", "start": date(2026, 6, 1), "due": date(2026, 6, 3), "est_h": 16}
    _loads, unplaced = feasible([t_a, t_b], 8)
    fz = "PASS" if unplaced else "FAIL"
    ok = ok and bool(unplaced)
    print(f"[{fz}] feasibility: 2 task 16h chồng [01-03/06) → unplaced={unplaced} (kỳ vọng có)")
    # window check: est 16h nhưng window chỉ 1 ngày → WINDOW_TOO_SMALL
    t = {"key": "C", "assignee": "X", "type": "task", "is_normal": True,
         "start": date(2026, 6, 1), "due": date(2026, 6, 2), "est_h": 16, "findings": []}
    validate_window(t, 8)
    has = any(f["code"] == "WINDOW_TOO_SMALL" for f in t["findings"])
    print(f"[{'PASS' if has else 'FAIL'}] window: est16h window 1 ngày → WINDOW_TOO_SMALL={has}")
    ok = ok and has
    print("\n" + ("✅ TẤT CẢ PASS" if ok else "❌ CÓ CASE FAIL"))
    return 0 if ok else 1


# ───────────────────────── main ─────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Kiểm tra worklog/thời gian task Jira + gợi ý task mới")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--month", help="YYYY-MM")
    ap.add_argument("--vault", help="đường dẫn vault (mặc định đọc config/factory-config.yaml)")
    ap.add_argument("--project", help="lọc theo project key (csv)")
    ap.add_argument("--assignee", help="lọc theo người (csv); --plan: người được gán task mới")
    ap.add_argument("--cap", type=float, default=CAP_DEFAULT)
    ap.add_argument("--new-tasks", help="JSON: [{name,est_h}] hoặc đường dẫn file .json")
    ap.add_argument("--anchor", help="ngày bắt đầu xếp task mới (YYYY-MM-DD)")
    ap.add_argument("--out", default=None, help="thư mục xuất (mặc định <data_root>/reports)")
    ap.add_argument("--data-root", default=None)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    data_root = args.data_root or os.getcwd()
    out_dir = args.out or os.path.join(data_root, "reports")

    if not args.month:
        print(json.dumps({"error": "thiếu --month YYYY-MM"}), file=sys.stderr)
        return 2
    vault = resolve_vault(args.vault, data_root)
    if not vault or not os.path.isdir(vault):
        print(json.dumps({"error": f"không tìm thấy vault: {vault}"}), file=sys.stderr)
        return 2

    issues = load_issues(vault)
    tasks = build_tasks(issues, args.cap)
    if args.project:
        keys = {k.strip().upper() for k in args.project.split(",") if k.strip()}
        tasks = [t for t in tasks if str(t["project"]).upper() in keys
                 or str(t["key"]).split("-")[0].upper() in keys]
    if args.assignee and args.validate:
        names = {n.strip().lower() for n in args.assignee.split(",") if n.strip()}
        tasks = [t for t in tasks if str(t["assignee"]).lower() in names]

    report = validate(tasks, args.month, args.cap)

    suggestions = None
    if args.plan:
        if not args.new_tasks or not args.anchor or not args.assignee:
            print(json.dumps({"error": "--plan cần --new-tasks, --anchor, --assignee"}), file=sys.stderr)
            return 2
        raw = args.new_tasks
        if os.path.isfile(raw):
            with open(raw, encoding="utf-8") as fh:
                new_tasks = json.load(fh)
        else:
            new_tasks = json.loads(raw)
        suggestions, _ = plan_new_tasks(new_tasks, args.anchor, args.assignee.split(",")[0].strip(),
                                        report["normal"], args.cap)

    svg = render_timeline_svg(report, suggestions, args.assignee.split(",")[0].strip() if (args.plan and args.assignee) else None)
    json_path, svg_path, html_path = write_outputs(report, out_dir, svg, suggestions)

    n_err = sum(1 for t in report["normal"] for f in t["findings"] if f["severity"] == "error")
    summary = {
        "month": args.month, "vault": vault, "tasks_normal": len(report["normal"]),
        "tasks_other": len(report["other"]), "errors": n_err,
        "people_over": sum(1 for p in report["people"] if p["findings"]),
        "json": json_path, "svg": svg_path, "html": html_path,
        "suggestions": suggestions or [],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
