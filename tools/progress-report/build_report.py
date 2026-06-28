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
import base64
import calendar
import glob
import html
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def data_root():
    """Thư mục DỮ LIỆU project user đang chạy — để report/config/vault đọc-ghi ĐÚNG project.

    Khi build_report là bản CÀI (`~/.claude/kora-framework/tools/...`) mà user chạy trong PROJECT (cwd khác),
    REPO_ROOT trỏ vào KF chứ không phải project → report rơi nhầm chỗ + ghi `reports/` (tương đối cwd) lỗi.
    Vì vậy: nếu cwd là project Kora thật (có `config/factory-config.yaml`) → dùng cwd; ngược lại → REPO_ROOT
    (bản dev cwd==REPO_ROOT, hoặc lịch nền orchestrator cwd==REPO_ROOT → giữ nguyên hành vi cũ)."""
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, "config", "factory-config.yaml")):
        return cwd
    return REPO_ROOT

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


def working_days_between(d1, d2):
    """Số NGÀY LÀM VIỆC (T2–6) từ d1 đến d2 INCLUSIVE (date hoặc 'YYYY-MM-DD').
    start=15, due=16 → 1 (làm TRONG ngày, không phải 2 ngày). Cùng ngày → 1 (nếu là ngày làm việc)."""
    def _d(x):
        if isinstance(x, date):
            return x
        try:
            return date(int(str(x)[:4]), int(str(x)[5:7]), int(str(x)[8:10]))
        except Exception:  # noqa: BLE001
            return None
    a, b = _d(d1), _d(d2)
    if not a or not b:
        return 0
    if b < a:
        a, b = b, a
    # 'start 15 / due 16' = 1 ngày làm việc → đếm [a, b) (không gồm mốc cuối), tối thiểu 1 nếu a là ngày làm việc.
    n = 0
    cur = a
    while cur < b:
        if cur.weekday() < 5:
            n += 1
        cur = cur.fromordinal(cur.toordinal() + 1)
    if n == 0 and a.weekday() < 5:   # cùng ngày / cùng 1 ngày làm việc
        n = 1
    return n


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
            key = fm.get("jira_key") or fm.get("excel_key")   # excel: import_excel.py ghi cả 2
            if fm.get("source") not in ("jira", "excel") or not key:
                continue
            fm["jira_key"] = key   # chuẩn hoá → downstream (dedup/hiển thị) dùng jira_key cho cả nguồn excel
            fm["_summary"] = issue_summary(fm, body)
            issues.append(fm)
    return issues


# ══════════════════════════════════════════════════════════════════════════════
# REPORT ĐA LOẠI (Pha 2): invoice / custom — đọc note source:invoice trong vault.
# Luồng progress (Jira) bên dưới KHÔNG đổi; dispatch ở main() rẽ nhánh sớm.
# ══════════════════════════════════════════════════════════════════════════════
def load_invoices(vault):
    """Nạp note HOÁ ĐƠN (source: invoice) trong vault → list dict (cho --report-type invoice/custom)."""
    invs = []
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
            fm, _body = parse_frontmatter(text)
            if fm.get("source") != "invoice":
                continue
            invs.append(fm)
    return invs


def _vnd(n):
    try:
        n = float(n)
    except (TypeError, ValueError):
        n = 0
    return f"{n:,.0f}".replace(",", ".") + " ₫"


def _inv_bars(pairs, width=520, bar_h=26, gap=12):
    if not pairs:
        return ""
    mx = max((v for _, v in pairs), default=0) or 1
    h = len(pairs) * (bar_h + gap) + gap
    out = [f'<svg viewBox="0 0 {width} {h}" width="100%" height="{h}" '
           f'xmlns="http://www.w3.org/2000/svg" role="img">']
    palette = ["#2b50c2", "#2e9e8f", "#c2772b", "#8a4fc2", "#c23b5e", "#3b8ac2"]
    y = gap
    for i, (label, val) in enumerate(pairs):
        bw = max(2, int((width - 230) * (val / mx)))
        c = palette[i % len(palette)]
        out.append(f'<text x="0" y="{y+int(bar_h*0.7)}" font-size="13" fill="#555">{esc(label)[:26]}</text>')
        out.append(f'<rect x="170" y="{y}" width="{bw}" height="{bar_h}" rx="4" fill="{c}"/>')
        out.append(f'<text x="{170+bw+6}" y="{y+int(bar_h*0.7)}" font-size="12" fill="#777">{_vnd(val)}</text>')
        y += bar_h + gap
    out.append("</svg>")
    return "".join(out)


def invoice_blocks(invoices):
    """Tính các KHỐI dữ liệu hoá đơn → dict html (cho layout mặc định HOẶC template custom)."""
    from collections import defaultdict
    rows = []
    for v in invoices:
        sub = float(v.get("subtotal") or 0)
        vat = float(v.get("vat") or 0)
        tot = float(v.get("total") or 0) or (sub + vat)
        rows.append({"invoice_no": str(v.get("invoice_no") or ""), "date": str(v.get("date") or ""),
                     "vendor": str(v.get("vendor") or ""), "category": str(v.get("category") or "Khác"),
                     "subtotal": sub, "vat": vat, "total": tot})
    rows.sort(key=lambda x: x["date"])
    n = len(rows)
    sub = sum(r["subtotal"] for r in rows)
    vat = sum(r["vat"] for r in rows)
    tot = sum(r["total"] for r in rows)
    by_cat, by_vendor, by_month = defaultdict(float), defaultdict(float), defaultdict(float)
    for r in rows:
        by_cat[r["category"]] += r["total"]
        by_vendor[r["vendor"]] += r["total"]
        by_month[(r["date"] or "0000-00")[:7]] += r["total"]
    cat_pairs = sorted(by_cat.items(), key=lambda x: -x[1])
    vendor_pairs = sorted(by_vendor.items(), key=lambda x: -x[1])
    month_pairs = sorted(by_month.items())
    dates = [r["date"] for r in rows if r["date"]]
    period = f"{dates[0]} → {dates[-1]}" if dates else "—"
    kpis = "".join(
        f'<div class="kpi"><div class="kpi-v">{esc(val)}</div><div class="kpi-l">{esc(lbl)}</div></div>'
        for lbl, val in [("Số hoá đơn", str(n)), ("Tiền hàng", _vnd(sub)),
                         ("Tổng VAT", _vnd(vat)), ("TỔNG CHI", _vnd(tot))])
    trows = "".join(
        f"<tr><td>{esc(r['invoice_no'])}</td><td>{esc(r['date'])}</td><td>{esc(r['vendor'])}</td>"
        f"<td>{esc(r['category'])}</td><td class='num'>{_vnd(r['subtotal'])}</td>"
        f"<td class='num'>{_vnd(r['vat'])}</td><td class='num b'>{_vnd(r['total'])}</td></tr>" for r in rows)
    trows += (f"<tr><td colspan='4' class='b'>TỔNG CỘNG</td><td class='num b'>{_vnd(sub)}</td>"
              f"<td class='num b'>{_vnd(vat)}</td><td class='num b'>{_vnd(tot)}</td></tr>")
    vrows = "".join(
        f"<tr><td>{esc(v)}</td><td class='num b'>{_vnd(t)}</td>"
        f"<td class='num'>{(t/tot*100 if tot else 0):.1f}%</td></tr>" for v, t in vendor_pairs)
    return {"n": n, "subtotal": sub, "vat": vat, "total": tot, "period": period, "KPIS": kpis,
            "TABLE_INVOICES": trows, "TABLE_VENDORS": vrows,
            "CHART_CATEGORY": _inv_bars(cat_pairs), "CHART_MONTH": _inv_bars(list(month_pairs))}


_INVOICE_CSS = (" body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#f4f6fb;color:#1c2540}"
    " .wrap{max-width:980px;margin:0 auto;padding:24px}"
    " .hd{background:linear-gradient(135deg,#1c2e6e,#2b50c2);color:#fff;border-radius:14px;padding:24px 28px}"
    " .hd h1{margin:0 0 4px;font-size:24px}.hd .sub{opacity:.85;font-size:14px}"
    " .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}"
    " .kpi{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.07);text-align:center}"
    " .kpi-v{font-size:20px;font-weight:700;color:#1c2e6e}.kpi-l{font-size:12px;color:#6a7390;margin-top:4px}"
    " .card{background:#fff;border-radius:12px;padding:18px 20px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.07)}"
    " .card h2{font-size:16px;margin:0 0 12px;color:#1c2e6e}"
    " table{width:100%;border-collapse:collapse;font-size:13px}"
    " th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #eef0f6}"
    " th{background:#eef1fb;color:#33406e}.num{text-align:right}.b{font-weight:700;color:#1c2e6e}"
    " .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}"
    " .foot{color:#9aa1b8;font-size:12px;text-align:center;margin:18px 0}"
    " @media(max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}}")


def render_invoice_report(invoices, title="Báo cáo chi phí — Hoá đơn", template_html=None):
    """Render report hoá đơn. template_html=None → layout mặc định; else thay {{KEY}} trong template."""
    b = invoice_blocks(invoices)
    if template_html:
        out = template_html
        repl = {"TITLE": esc(title), "PERIOD": esc(b["period"]), "N": str(b["n"]),
                "KPIS": b["KPIS"], "TABLE_INVOICES": b["TABLE_INVOICES"], "TABLE_VENDORS": b["TABLE_VENDORS"],
                "CHART_CATEGORY": b["CHART_CATEGORY"], "CHART_MONTH": b["CHART_MONTH"],
                "TOTAL": _vnd(b["total"]), "SUBTOTAL": _vnd(b["subtotal"]), "VAT": _vnd(b["vat"])}
        for k, val in repl.items():
            out = out.replace("{{" + k + "}}", val)
        return out
    return ("<!DOCTYPE html><html lang='vi'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>{esc(title)}</title><style>{_INVOICE_CSS}</style></head><body><div class='wrap'>"
            f"<div class='hd'><h1>{esc(title)}</h1><div class='sub'>Kỳ: {esc(b['period'])} · {b['n']} hoá đơn · "
            "Nguồn: hoá đơn quét (OCR) · VND</div></div>"
            f"<div class='kpis'>{b['KPIS']}</div>"
            f"<div class='grid2'><div class='card'><h2>Chi theo phân loại</h2>{b['CHART_CATEGORY']}</div>"
            f"<div class='card'><h2>Chi theo tháng</h2>{b['CHART_MONTH']}</div></div>"
            "<div class='card'><h2>Tổng theo nhà cung cấp</h2><table><thead><tr><th>Nhà cung cấp</th>"
            f"<th class='num'>Tổng chi</th><th class='num'>Tỷ trọng</th></tr></thead><tbody>{b['TABLE_VENDORS']}</tbody></table></div>"
            f"<div class='card'><h2>Chi tiết hoá đơn ({b['n']})</h2><table><thead><tr><th>Số HĐ</th><th>Ngày</th>"
            "<th>Nhà cung cấp</th><th>Phân loại</th><th class='num'>Tiền hàng</th><th class='num'>VAT</th>"
            f"<th class='num'>Tổng</th></tr></thead><tbody>{b['TABLE_INVOICES']}</tbody></table></div>"
            "<div class='foot'>Kora — Report hoá đơn · build_report.py --report-type invoice</div>"
            "</div></body></html>")


def load_report_template(name, droot):
    """Đọc templates/reports/_index.json → tìm template theo name → trả (html, base, title)."""
    idx = os.path.join(droot, "templates", "reports", "_index.json")
    if not os.path.exists(idx):
        die(f"Chưa có registry template: {idx}. Tạo template trước (workflow report).")
    reg = json.load(open(idx, encoding="utf-8"))
    ent = next((t for t in reg.get("templates", []) if t.get("name") == name), None)
    if not ent:
        names = ", ".join(t.get("name", "?") for t in reg.get("templates", [])) or "(rỗng)"
        die(f"Không thấy template '{name}'. Có: {names}.")
    fp = os.path.join(droot, "templates", "reports", ent["file"])
    if not os.path.exists(fp):
        die(f"File template không tồn tại: {fp}")
    return open(fp, encoding="utf-8").read(), ent.get("base", "invoice"), ent.get("title")


# ── Pha 4: Meeting + Roadmap ──────────────────────────────────────────────────
def load_meeting_rows(path):
    """Đọc biên bản họp đã AI-tóm-tắt (list[dict] title/date/attendees/summary/decisions/action_items/risks)."""
    if not path or not os.path.exists(path):
        return []
    try:
        data = json.load(open(path, encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _mr_list(items):
    items = items or []
    if not items:
        return "<div class='muted'>(không có)</div>"
    return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>"


_MR_CSS = (" body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#f5f4fb;color:#241c40}"
    " .wrap{max-width:980px;margin:0 auto;padding:24px}"
    " .hd{background:linear-gradient(135deg,#3a2e6e,#6b4ec2);color:#fff;border-radius:14px;padding:24px 28px}"
    " .hd h1{margin:0 0 4px;font-size:24px}.hd .sub{opacity:.85;font-size:14px}"
    " .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:18px 0}"
    " .kpi{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06);text-align:center}"
    " .kpi-v{font-size:22px;font-weight:700;color:#4a3aa7}.kpi-l{font-size:12px;color:#6a6790;margin-top:4px}"
    " .card{background:#fff;border-radius:12px;padding:18px 20px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}"
    " .card h2{font-size:16px;margin:0 0 6px;color:#4a3aa7}"
    " .muted{color:#8a86a8;font-size:13px}.sec{margin-top:10px}.sec b{color:#33306e}"
    " ul{margin:6px 0 0;padding-left:20px}li{font-size:13px;margin:3px 0}"
    " .grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}p{font-size:14px;line-height:1.55}"
    " .foot{color:#9a96b8;font-size:12px;text-align:center;margin:18px 0}"
    " @media(max-width:760px){.grid2{grid-template-columns:1fr}}")


def render_meeting_roadmap(meetings, issues, title="Báo cáo Meeting & Roadmap"):
    """Gộp BIÊN BẢN HỌP (AI summary) + ROADMAP từ task Jira → 1 report chiến lược (Pha 4)."""
    cur, nxt, done = [], [], 0
    for i in issues or []:
        st = (i.get("status") or "").strip().lower()
        label = f"{i.get('jira_key') or ''} — {i.get('_summary') or ''}".strip(" —")
        if any(w in st for w in ("done", "closed", "resolved", "hoàn thành", "complete")):
            done += 1
        elif any(w in st for w in ("progress", "doing", "đang", "review", "test")):
            cur.append(label)
        else:
            nxt.append(label)
    n_dec = sum(len(m.get("decisions") or []) for m in meetings)
    n_act = sum(len(m.get("action_items") or []) for m in meetings)
    n_risk = sum(len(m.get("risks") or []) for m in meetings)
    kpis = [("Cuộc họp", len(meetings)), ("Quyết định", n_dec), ("Action item", n_act), ("Rủi ro", n_risk)]
    if issues:
        kpis.append(("Task (Jira)", len(issues)))
    kpi_html = "".join(f'<div class="kpi"><div class="kpi-v">{v}</div>'
                       f'<div class="kpi-l">{esc(l)}</div></div>' for l, v in kpis)
    cards = ""
    for m in meetings:
        cards += (f"<div class='card'><h2>{esc(m.get('title') or 'Họp')}</h2>"
                  f"<div class='muted'>{esc(m.get('date') or '')} · {esc(m.get('attendees') or '')}</div>"
                  f"<p>{esc(m.get('summary') or '')}</p>"
                  f"<div class='sec'><b>Quyết định</b>{_mr_list(m.get('decisions'))}</div>"
                  f"<div class='sec'><b>Hành động</b>{_mr_list(m.get('action_items'))}</div>"
                  f"<div class='sec'><b>Rủi ro</b>{_mr_list(m.get('risks'))}</div></div>")
    if issues:
        roadmap = (f"<div class='card'><h2>🗺️ Roadmap (từ {len(issues)} task Jira)</h2>"
                   f"<div class='grid2'><div><b>Đang làm ({len(cur)})</b>{_mr_list(cur[:15])}</div>"
                   f"<div><b>Kế tiếp ({len(nxt)})</b>{_mr_list(nxt[:15])}</div></div>"
                   f"<div class='muted' style='margin-top:8px'>Đã xong: {done} task.</div></div>")
    else:
        roadmap = "<div class='card'><div class='muted'>Chưa có task Jira trong vault để dựng roadmap (quét Jira để bổ sung).</div></div>"
    dates = sorted(str(m.get("date") or "") for m in meetings if m.get("date"))
    period = f"{dates[0]} → {dates[-1]}" if dates else "—"
    return ("<!DOCTYPE html><html lang='vi'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>{esc(title)}</title><style>{_MR_CSS}</style></head><body><div class='wrap'>"
            f"<div class='hd'><h1>{esc(title)}</h1><div class='sub'>Kỳ: {esc(period)} · "
            f"{len(meetings)} cuộc họp · {len(issues or [])} task Jira</div></div>"
            f"<div class='kpis'>{kpi_html}</div>{roadmap}"
            f"<h2 style='color:#4a3aa7;margin:18px 0 4px'>Biên bản họp ({len(meetings)})</h2>{cards}"
            "<div class='foot'>Kora — Meeting & Roadmap · build_report.py --report-type meeting-roadmap</div>"
            "</div></body></html>")


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


def apply_scope(issues, scope, recent_days):
    """Giới hạn PHẠM VI báo cáo (dự án lớn không lấy hết) — trả (issues_lọc, nhãn).
    sprint = chỉ hạng mục công việc trong SPRINT ĐANG CHẠY (fallback N ngày gần đây nếu không có sprint active);
    recent = hạng mục công việc có 'updated' trong N ngày; all/rỗng = toàn bộ. KHÔNG trả rỗng khi vault có data.
    LƯU Ý: row IMPORT (source ≠ jira, vd Excel/SharePoint) là SNAPSHOT hiện tại → LUÔN giữ, recency/sprint chỉ áp cho note Jira."""
    if scope in ("all", "", None):
        return issues, "Toàn bộ"
    cutoff = (date.today() - timedelta(days=max(1, int(recent_days or 30)))).isoformat()
    # Tách Jira (có time-series 'updated') vs IMPORT (Excel/SharePoint — snapshot, không lọc theo recency).
    imported = [i for i in issues if (i.get("source") or "jira") != "jira"]
    jira = [i for i in issues if (i.get("source") or "jira") == "jira"]
    recent_jira = [i for i in jira if str(i.get("updated") or "")[:10] >= cutoff]
    if scope == "sprint":
        sp = [i for i in jira if (i.get("sprint_state") or "").lower() == "active"]
        if sp or imported:
            return sp + imported, "Sprint đang chạy"
        if recent_jira:
            return recent_jira, f"{recent_days} ngày gần đây (không có sprint active)"
        return issues, "Toàn bộ (không có sprint active / hoạt động gần đây)"
    if scope == "recent":
        if recent_jira or imported:
            return recent_jira + imported, f"{recent_days} ngày gần đây"
        return issues, f"Toàn bộ (không có hoạt động trong {recent_days} ngày)"
    return issues, "Toàn bộ"


def compute(issues, smap, today, complexity_high=7, qc_members=None, pm_members=None):
    total = len(issues)
    grp = _status_breakdown(issues, smap)
    by_type = {}
    for i in issues:
        by_type[i.get("type", "hạng mục")] = by_type.get(i.get("type", "hạng mục"), 0) + 1
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
                "project": i.get("project", "—"), "type": i.get("type", "hạng mục"),
                "spent_s": int(i.get("time_spent_s") or 0), "est_s": int(i.get("time_estimate_s") or 0),
                "story_points": i.get("story_points", ""),
            } for i in items], key=lambda x: x["group"]),
        })

    # ── ROADMAP: gom MỌI sprint theo sprint_name → current/next/backlog (cho PM điều phối) ──
    sp_all = {}
    for i in issues:
        sn = i.get("sprint_name")
        if sn:
            sp_all.setdefault(str(sn), []).append(i)
    active_names = {str(i.get("sprint_name")) for i in active}
    roadmap = []
    for name, items in sp_all.items():
        g = _status_breakdown(items, smap)
        t = _time_sum(items)
        ends = sorted(str(x.get("sprint_end") or "")[:10] for x in items if x.get("sprint_end"))
        roadmap.append({
            "name": name, "phase": "current" if name in active_names else "other",
            "end": (ends[-1] if ends else ""), "total": len(items),
            "done": g["done"], "in_progress": g["in_progress"], "todo": g["todo"],
            "pct_done": pct(g["done"], len(items)),
            "story_points": sum(float(x["story_points"]) for x in items if isinstance(x.get("story_points"), (int, float))),
            "est_s": t["estimate_s"], "spent_s": t["spent_s"],
        })
    roadmap.sort(key=lambda r: (r["phase"] != "current", r["end"] == "", r["end"], r["name"]))
    _noncur = [r for r in roadmap if r["phase"] != "current"]
    for idx, r in enumerate(_noncur):   # sprint không-current đầu tiên = next, còn lại = backlog
        r["phase"] = "next" if idx == 0 else "backlog"

    # ── Theo người: assignee (Dev) + reporter-của-Bug (QC) ──────────────────────────
    # QC (tester) TẠO bug, KHÔNG logtime như dev (hay chỉ join cuối sprint) → KHÔNG đo bằng giờ-công.
    # Vai trò: config reports.qc_members ƯU TIÊN; else auto = 0 logtime + có report Bug + KHÔNG ôm việc khác Bug.
    qc_set = {str(n).strip().lower() for n in (qc_members or []) if str(n).strip()}
    # PM/PO TẠO Epic/Request/US — KHÔNG logtime như Dev, KHÔNG "chạy hết sprint" theo giờ → KHÔNG đo bằng giờ-công.
    pm_set = {str(n).strip().lower() for n in (pm_members or []) if str(n).strip()}
    PM_TYPES = {"epic", "story", "user_story", "user story", "request", "change request"}  # gồm dạng chuẩn hoá "user_story"
    LOGW_TYPES = {"task", "sub-task", "subtask", "bug"}   # loại việc THỰC SỰ cần log giờ
    def _is_bug(i):
        return str(i.get("type") or "").lower() == "bug" or str(i.get("jira_issue_type") or "").lower() == "bug"
    def _is_pm_type(i):
        return (str(i.get("type") or "").lower() in PM_TYPES
                or str(i.get("jira_issue_type") or "").lower() in PM_TYPES)
    bugs_reported = {}   # người → SỐ Bug họ TẠO (reporter) — đo năng suất QC thay cho giờ-công
    pm_reported = {}     # người → SỐ Epic/Request/US họ TẠO (reporter) — dấu hiệu PM/PO, không tính giờ-công
    for i in issues:
        if _is_bug(i):
            rep = str(i.get("reporter") or "").strip()
            if rep:
                bugs_reported[rep] = bugs_reported.get(rep, 0) + 1
        if _is_pm_type(i):
            rep = str(i.get("reporter") or "").strip()
            if rep:
                pm_reported[rep] = pm_reported.get(rep, 0) + 1
    who = {}
    for i in issues:
        who.setdefault(i.get("assignee") or "(chưa giao)", []).append(i)
    for rep in bugs_reported:          # QC chỉ-là-reporter (chưa từng được assign) → VẪN vào danh sách người (trước đây bị sót)
        who.setdefault(rep, [])
    for rep in pm_reported:            # PM chỉ-là-reporter (tạo Epic/Request/US, không được assign) → VẪN vào danh sách người
        who.setdefault(rep, [])
    by_assignee = []
    for name, items in who.items():
        g = _status_breakdown(items, smap)
        t = _time_sum(items)
        nbug = bugs_reported.get(name, 0)
        npm = pm_reported.get(name, 0)
        if name in ("(chưa giao)", "—", ""):
            role = "—"
        elif name.lower() in qc_set:
            role = "QC"
        elif name.lower() in pm_set:
            role = "PM"
        elif t["spent_s"] == 0 and nbug > 0 and not any(not _is_bug(x) for x in items):
            role = "QC"   # auto: 0 logtime + có tạo bug + không ôm việc nào khác Bug
        elif t["spent_s"] == 0 and npm > 0 and not any(str(x.get("type") or "").lower() in LOGW_TYPES for x in items):
            role = "PM"   # auto: 0 logtime + có tạo Epic/Request/US + không ôm Task/Sub-task/Bug cần log
        else:
            role = "Dev"
        by_assignee.append({
            "assignee": name, "role": role, "total": len(items), "todo": g["todo"],
            "in_progress": g["in_progress"], "done": g["done"], "pct_done": pct(g["done"], len(items)),
            "time": t, "bugs_reported": nbug, "pm_reported": npm,
            "story_points": sum(float(i["story_points"]) for i in items if isinstance(i.get("story_points"), (int, float))),
        })
    by_assignee.sort(key=lambda x: ({"Dev": 0, "PM": 1, "QC": 2}.get(x["role"], 3), -x["total"], x["assignee"]))  # Dev → PM → QC

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

    # ── Năng lực giờ công — THÁNG (5 ngày/tuần × 8h/ngày), so với SỐ NGÀY LÀM VIỆC ĐÃ TRÔI QUA (công bằng) ──
    try:
        ty, tmo, tday = int(today[:4]), int(today[5:7]), int(today[8:10])
    except Exception:  # noqa: BLE001
        _n = datetime.now(); ty, tmo, tday = _n.year, _n.month, _n.day
    days_in_month = calendar.monthrange(ty, tmo)[1]
    working_days = sum(1 for d in range(1, days_in_month + 1) if date(ty, tmo, d).weekday() < 5)
    # Ngày làm việc ĐÃ HOÀN THÀNH (đầu tháng → HẾT HÔM QUA). HÔM NAY chỉ tính SAU khi HẾT NGÀY (24:00) — ngày chưa
    # xong thì CHƯA kỳ vọng 8h logtime cho hôm nay (tránh report lúc 8:00 báo "thiếu 8h" sai). Mặc định 24 = không tính
    # hôm nay khi còn trong ngày; đổi mốc qua env KORA_WORKDAY_END_HOUR (vd 17 nếu muốn tính sau giờ tan làm).
    end_hour = int(os.getenv("KORA_WORKDAY_END_HOUR") or 24)
    today_done = date(ty, tmo, tday).weekday() < 5 and datetime.now().hour >= end_hour
    last_complete = tday if today_done else tday - 1
    wd_elapsed = sum(1 for d in range(1, min(last_complete, days_in_month) + 1) if date(ty, tmo, d).weekday() < 5)
    std_person = working_days * 8 * 3600           # mục tiêu THÁNG / người (giây)
    expect_person = wd_elapsed * 8 * 3600          # KỲ VỌNG đến mốc HOÀN THÀNH gần nhất (0 = đầu kỳ, chưa hết ngày nào)
    for a in by_assignee:
        sp = a["time"]["spent_s"]
        a["logged_working_days"] = round(sp / (8 * 3600), 1)
        if a["role"] != "Dev":   # QC/placeholder: KHÔNG đo bằng giờ-công (không logtime / join cuối sprint) → để TRỐNG, đo bằng số Bug
            a["std_seconds"] = None
            a["expected_so_far_s"] = None
            a["ot_seconds"] = 0
            a["under_seconds"] = 0
            a["pct_capacity"] = None
            continue
        a["std_seconds"] = std_person
        a["expected_so_far_s"] = expect_person
        # expect=0 (đầu kỳ / hôm nay chưa hết giờ) → KHÔNG flag thiếu/OT (tránh "thiếu 8h" sai lúc 8:00).
        a["ot_seconds"] = max(0, sp - expect_person) if expect_person else 0
        a["under_seconds"] = max(0, expect_person - sp) if expect_person else 0
        a["pct_capacity"] = pct(sp, expect_person) if expect_person else 0
    members = [a for a in by_assignee if a["role"] == "Dev"]   # team capacity CHỈ tính Dev (QC không logtime → không kéo tụt kỳ vọng team)
    team_std = len(members) * std_person
    team_expect = len(members) * expect_person
    capacity = {
        "month": f"{tmo:02d}/{ty}", "working_days": working_days, "working_days_elapsed": wd_elapsed,
        "today_counted": today_done, "workday_end_hour": end_hour,
        "std_hours_person": working_days * 8, "std_seconds_person": std_person,
        "expected_so_far_person_s": expect_person, "team_expected_so_far_s": team_expect,
        "num_members": len(members), "team_std_seconds": team_std,
        "logged_seconds": tsum["spent_s"], "logged_working_days": round(tsum["spent_s"] / (8 * 3600), 1),
        "ot_seconds": max(0, tsum["spent_s"] - team_expect) if team_expect else 0,
        "under_seconds": max(0, team_expect - tsum["spent_s"]) if team_expect else 0,
        "pct_capacity": pct(tsum["spent_s"], team_expect) if team_expect else 0,
    }

    # ── Logtime theo LOẠI — chỉ Task/Sub-task/Bug thực sự log; Epic/Story/Request thường KHÔNG log ──
    LOG_TYPES = {"task", "sub-task", "subtask", "bug"}
    logged_by_type, est_by_type = {}, {}
    for i in issues:
        tt = i.get("type") or "issue"
        logged_by_type[tt] = logged_by_type.get(tt, 0) + int(i.get("time_spent_s") or 0)
        est_by_type[tt] = est_by_type.get(tt, 0) + int(i.get("time_estimate_s") or 0)
    pm_names = {str(a["assignee"]).strip().lower() for a in by_assignee if a["role"] == "PM"}  # PM không tính log giờ
    work_no_log = [{"key": i.get("jira_key"), "summary": i.get("_summary", ""),
                    "type": i.get("type"), "assignee": i.get("assignee", "—")}
                   for i in issues
                   if (i.get("type") or "") in LOG_TYPES
                   and str(i.get("assignee") or "").strip().lower() not in pm_names
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

    # 🧩 ĐỘ PHỨC TẠP (Complexity) — TRỌNG TÂM: phân bố điểm + hạng mục phức tạp cao (>= ngưỡng, mặc định 7)
    complexity_dist, cx_pairs = {}, []
    for i in issues:
        cv = i.get("complexity")
        if isinstance(cv, int):
            complexity_dist[cv] = complexity_dist.get(cv, 0) + 1
            cx_pairs.append((cv, i))
    high_complexity = sorted(
        ({"key": i.get("jira_key"), "summary": i.get("_summary", ""), "complexity": cv,
          "assignee": i.get("assignee", "—"), "status": i.get("status", ""),
          "group": issue_group(i, smap), "project": i.get("project", "—")}
         for cv, i in cx_pairs if cv >= complexity_high),
        key=lambda x: -x["complexity"])
    complexity = {
        "field_present": bool(cx_pairs), "high_threshold": complexity_high,
        "high_count": len(high_complexity), "total_scored": len(cx_pairs),
        "max": max(complexity_dist) if complexity_dist else 0,
        "dist": complexity_dist, "high": high_complexity[:50],
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "total": total,
        "by_status_group": grp, "pct_done": pct(grp["done"], total), "by_type": by_type,
        "time": tsum, "active_sprints": active_sprints, "roadmap": roadmap, "by_assignee": by_assignee, "by_project": by_project,
        "risks": {"overdue": overdue[:50], "active_sprint_no_assignee": no_assignee[:50],
                  "active_sprint_no_estimate": no_est[:50]},
        "with_time": sum(1 for i in issues if i.get("time_estimate_s") or i.get("time_spent_s")),
        "capacity": capacity, "logged_by_type": logged_by_type, "est_by_type": est_by_type,
        "log_types": sorted(LOG_TYPES), "work_no_log": work_no_log[:50], "complexity": complexity,
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
            f'<text x="{cx}" y="{cy + 15}" text-anchor="middle" font-size="10" fill="{PAL["mut"]}">hạng mục</text></svg>'
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


# ── OKR / Standing-Meeting (file CHIẾN LƯỢC, KHÔNG phải task) — section RIÊNG ──
# Claude đọc file OKR/Standing-Meeting → lập reports/_okr-blocks.json (cấu trúc) → build_report render
# section chia nhóm (grid) + khối AI phân tích RIÊNG, vào CẢ dashboard LẪN email. None → không có section.
def load_okr_blocks(out_dir):
    """Đọc reports/_okr-blocks.json → dict {title, source, groups:[{icon,label,items:[{name,chips:[]}]}], analysis_md}. None nếu thiếu/sai."""
    p = os.path.join(out_dir, "_okr-blocks.json")
    if not os.path.exists(p):
        return None
    try:
        data = json.loads(open(p, encoding="utf-8").read())
    except Exception:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("groups"), list) or not data["groups"]:
        return None
    return data


def _okr_chip(chip):
    """chip = 'text' HOẶC {'text':..., 'tone':'ok|warn|risk|info'} → (text, tone)."""
    if isinstance(chip, dict):
        return str(chip.get("text", "")).strip(), str(chip.get("tone", "") or "").lower()
    return str(chip).strip(), ""


def render_okr_dashboard(data):
    """Section OKR/Standing-Meeting cho DASHBOARD (grid chia nhóm + AI riêng)."""
    if not data:
        return ""
    title = esc(data.get("title") or "Cập nhật nhóm / OKR")
    src = esc(data.get("source") or "")
    tone_c = {"ok": PAL["green"], "warn": PAL["orange"], "risk": PAL["red"], "info": PAL["blue"]}
    cols = []
    for g in data.get("groups", []):
        items_html = ""
        for it in (g.get("items") or []):
            chips = ""
            for ch in (it.get("chips") or []):
                t, tone = _okr_chip(ch)
                if not t:
                    continue
                c = tone_c.get(tone, PAL["mut"])
                chips += (f'<span style="display:inline-block;margin:3px 4px 0 0;padding:2px 9px;border-radius:999px;'
                          f'border:1px solid {c};color:{c};font-size:11px;line-height:1.5">{esc(t)}</span>')
            items_html += (f'<div style="margin-top:9px"><div style="font-weight:700;color:{PAL["ink"]};font-size:13px">'
                           f'{esc(it.get("name", ""))}</div><div>{chips}</div></div>')
        cols.append(f'<div style="flex:1 1 250px;min-width:230px"><div style="color:{PAL["teal"]};font-weight:800;'
                    f'font-size:13.5px;border-bottom:1px solid {PAL["line"]};padding-bottom:5px">'
                    f'{esc(g.get("icon", ""))} {esc(g.get("label", ""))}</div>{items_html}</div>')
    grid = f'<div style="display:flex;flex-wrap:wrap;gap:16px 28px">{"".join(cols)}</div>'
    ana = ""
    if data.get("analysis_md"):
        ana = (f'<div style="margin-top:14px;border-top:1px dashed {PAL["line"]};padding-top:10px">'
               f'<b style="color:#c9b8ff">🤖 Phân tích AI — OKR / Chiến lược</b>{render_ai_cards(data["analysis_md"])}</div>')
    badge = f' · <span style="color:{PAL["mut"]};font-size:14px">{src}</span>' if src else ""
    return f'<h2>📋 {title}{badge}</h2><div class="pr-card">{grid}{ana}</div>'


def render_okr_email(data):
    """Section OKR/Standing-Meeting cho EMAIL (email-safe, chia nhóm + AI riêng)."""
    if not data:
        return ""
    title = esc(data.get("title") or "Cập nhật nhóm / OKR")
    src = esc(data.get("source") or "")
    tone_c = {"ok": EPAL["green"], "warn": EPAL["orange"], "risk": EPAL["red"], "info": EPAL["blue"]}
    blocks = ""
    for g in data.get("groups", []):
        items = ""
        for it in (g.get("items") or []):
            chips = ""
            for ch in (it.get("chips") or []):
                t, tone = _okr_chip(ch)
                if not t:
                    continue
                c = tone_c.get(tone, EPAL["mut"])
                chips += (f'<span style="display:inline-block;margin:2px 4px 0 0;padding:1px 8px;border:1px solid {c};'
                          f'color:{c};border-radius:999px;font-size:11px">{esc(t)}</span>')
            items += (f'<div style="margin-top:6px"><span style="font-weight:700;color:{EPAL["ink"]};font-size:12.5px">'
                      f'{esc(it.get("name", ""))}</span><br>{chips}</div>')
        blocks += (f'<div style="margin-top:10px"><div style="color:{EPAL["blue"]};font-weight:800;font-size:12.5px;'
                   f'border-bottom:1px solid {EPAL["line"]};padding-bottom:3px">{esc(g.get("icon", ""))} '
                   f'{esc(g.get("label", ""))}</div>{items}</div>')
    ana = ""
    if data.get("analysis_md"):
        ana = (f'<div style="margin-top:10px;border-top:1px dashed {EPAL["line"]};padding-top:8px">'
               f'{render_ai_cards(data["analysis_md"])}</div>')
    badge = f' · {src}' if src else ""
    return (f'<tr><td class="kpad" style="padding:10px 22px 2px">'
            f'<div style="font-size:13px;font-weight:800;color:{EPAL["vio"]};text-transform:uppercase;'
            f'letter-spacing:.03em;margin-bottom:4px">📋 {title}{badge}</div>'
            f'<div style="background:{EPAL["chip"]};border:1px solid {EPAL["line"]};border-radius:10px;'
            f'padding:10px 13px">{blocks}{ana}</div></td></tr>')


def render_fragment(m, vault, okr=None):
    t = m["time"]
    cards = "".join([
        kpi("Tổng hạng mục", m["total"], color="ink"),
        kpi("Hoàn thành", f'{m["pct_done"]}%', f'{m["by_status_group"]["done"]}/{m["total"]}', "green"),
        kpi("Ước tính", human_seconds(t["estimate_s"]), color="blue"),
        kpi("Đã log", human_seconds(t["spent_s"]), f'{t["pct_logged"]}% ước tính', "teal"),
        kpi("Còn lại", human_seconds(t["remaining_s"]), color="orange"),
        kpi("Sprint đang chạy", len(m["active_sprints"]), color="vio"),
        kpi("Kỳ vọng đến hôm nay", human_seconds(m["capacity"]["team_expected_so_far_s"]),
            f'{m["capacity"]["working_days_elapsed"]}/{m["capacity"]["working_days"]} ngày làm việc · {m["capacity"]["num_members"]} TV · mục tiêu tháng {human_seconds(m["capacity"]["team_std_seconds"])}', "blue"),
        kpi("Vượt kỳ vọng (OT)" if m["capacity"]["ot_seconds"] else "Thiếu so với kỳ vọng",
            human_seconds(m["capacity"]["ot_seconds"] or m["capacity"]["under_seconds"]),
            f'Đạt {m["capacity"]["pct_capacity"]}% kỳ vọng đến hôm nay',
            "green" if m["capacity"]["ot_seconds"] else "red"),  # dương(OT)=xanh · âm(thiếu)=đỏ
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

    # 🗺️ ROADMAP — gom sprint current/next/backlog cho PM điều phối
    roadmap_html = ""
    if m.get("roadmap"):
        _ph = {"current": "🟢 Hiện tại", "next": "🔵 Kế tiếp", "backlog": "⚪ Backlog"}
        _grp = {"current": "done", "next": "in_progress", "backlog": "todo"}
        rr = "".join(
            f'<tr><td><span class="pr-pill pr-{_grp.get(r["phase"], "todo")}">{_ph.get(r["phase"], r["phase"])}</span></td>'
            f'<td><b>{esc(r["name"])}</b></td><td>{esc(r["end"]) or "—"}</td>'
            f'<td>{r["done"]}/{r["total"]} ({r["pct_done"]}%)</td>'
            f'<td>{r["todo"]} / {r["in_progress"]} / {r["done"]}</td>'
            f'<td>{r["story_points"] or ""}</td>'
            f'<td>{human_seconds(r["spent_s"])} / {human_seconds(r["est_s"])}</td></tr>'
            for r in m["roadmap"])
        roadmap_html = (
            '<div class="pr-card"><div class="pr-card-h"><b>🗺️ Roadmap / Sprint</b>'
            '<span class="pr-mut">hiện tại · kế tiếp · backlog — cho PM điều phối</span></div>'
            '<table class="pr-t"><thead><tr><th>Giai đoạn</th><th>Sprint</th><th>Kết thúc</th>'
            '<th>Done</th><th>Chưa/Đang/Done</th><th>SP</th><th>Log/Ước tính</th></tr></thead>'
            f'<tbody>{rr}</tbody></table></div>')

    def _ot_cell(a):
        # QC & PM không đo bằng giờ-công → "—". Quy ước màu: DƯƠNG (OT) = XANH, ÂM (thiếu) = ĐỎ.
        if a.get("role") in ("QC", "PM"):
            return '<span class="pr-mut">—</span>'
        if a.get("ot_seconds"):
            return f'<span style="color:{PAL["green"]}">+{human_seconds(a["ot_seconds"])}</span>'
        if a.get("under_seconds"):
            return f'<span style="color:{PAL["red"]}">−{human_seconds(a["under_seconds"])}</span>'
        return '<span class="pr-mut">0</span>'
    def _role_cell(a):
        r = a.get("role") or "—"
        if r == "QC":
            return f'<span class="pr-pill" style="background:{PAL["orange"]}1a;color:{PAL["orange"]}">QC</span>'
        if r == "PM":
            return f'<span class="pr-pill" style="background:{PAL["blue"]}1a;color:{PAL["blue"]}">PM</span>'
        if r == "Dev":
            return '<span class="pr-mut">Dev</span>'
        return '<span class="pr-mut">—</span>'
    def _std_cell(a):   # Giờ chuẩn — QC để "—"
        return '<span class="pr-mut">—</span>' if a.get("std_seconds") is None else human_seconds(a["std_seconds"])
    def _cap_cell(a):   # % Năng suất — QC để "—"
        return '<span class="pr-mut">—</span>' if a.get("pct_capacity") is None else f'{a.get("pct_capacity", 0)}%'
    def _bug_cell(a):   # Bug tạo (reporter) — đo năng suất QC
        n = a.get("bugs_reported") or 0
        return f'<span style="color:{PAL["red"]}">{n}</span>' if n else '<span class="pr-mut">0</span>'
    arows = "".join(
        f'<tr class="pr-row" data-assignee="{esc(a["assignee"])}"><td>{esc(a["assignee"])}</td><td>{_role_cell(a)}</td><td>{a["total"]}</td>'
        f'<td>{a["todo"]}</td><td>{a["in_progress"]}</td><td>{a["done"]}</td>'
        f'<td style="min-width:90px">{bar(a["pct_done"], "green")}</td>'
        f'<td>{human_seconds(a["time"]["spent_s"])} / {human_seconds(a["time"]["estimate_s"])}</td>'
        f'<td>{_std_cell(a)}</td><td>{_ot_cell(a)}</td>'
        f'<td>{_cap_cell(a)}</td><td>{_bug_cell(a)}</td>'
        f'<td>{a["story_points"] or ""}</td></tr>' for a in m["by_assignee"])
    assignee_html = (
        f'<table class="pr-t"><thead><tr><th>Thành viên</th><th>Vai trò</th><th>Tổng</th><th>Chưa làm</th><th>Đang làm</th>'
        f'<th>Hoàn thành</th><th>% Hoàn thành</th><th>Đã log / Ước tính</th><th>Giờ chuẩn</th>'
        f'<th>OT / Thiếu</th><th>% Năng suất</th><th>Bug tạo</th><th>Story Points</th></tr></thead><tbody>{arows}</tbody></table>')

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
                 '<!--KR-AI-START-->'
                 '<div class="pr-mut" style="margin-top:6px">Khu vực này được Claude điền khi chạy báo cáo: '
                 'phân loại rủi ro theo mức · dự đoán nguy cơ trượt timeline mỗi sprint (kèm lý do) · giải pháp '
                 'cho từng rủi ro · đề xuất theo từng thành viên · tổng kết điều hành.</div>'
                 '<!--KR-AI-END--></section>')
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
    _msl = m.get("scope_label", "")
    if _msl and not _msl.startswith("Toàn bộ"):
        _scope = f"{_scope} · {esc(_msl)}"
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
    # 🧩 Độ phức tạp (Complexity) — section trọng tâm cho dashboard
    cxm = m.get("complexity", {})
    cx_section = ""
    if cxm.get("field_present"):
        cthr = cxm.get("high_threshold", 7)
        cdist = cxm.get("dist", {})
        cdmax = max(cdist.values()) if cdist else 1
        cxmax = cxm.get("max", 0) or 1
        def cx_color(val):   # độ phức tạp: ĐIỂM CÀNG LỚN màu CAM càng ĐẬM (KHÔNG dùng đỏ — đỏ = lỗi/nguy hiểm)
            r = max(0.0, min(1.0, (val or 0) / cxmax))
            lo, hi = (255, 224, 178), (191, 84, 13)   # cam nhạt → cam/hổ phách đậm
            return "#%02x%02x%02x" % tuple(round(lo[j] + (hi[j] - lo[j]) * r) for j in range(3))
        def cx_text(val):    # chữ trắng khi nền cam đậm, chữ nâu khi nền nhạt (giữ độ tương phản)
            return "#fff" if (val or 0) / cxmax >= 0.45 else "#5a3210"
        cbars = "".join(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
            f'<span style="width:62px;font-size:12px;color:#667">Điểm {k}</span>'
            f'<span style="flex:1;height:14px;background:#eceff5;border-radius:4px;overflow:hidden">'
            f'<span style="display:block;height:14px;width:{round(100 * v / cdmax)}%;background:{cx_color(int(k))}"></span></span>'
            f'<b style="width:58px;font-size:12px;text-align:right">{v}</b></div>'
            for k, v in sorted(cdist.items(), key=lambda kv: -int(kv[0])))
        chrows = "".join(
            f'<tr><td><b>{esc(x["key"])}</b></td><td>{esc((x["summary"] or "")[:70])}</td>'
            f'<td style="text-align:center;color:{cx_text(x["complexity"])};background:{cx_color(x["complexity"])};font-weight:800">{x["complexity"]}</td>'
            f'<td>{esc(x["assignee"])}</td><td>{esc(x["status"])}</td></tr>'
            for x in cxm.get("high", [])[:30])
        chtbl = (f'<table class="pr-t"><thead><tr><th>Hạng mục</th><th>Tóm tắt</th><th>Điểm</th><th>Người</th><th>Trạng thái</th></tr></thead><tbody>{chrows}</tbody></table>'
                 if chrows else '<div class="pr-mut">Không có hạng mục công việc ≥ ngưỡng phức tạp cao.</div>')
        cx_section = (f'<h2>🧩 Độ phức tạp (Complexity) — trọng tâm</h2><div class="pr-card">'
                      f'<p style="margin:0 0 8px"><b style="color:{PAL["orange"]};font-size:18px">{cxm.get("high_count", 0)}</b> '
                      f'hạng mục PHỨC TẠP CAO (điểm ≥ {cthr}) / {cxm.get("total_scored", 0)} hạng mục công việc có điểm · cao nhất '
                      f'<b>{cxm.get("max", 0)}</b>. Số càng lớn càng phức tạp → ưu tiên review &amp; nguồn lực.</p>'
                      f'{cbars}{chtbl}</div>')
    okr_html = render_okr_dashboard(okr)
    return f"""{style}<div class="pr">
<h1>📊 Báo cáo tiến độ dự án</h1>
<div class="pr-sub">{_scope} · Vault: {esc(os.path.basename(vault.rstrip('/')))} · cập nhật {esc(gen)} (giờ UTC) · {m['total']} hạng mục công việc</div>
{stale}
{note}
{filter_bar}
<div class="pr-kpis">{cards}</div>
{ai_anchor}
<h2>Tiến độ tổng thể</h2><div class="pr-card">{stacked(m['by_status_group'])}</div>
<h2>📈 Biểu đồ</h2>{charts_html}
{cx_section}
{proj_section}
{("<h2>🗺️ Roadmap / Sprint (điều phối)</h2>" + roadmap_html) if roadmap_html else ""}
{okr_html}
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


def _estack(grp):
    """Thanh trạng thái xếp tầng — EMAIL-SAFE (table + bgcolor, render mọi client)."""
    tot = max(grp["todo"] + grp["in_progress"] + grp["done"], 1)
    segs = ""
    for n, c in (("done", EPAL["green"]), ("in_progress", EPAL["blue2"]), ("todo", "#aab6c8")):
        if grp[n]:
            w = max(1, round(100 * grp[n] / tot))
            segs += f'<td width="{w}%" bgcolor="{c}" style="height:18px;font-size:0;line-height:18px">&nbsp;</td>'
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-radius:8px;overflow:hidden"><tr>{segs}</tr></table>'
            f'<div style="font-size:12px;color:{EPAL["mut"]};margin-top:6px">'
            f'<span style="color:{EPAL["green"]}">■</span> Done {grp["done"]} &nbsp;&nbsp;'
            f'<span style="color:{EPAL["blue2"]}">■</span> Đang làm {grp["in_progress"]} &nbsp;&nbsp;'
            f'<span style="color:#7a8aa3">■</span> Chưa làm {grp["todo"]}</div>')


def _ebar(label, value, maxv, color, suffix=""):
    """1 dòng bar ngang — EMAIL-SAFE (table + bgcolor width %)."""
    w = max(2, round(100 * value / (maxv or 1)))
    return (f'<tr><td width="36%" style="padding:3px 8px 3px 0;font-size:12px;color:{EPAL["ink"]};white-space:nowrap">'
            f'{esc(str(label))[:22]}</td>'
            f'<td style="padding:3px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
            f'<td width="{w}%" bgcolor="{color}" style="height:13px;border-radius:4px;font-size:0;line-height:13px">&nbsp;</td>'
            f'<td bgcolor="#eef1f6" style="height:13px;font-size:0;line-height:13px">&nbsp;</td></tr></table></td>'
            f'<td width="46" align="right" style="padding:3px 0 3px 8px;font-size:12px;font-weight:700;color:{EPAL["ink"]}">'
            f'{value}{esc(suffix)}</td></tr>')


_TYPE_LABELS = {"epic": "Epic", "story": "User Story", "user_story": "User Story",
                "task": "Task", "sub-task": "Sub-task", "subtask": "Sub-task",
                "bug": "Bug", "request": "Request", "issue": "Hạng mục công việc"}


def _type_label(t):
    return _TYPE_LABELS.get((t or "issue").lower(), (t or "Issue").title())


def render_email_body(m, vault, banner_url="", okr=None):
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
    od = od or '<li style="margin:3px 0;color:#5b7a4f">Không có hạng mục công việc quá hạn 👍</li>'
    gen = m["generated_at"][:16].replace("T", " ")
    sp = lambda k: 100 * g[k] / tot
    # Phạm vi báo cáo = theo DỰ ÁN (lọc node rỗng 1 lần → dùng cho cả scope + tiering, nhất quán).
    bp = [p for p in m.get("by_project", []) if p.get("project") not in (None, "", "—")]
    scope = f"{len(bp)} dự án" if len(bp) > 1 else (esc(bp[0]["project"]) if bp else "—")
    _sl = m.get("scope_label", "")
    if _sl and not _sl.startswith("Toàn bộ"):
        scope = f"{scope} · {esc(_sl)}"
    # Banner RESPONSIVE bền cho APP MOBILE (Outlook/Gmail app hay bỏ qua `width:100%` trên <img> + giữ
    # width="600" → ảnh không giãn hết width như card). `min-width:100%` ÉP ảnh tối thiểu = bề ngang container
    # (full-width trên mobile, vẫn cap 600px desktop); td width="100%" + font-size:0 khử khoảng trắng.
    banner_row = (f'<tr><td width="100%" align="center" valign="top" '
                  f'style="padding:0;margin:0;font-size:0;line-height:0;mso-line-height-rule:exactly">'
                  f'<img class="kbanner" src="{banner_url}" alt="Cập nhật tiến độ dự án mỗi ngày" width="600" border="0" '
                  f'style="display:block;width:100%;min-width:100%;max-width:600px;height:auto;margin:0 auto;'
                  f'border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic"></td></tr>') if banner_url else ""
    # ── Năng suất & giờ công + lưu ý logtime theo loại ──
    cap = m.get("capacity", {})
    hs = human_seconds
    if cap.get("ot_seconds"):  # dương (vượt) = xanh
        ot_txt = f'<span style="color:{EPAL["green"]}"><b>Vượt kỳ vọng đến hôm nay (OT): +{hs(cap["ot_seconds"])}</b></span>'
    else:                      # âm (thiếu) = đỏ
        ot_txt = f'<span style="color:{EPAL["red"]}"><b>Còn thiếu so với kỳ vọng đến hôm nay: −{hs(cap.get("under_seconds", 0))}</b></span>'
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
        • Ngày làm việc: <b>{cap.get('working_days_elapsed', 0)} / {cap.get('working_days', 0)} ngày</b> đã <b>HOÀN THÀNH</b> trong tháng (T2–T6, 8h/ngày = 1 ngày công) — {'đã tính cả hôm nay (ngày đã hết).' if cap.get('today_counted') else "<b>hôm nay CHƯA tính</b> (chỉ tính sau khi HẾT NGÀY — tránh báo thiếu logtime sai khi ngày chưa xong)."}<br>
        • Kỳ vọng <b>đến hôm nay</b>: <b>{hs(cap.get('team_expected_so_far_s', 0))}</b> ({cap.get('num_members', 0)} TV × {cap.get('working_days_elapsed', 0)} ngày × 8h) · mục tiêu cả tháng: <b>{hs(cap.get('team_std_seconds', 0))}</b>.<br>
        • Đã log: <b>{hs(cap.get('logged_seconds', 0))}</b> = <b>{cap.get('logged_working_days', 0)} ngày công</b> → đạt <b>{cap.get('pct_capacity', 0)}%</b> so với kỳ vọng đến hôm nay.<br>
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
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:center">Hạng mục</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:center">% xong</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:right">Đã log / Ước tính</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:right">Còn lại</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:center">Quá hạn</td>
        </tr>{prows}
      </table>
      <div style="font-size:11.5px;color:{EPAL['mut']};margin-top:6px">Lọc &amp; drill-down chi tiết từng dự án có trong dashboard đính kèm.</div></td></tr>'''
    # 👥 Bảng "Theo người phụ trách" — đưa BÁO CÁO ĐẦY ĐỦ vào THÂN email (đọc ngay, không cần mở file đính kèm)
    asg_full = [a for a in m["by_assignee"] if a["assignee"] not in ("(chưa giao)", "—", "")]
    asg_block = ""
    if asg_full:
        arows = ""
        for a in asg_full:
            is_qc = a.get("role") == "QC"
            is_pm = a.get("role") == "PM"
            pc = a.get("pct_capacity")
            if is_qc or is_pm or pc is None:   # QC & PM không đo bằng giờ-công → "—"
                ns_cell = f'<span style="color:{EPAL["mut"]}">—</span>'
            else:
                pcol = EPAL["green"] if 80 <= pc <= 120 else (EPAL["red"] if pc > 120 else EPAL["amber"])
                ns_cell = f'<span style="color:{pcol};font-weight:700">{pc}%</span>'
            role_cell = (f'<span style="color:{EPAL["amber"]};font-weight:700">QC</span>' if is_qc
                         else f'<span style="color:{EPAL["blue2"]};font-weight:700">PM</span>' if is_pm
                         else f'<span style="color:{EPAL["mut"]}">Dev</span>')
            nbug = a.get("bugs_reported") or 0
            bug_cell = (f'<span style="color:{EPAL["red"]};font-weight:700">{nbug}</span>' if nbug
                        else f'<span style="color:{EPAL["mut"]}">0</span>')
            arows += (
                f'<tr>'
                f'<td style="padding:7px 9px;font-size:13px;color:{EPAL["ink"]};font-weight:700;border-top:1px solid #eef1f6">{esc(a["assignee"])}</td>'
                f'<td style="padding:7px 9px;font-size:12px;text-align:center;border-top:1px solid #eef1f6">{role_cell}</td>'
                f'<td style="padding:7px 9px;font-size:13px;color:#39465c;text-align:center;border-top:1px solid #eef1f6">{a["total"]}</td>'
                f'<td style="padding:7px 9px;font-size:13px;color:{EPAL["green"]};font-weight:700;text-align:center;border-top:1px solid #eef1f6">{a["done"]}</td>'
                f'<td style="padding:7px 9px;font-size:13px;color:{EPAL["blue2"]};text-align:center;border-top:1px solid #eef1f6">{a["in_progress"]}</td>'
                f'<td style="padding:7px 9px;font-size:12.5px;color:#39465c;text-align:right;border-top:1px solid #eef1f6">{hs(a["time"]["spent_s"])} · {a.get("logged_working_days", 0)}đ</td>'
                f'<td style="padding:7px 9px;font-size:13px;text-align:center;border-top:1px solid #eef1f6">{ns_cell}</td>'
                f'<td style="padding:7px 9px;font-size:13px;text-align:center;border-top:1px solid #eef1f6">{bug_cell}</td>'
                f'</tr>')
        asg_block = f'''<tr><td class="kpad" style="padding:8px 22px 2px">
      <div style="font-size:12px;color:{EPAL['mut']};text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">Theo người phụ trách ({len(asg_full)})</div>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e6eaf0;border-radius:10px;overflow:hidden">
        <tr style="background:{EPAL['chip']}">
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-transform:uppercase">Người</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:center">Vai trò</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:center">Hạng mục</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['green']};text-align:center">Done</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['blue2']};text-align:center">Đang làm</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:right">Đã log (giờ·ngày)</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:center">% NS</td>
          <td style="padding:7px 9px;font-size:11px;color:{EPAL['mut']};text-align:center">Bug tạo</td>
        </tr>{arows}
      </table>
      <div style="font-size:11.5px;color:{EPAL['mut']};margin-top:6px">% NS = năng suất Dev so với kỳ vọng ngày-công đến hôm nay (8h/ngày). <b>QC</b> không logtime → đo bằng <b>Bug tạo</b> (—). <b>PM</b> tạo Epic/Request/US → KHÔNG tính giờ-công, không cảnh báo "chưa log".</div></td></tr>'''
    # 🏃 Sprint đang chạy
    spr_block = ""
    if m["active_sprints"]:
        srows = "".join(
            f'<div style="font-size:12.5px;color:#33405a;margin:3px 0;line-height:1.5">▸ <b style="color:{EPAL["ink"]}">{esc(s["name"])}</b> — '
            f'{s["total"]} hạng mục công việc · <b style="color:{EPAL["green"]}">{s["pct_done"]}%</b> xong'
            + (f' · hết hạn <b>{esc(str(s["end"])[:10])}</b>' if s.get("end") else '') + '</div>'
            for s in m["active_sprints"][:5])
        spr_block = (f'<tr><td class="kpad" style="padding:6px 22px 2px">'
                     f'<div style="font-size:12px;color:{EPAL["mut"]};text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px">Sprint đang chạy ({len(m["active_sprints"])})</div>'
                     f'{srows}</td></tr>')
    # 🗺️ ROADMAP block (email) — current/next/backlog cho PM
    roadmap_block = ""
    if m.get("roadmap"):
        _phl = {"current": ("🟢", "Hiện tại"), "next": ("🔵", "Kế tiếp"), "backlog": ("⚪", "Backlog")}
        rrows = "".join(
            f'<tr><td style="padding:5px 8px;font-size:12px;border-top:1px solid #eef1f6">{_phl.get(r["phase"],("",""))[0]} {_phl.get(r["phase"],("",r["phase"]))[1]}</td>'
            f'<td style="padding:5px 8px;font-size:12px;border-top:1px solid #eef1f6"><b>{esc(r["name"])}</b></td>'
            f'<td style="padding:5px 8px;font-size:12px;text-align:center;border-top:1px solid #eef1f6">{r["done"]}/{r["total"]} ({r["pct_done"]}%)</td>'
            f'<td style="padding:5px 8px;font-size:12px;text-align:center;border-top:1px solid #eef1f6">{r["story_points"] or "—"}</td>'
            f'<td style="padding:5px 8px;font-size:12px;text-align:center;border-top:1px solid #eef1f6">{esc(r["end"]) or "—"}</td></tr>'
            for r in m["roadmap"][:12])
        roadmap_block = (
            f'<tr><td class="kpad" style="padding:8px 22px 2px">'
            f'<div style="font-size:12px;color:{EPAL["mut"]};text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">🗺️ Roadmap / Sprint (điều phối)</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e6eaf0;border-radius:10px;overflow:hidden">'
            f'<tr style="background:{EPAL["chip"]}"><td style="padding:6px 8px;font-size:11px;color:{EPAL["mut"]}">Giai đoạn</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{EPAL["mut"]}">Sprint</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{EPAL["mut"]};text-align:center">Done</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{EPAL["mut"]};text-align:center">SP</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{EPAL["mut"]};text-align:center">Kết thúc</td></tr>{rrows}</table></td></tr>')
    # 📋 OKR / Standing-Meeting block (email) — section RIÊNG cho file chiến lược (không phải task)
    okr_block = render_okr_email(okr)
    # 📊 Biểu đồ EMAIL-SAFE (table + bgcolor) — render mọi client, không SVG/JS
    asg = [a for a in m["by_assignee"] if a["assignee"] not in ("(chưa giao)", "—", "")][:6]
    asg_max = max((a["total"] for a in asg), default=1)
    asg_rows = "".join(_ebar(a["assignee"], a["total"], asg_max, EPAL["blue2"]) for a in asg) or \
        f'<tr><td style="font-size:12px;color:{EPAL["mut"]}">(chưa giao việc)</td></tr>'
    proj_chart = ""
    if len(bp) > 1:
        pmax = max((p["total"] for p in bp), default=1)
        prows = "".join(_ebar(p["project"], p["total"], pmax, EPAL["vio"])
                        for p in sorted(bp, key=lambda z: -z["total"])[:6])
        proj_chart = (f'<div style="font-size:11.5px;color:{EPAL["mut"]};text-transform:uppercase;letter-spacing:.04em;margin:14px 0 4px">Khối lượng theo dự án</div>'
                      f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{prows}</table>')
    charts_block = (f'<tr><td class="kpad kcard" bgcolor="{EPAL["card"]}" style="padding:8px 22px 4px;background-color:{EPAL["card"]}">'
                    f'<div style="font-size:11.5px;color:{EPAL["mut"]};text-transform:uppercase;letter-spacing:.04em;margin:4px 0 8px">📊 Phân bố trạng thái</div>'
                    f'{_estack(g)}'
                    f'<div style="font-size:11.5px;color:{EPAL["mut"]};text-transform:uppercase;letter-spacing:.04em;margin:14px 0 4px">Khối lượng theo người</div>'
                    f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{asg_rows}</table>'
                    f'{proj_chart}</td></tr>')
    # 🧩 ĐỘ PHỨC TẠP — TRỌNG TÂM (card tím nổi bật): KPI + phân bố điểm + bảng hạng mục phức tạp cao (≥ngưỡng)
    cx = m.get("complexity", {})
    cx_block = ""
    if cx.get("field_present"):
        thr = cx.get("high_threshold", 7)
        dist = cx.get("dist", {})
        dmax = max(dist.values()) if dist else 1
        bars = "".join(_ebar(f"Điểm {k}", v, dmax, (EPAL["red"] if int(k) >= thr else EPAL["blue2"]), suffix=" hạng mục")
                       for k, v in sorted(dist.items(), key=lambda kv: -int(kv[0])))
        hrows = ""
        for x in cx.get("high", [])[:15]:
            hrows += (f'<tr>'
                      f'<td style="padding:6px 9px;font-size:12.5px;font-weight:700;color:{EPAL["ink"]};border-top:1px solid #ece7f8">{esc(x["key"])}</td>'
                      f'<td style="padding:6px 9px;font-size:12px;color:#39465c;border-top:1px solid #ece7f8">{esc((x["summary"] or "")[:54])}</td>'
                      f'<td style="padding:6px 9px;font-size:13px;font-weight:800;color:#fff;background-color:{EPAL["red"]};text-align:center;border-top:1px solid #ece7f8">{x["complexity"]}</td>'
                      f'<td style="padding:6px 9px;font-size:12px;color:#39465c;border-top:1px solid #ece7f8">{esc(x["assignee"])}</td>'
                      f'<td style="padding:6px 9px;font-size:12px;color:#39465c;border-top:1px solid #ece7f8">{esc(x["status"])}</td>'
                      f'</tr>')
        htable = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e0d8f3;border-radius:10px;overflow:hidden;margin-top:8px">'
                  f'<tr style="background:#efe9fb"><td style="padding:6px 9px;font-size:11px;color:#5a32a3">Hạng mục</td>'
                  f'<td style="padding:6px 9px;font-size:11px;color:#5a32a3">Tóm tắt</td>'
                  f'<td style="padding:6px 9px;font-size:11px;color:#5a32a3;text-align:center">Điểm</td>'
                  f'<td style="padding:6px 9px;font-size:11px;color:#5a32a3">Người</td>'
                  f'<td style="padding:6px 9px;font-size:11px;color:#5a32a3">Trạng thái</td></tr>{hrows}</table>'
                  if hrows else f'<div style="font-size:12.5px;color:{EPAL["mut"]};margin-top:6px">Không có hạng mục công việc nào ≥ {thr} (phức tạp cao).</div>')
        cx_block = (
            f'<tr><td class="kpad" style="padding:10px 22px 2px">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#f6f3fe" style="background-color:#f6f3fe;border:1.5px solid #cdbff0;border-left:5px solid #6b46c1;border-radius:10px">'
            f'<tr><td style="padding:12px 15px">'
            f'<div style="font-size:13.5px;font-weight:800;color:#553399">🧩 ĐỘ PHỨC TẠP (Complexity) — TRỌNG TÂM</div>'
            f'<div style="font-size:12.5px;color:#5a4b78;margin:4px 0 8px">'
            f'<b style="color:{EPAL["red"]};font-size:15px">{cx.get("high_count", 0)}</b> hạng mục PHỨC TẠP CAO (điểm ≥ {thr}) '
            f'/ {cx.get("total_scored", 0)} hạng mục công việc có điểm · cao nhất <b>{cx.get("max", 0)}</b>. '
            f'<i>Số càng lớn càng phức tạp — ưu tiên nguồn lực &amp; review cho nhóm điểm cao.</i></div>'
            f'<div style="font-size:11px;color:#7a6a9a;text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px">Phân bố điểm (đỏ = ≥{thr})</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{bars}</table>'
            f'{htable}</td></tr></table></td></tr>')
    return f"""<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only"><meta name="supported-color-schemes" content="light only">
<style>
:root{{color-scheme:light only;supported-color-schemes:light only}}
@media only screen and (max-width:600px){{.kc{{display:block!important;width:100%!important;box-sizing:border-box}}.kpad{{padding:16px!important}}.kbody{{padding-left:0!important;padding-right:0!important}}.kcard{{border-radius:0!important}}.kbanner{{width:100%!important;min-width:100%!important;max-width:100%!important;height:auto!important}}}}
@media (prefers-color-scheme:dark){{
  .kbody,.kbody td,.kbody div,.kbody span,.kbody b,.kbody li,.kbody strong{{color:{EPAL['ink']}!important}}
  .kcard{{background:#ffffff!important;background-color:#ffffff!important}}
  .kfoot,.kfoot div{{color:#ffffff!important}}
}}
</style>
<table role="presentation" class="kbody" width="100%" cellpadding="0" cellspacing="0" bgcolor="{EPAL['bg']}" style="background:{EPAL['bg']};background-color:{EPAL['bg']};padding:16px 8px;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif">
<tr><td align="center"><table role="presentation" class="kcard" width="600" cellpadding="0" cellspacing="0" bgcolor="#ffffff" style="max-width:600px;width:100%;background:#ffffff;background-color:#ffffff;border-radius:14px;overflow:hidden">
  {banner_row}
  <tr><td class="kpad" style="padding:18px 22px 2px">
    <span style="display:inline-block;background:{EPAL['cream']};border:1px solid {EPAL['creambd']};color:#b45309;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;padding:6px 13px;border-radius:999px">⏱️ Cập nhật tiến độ · {scope}</span></td></tr>
  <tr><td class="kpad" style="padding:10px 22px 0">
    <div style="font-size:15px;color:{EPAL['ink']};font-weight:700;font-style:italic">Kính gửi Anh/Chị,</div>
    <div style="font-size:13.5px;color:#33405a;line-height:1.7;margin-top:6px">Trợ lý <b>Claude AI</b> – FPT Telecom xin cập nhật <b>tiến độ dự án</b> ({scope}) tới <b>{esc(gen)}</b> (UTC) như sau:</div></td></tr>
  <tr><td class="kpad" style="padding:12px 22px 2px">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#fff3e0" style="background-color:#fff3e0;border:1.5px solid #ffb74d;border-left:5px solid #f57c00;border-radius:10px">
      <tr><td style="padding:12px 15px">
        <div style="font-size:13.5px;color:#9a3b00;font-weight:800;line-height:1.5">📎 Mở FILE ĐÍNH KÈM để xem DASHBOARD CHI TIẾT</div>
        <div style="font-size:12.5px;color:#8a4b00;line-height:1.6;margin-top:3px">Email này là bản TÓM TẮT. Nhấn mở <b>file HTML đính kèm</b> để xem <b>dashboard tương tác</b>: lọc theo <b>project / người phụ trách</b>, biểu đồ & drill-down từng hạng mục công việc · sprint.</div>
      </td></tr>
    </table></td></tr>
  <tr><td class="kpad" style="padding:14px 17px 2px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
    {_ecard("Tổng số hạng mục", m['total'], "hạng mục")}{_ecard("Đã hoàn thành", g['done'], "hạng mục")}{_ecard("Còn lại", m['total'] - g['done'], "hạng mục", True)}
  </tr></table></td></tr>
  <tr><td class="kpad" style="padding:8px 22px">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e9edf3;border-radius:999px;overflow:hidden"><tr style="height:12px">
      <td width="{sp('done'):.0f}%" bgcolor="{EPAL['green']}"></td><td bgcolor="#e9edf3"></td></tr></table>
    <table role="presentation" width="100%" style="margin-top:7px"><tr>
      <td style="font-size:12.5px;color:{EPAL['mut']}">Tiến độ hoàn thành</td>
      <td style="font-size:12.5px;text-align:right;color:#39465c"><b style="color:{EPAL['green']}">{m['pct_done']}%</b> · còn lại {m['total'] - g['done']} hạng mục công việc · <span style="color:{EPAL['amber']}">đang làm {g['in_progress']}</span></td>
    </tr></table></td></tr>
  {cx_block}
  {charts_block}
  {proj_block}
  {asg_block}
  {roadmap_block}
  {okr_block}
  {spr_block}
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
    <div style="font-size:13px;color:#33405a;line-height:1.7">Để xem chi tiết từng hạng mục công việc / sprint / thành viên (có bộ lọc), vui lòng mở <b>Dashboard đính kèm</b>. Mọi thông tin cần hỗ trợ, vui lòng liên hệ đầu mối bên dưới.</div>
    <div style="font-size:13.5px;color:{EPAL['ink']};font-weight:700;margin-top:10px">Trân trọng!</div></td></tr>
  <tr><td class="kfoot" bgcolor="#0b2a5e" style="background:linear-gradient(135deg,#0b2a5e,#15428f);background-color:#0b2a5e;padding:16px 22px;text-align:center">
    <div style="color:#ffffff;font-size:13px;font-weight:700">Claude AI · Trợ lý tiến độ dự án — FPT Telecom</div>
    <div style="color:#a9c2ee;font-size:11.5px;margin-top:4px">Báo cáo tạo tự động mỗi ngày · Dữ liệu cập nhật {esc(gen)} (UTC)</div></td></tr>
</table></td></tr></table>"""


# ─────────────────────── Phân tích AI → CARD MÀU + BẢNG (email-safe) ───────────────────────
# Mỗi mục phân tích = 1 CARD có màu riêng (viền + nền nhạt + tiêu đề đậm) thay cho chip inline → dễ quan sát.
_AI_THEMES = {
    "red":    {"bd": "#d23b3b", "bg": "#fdeceb", "hd": "#a52217", "ic": "🔴"},
    "amber":  {"bd": "#e0900a", "bg": "#fff6e3", "hd": "#945c00", "ic": "🟡"},
    "green":  {"bd": "#1fa463", "bg": "#e8f8f0", "hd": "#137045", "ic": "🟢"},
    "blue":   {"bd": "#2f6fe0", "bg": "#eaf1fd", "hd": "#1b4aa0", "ic": "👥"},
    "violet": {"bd": "#7c4dd6", "bg": "#f1ebfb", "hd": "#5a32a3", "ic": "📅"},
    "teal":   {"bd": "#0ea5b5", "bg": "#e4f6f8", "hd": "#0a6f7a", "ic": "🎯"},
    "slate":  {"bd": "#5a6b86", "bg": "#eef2f7", "hd": "#33405a", "ic": "📌"},
}


def _ai_theme(title):
    t = title.lower()
    if "🔴" in title:
        return "red"
    if "🟡" in title:
        return "amber"
    if "🟢" in title:
        return "green"
    pairs = [
        ("red", ("rủi ro cao", "nghiêm trọng", "blocker", "critical", "khẩn", "sự cố")),
        ("amber", ("rủi ro vừa", "rủi ro trung", "cảnh báo", "warning", "theo dõi", "lưu ý")),
        ("green", ("tích cực", "điểm sáng", "thuận lợi", "positive", "tốt", "đạt")),
        ("blue", ("thành viên", "nhân sự", "workload", "phân bổ", "tải", "theo người")),
        ("violet", ("dự đoán", "sprint", "timeline", "forecast", "dự báo")),
        ("teal", ("hành động", "đề xuất", "khuyến nghị", "action", "ưu tiên", "next step")),
        ("slate", ("tóm tắt", "điều hành", "tổng kết", "summary", "kết luận")),
    ]
    for theme, kws in pairs:
        if any(k in t for k in kws):
            return theme
    return "slate"


def _status_tint(text):
    t = (text or "").lower()
    if any(k in t for k in ("done", "hoàn thành", "resolve", "closed", "xong")):
        return "#1fa463"
    if "review" in t:
        return "#2f6fe0"
    if any(k in t for k in ("progress", "đang làm", "doing", "wip")):
        return "#e0900a"
    if "test" in t:
        return "#7c4dd6"
    if any(k in t for k in ("todo", "to do", "chưa", "backlog", "open", "mở")):
        return "#8a96a8"
    return ""


def _ai_inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s


def _render_md_table(rows, theme):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [c for c in cells if "".join(c).replace("-", "").replace(":", "").strip()]  # bỏ dòng phân cách |---|
    if not cells:
        return ""
    head, body = cells[0], cells[1:]
    th = "".join(
        f'<th style="padding:6px 9px;text-align:left;font-size:11.5px;font-weight:800;color:#ffffff;'
        f'background:{_status_tint(h) or _AI_THEMES[theme]["bd"]};border:1px solid #ffffff">{_ai_inline(h)}</th>'
        for h in head)
    trs = ""
    for ri, row in enumerate(body):
        bg = "#ffffff" if ri % 2 == 0 else "#f4f7fb"
        tds = "".join(
            f'<td style="padding:5px 9px;font-size:12px;color:{EPAL["ink"]};background-color:{bg};'
            f'border:1px solid #e3e9f1">{_ai_inline(c)}</td>' for c in row)
        trs += f"<tr>{tds}</tr>"
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;margin:7px 0">'
            f'<thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>')


def _ai_body(lines, theme):
    out, ul, tbl = [], [], []

    def flush_ul():
        if ul:
            out.append('<ul style="margin:4px 0 5px;padding-left:18px">' + "".join(ul) + "</ul>")
            ul.clear()

    def flush_tbl():
        if tbl:
            flush_ul()
            out.append(_render_md_table(list(tbl), theme))
            tbl.clear()

    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("|"):
            flush_ul()
            tbl.append(s)
            continue
        flush_tbl()
        if s.startswith("###"):
            flush_ul()
            out.append(f'<div style="font-weight:700;color:{EPAL["ink"]};font-size:12.5px;margin:8px 0 2px">'
                       f'{_ai_inline(s.lstrip("# "))}</div>')
        elif s[:2] in ("- ", "* ") or s.startswith("•") or re.match(r"^\d+[.)]\s", s):
            txt = re.sub(r"^(\d+[.)]|[-*•])\s*", "", s)
            ul.append(f'<li style="margin:3px 0;font-size:12.5px;color:#33405a;line-height:1.55">{_ai_inline(txt)}</li>')
        else:
            flush_ul()
            out.append(f'<div style="margin:4px 0;font-size:12.5px;color:#33405a;line-height:1.55">{_ai_inline(s)}</div>')
    flush_tbl()
    flush_ul()
    return "".join(out)


def _ai_card(title, body_html, theme):
    th = _AI_THEMES[theme]
    disp = re.sub(r"^[🔴🟡🟢👥📅🎯📌•\-\s]+", "", title).strip() or title
    return (f'<div style="border-left:4px solid {th["bd"]};background-color:{th["bg"]};border-radius:8px;'
            f'padding:11px 14px;margin:10px 0">'
            f'<div style="font-weight:800;color:{th["hd"]};font-size:13.5px;margin-bottom:5px">{th["ic"]} {esc(disp)}</div>'
            f'{body_html or ""}</div>')


def render_ai_cards(md):
    """Markdown phân tích AI → CHUỖI card màu theo mục + bảng (email-safe). Thay cho chip inline."""
    md = (md or "").strip()
    if not md:
        return '<div style="color:#7a8aa3;font-size:12.5px">Chưa có phân tích AI cho kỳ này.</div>'
    cards, intro, cur_title, cur_lines = [], [], None, []

    def flush():
        nonlocal cur_title, cur_lines
        if cur_title is not None:
            theme = _ai_theme(cur_title)
            cards.append(_ai_card(cur_title, _ai_body(cur_lines, theme), theme))
        cur_title, cur_lines = None, []

    for ln in md.splitlines():
        s = ln.strip()
        is_hdr = bool(re.match(r"^#{1,2}\s", s)) or \
            (s.startswith("**") and s.endswith("**") and 3 < len(s) < 56 and s.count("**") == 2)
        if is_hdr:
            flush()
            cur_title = re.sub(r"^#+\s*", "", s).strip().strip("*").strip()
            cur_lines = []
        elif cur_title is None:
            if s:
                intro.append(s)
        else:
            cur_lines.append(ln)
    flush()
    intro_html = "".join(
        f'<div style="margin:4px 0;font-size:12.5px;color:#33405a;line-height:1.55">{_ai_inline(x)}</div>'
        for x in intro)
    return intro_html + "".join(cards)


def inject_ai_into_email(out_dir, md_path):
    """Đọc file markdown AI → render card màu → thay khối <!--KR-AI--> trong CẢ BA file -latest:
    email-body (gửi) · email-preview (xem trước, banner base64) · progress-report (dashboard #kr-ai) —
    để phân tích AI LUÔN có ở CẢ email LẪN dashboard."""
    os.makedirs(out_dir, exist_ok=True)   # phòng thủ: không chết vì thiếu thư mục
    email = os.path.join(out_dir, "email-body-latest.html")
    if not os.path.exists(email):
        die(f"Không thấy {email} — hãy chạy build_report (sinh email) trước khi --inject-ai.")
    md = open(md_path, encoding="utf-8").read() if os.path.exists(md_path) else md_path
    block = render_ai_cards(md)
    done = []
    for fp in (email,
               os.path.join(out_dir, "email-preview-latest.html"),
               os.path.join(out_dir, "progress-report-latest.html")):
        if not os.path.exists(fp):
            continue
        txt = open(fp, encoding="utf-8").read()
        new_txt, n = re.subn(r"<!--KR-AI-START-->.*?<!--KR-AI-END-->",
                             lambda _m: "<!--KR-AI-START-->" + block + "<!--KR-AI-END-->", txt, count=1, flags=re.DOTALL)
        if n:
            open(fp, "w", encoding="utf-8").write(new_txt)
            done.append(os.path.basename(fp))
    print(f"Đã chèn phân tích AI (card màu) vào: {', '.join(done)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", help="Đường dẫn vault (mặc định đọc config/factory-config.yaml)")
    ap.add_argument("--out", help="Thư mục xuất (mặc định reports/)")
    ap.add_argument("--projects", default="", help="Lọc báo cáo theo project key, cách nhau phẩy "
                    "(vd PROJ1,PROJ2). Rỗng = tất cả project trong vault.")
    ap.add_argument("--source-ids", dest="source_ids", default="", help="Lọc báo cáo theo NGUỒN, cách nhau phẩy. "
                    "Mỗi token là 'jira' (mọi note source:jira) HOẶC một source_id của lần import Excel/SharePoint "
                    "(vd local_kehoach,sp_standup). Rỗng = mọi nguồn. Dùng để báo cáo CHỈ nguồn user đã chọn.")
    ap.add_argument("--inject-ai", dest="inject_ai", help="Chèn file markdown phân tích AI (CARD MÀU) vào "
                    "email-body-latest.html (trong --out) rồi thoát. KHÔNG build lại report.")
    ap.add_argument("--scope", default="all", choices=["all", "sprint", "recent"],
                    help="Phạm vi báo cáo (dự án lớn): sprint = sprint đang chạy (fallback N ngày) · "
                         "recent = updated trong N ngày · all = toàn bộ (mặc định).")
    ap.add_argument("--recent-days", dest="recent_days", type=int, default=30,
                    help="Số ngày N cho --scope recent / fallback của sprint (mặc định 30).")
    ap.add_argument("--complexity-high", dest="complexity_high", type=int, default=7,
                    help="Ngưỡng 'phức tạp cao' cho field Complexity (mặc định 7 — >= ngưỡng = cao).")
    ap.add_argument("--report-type", dest="report_type", default="progress",
                    choices=["progress", "invoice", "meeting-roadmap", "custom"],
                    help="Loại report: progress (Jira, mặc định) | invoice (hoá đơn) | meeting-roadmap (Pha 4) | custom (template).")
    ap.add_argument("--template", help="Tên template trong templates/reports/_index.json "
                    "(bắt buộc cho --report-type custom; tuỳ chọn cho invoice).")
    ap.add_argument("--meetings", help="File JSON biên bản họp đã AI-tóm-tắt (cho --report-type meeting-roadmap; "
                    "mặc định reports/_meeting-rows.json).")
    args = ap.parse_args()
    DATA = data_root()   # project (cwd) nếu có config/factory-config.yaml; else REPO_ROOT (dev / lịch nền)

    if args.inject_ai:  # chỉ chèn phân tích AI vào email đã build → thoát
        inject_ai_into_email(args.out or os.path.join(DATA, "reports"), args.inject_ai)
        return

    vault = args.vault
    smap = None
    cfg_path = os.path.join(DATA, "config", "factory-config.yaml")
    qc_members = []   # reports.qc_members: ép vai trò QC (không đo giờ-công). Else auto theo reporter-của-Bug + 0 logtime.
    pm_members = []   # reports.pm_members: ép vai trò PM (không đo giờ-công). Else auto theo reporter-của-Epic/Request/US + 0 logtime.
    if os.path.exists(cfg_path):
        cfg = open(cfg_path, encoding="utf-8").read()
        if not vault:
            mm = re.search(r"^\s*vault_path:\s*(.+)$", cfg, re.M)
            if mm:
                vault = mm.group(1).strip().strip('"').strip("'")
        qm = re.search(r"^\s*qc_members:\s*\[([^\]]*)\]", cfg, re.M)   # inline list ["A","B"] (như to:/recipients:)
        if qm:
            qc_members = [x.strip().strip('"').strip("'") for x in qm.group(1).split(",") if x.strip()]
        pmm = re.search(r"^\s*pm_members:\s*\[([^\]]*)\]", cfg, re.M)   # inline list ["A","B"]
        if pmm:
            pm_members = [x.strip().strip('"').strip("'") for x in pmm.group(1).split(",") if x.strip()]
    if not vault:
        die("Không tìm thấy vault. Truyền --vault <path> hoặc đặt vault_path trong config/factory-config.yaml.")
    if not os.path.isabs(vault):
        vault = os.path.normpath(os.path.join(DATA, vault))
    if not os.path.isdir(vault):
        die(f"Vault không tồn tại: {vault}")

    # ── DISPATCH theo --report-type (nhánh KHÔNG-Jira: invoice/custom/meeting-roadmap) ──
    rtype = getattr(args, "report_type", "progress")
    if rtype != "progress":
        out_dir = args.out or os.path.join(DATA, "reports")
        os.makedirs(out_dir, exist_ok=True)
        if rtype == "meeting-roadmap":
            meetings = load_meeting_rows(args.meetings or os.path.join(DATA, "reports", "_meeting-rows.json"))
            if not meetings:
                die("Không có biên bản họp. Tạo reports/_meeting-rows.json (AI tóm tắt từ file họp) hoặc truyền "
                    "--meetings <file>, rồi (tùy chọn) import_meeting.py để lưu vault.")
            mr_issues = load_issues(vault)
            html_out = render_meeting_roadmap(meetings, mr_issues, "Báo cáo Meeting & Roadmap")
            stamp = datetime.now().strftime("%Y%m%d-%H%M")
            latest = os.path.join(out_dir, "meeting-roadmap-latest.html")
            open(latest, "w", encoding="utf-8").write(html_out)
            open(os.path.join(out_dir, f"meeting-roadmap-{stamp}.html"), "w", encoding="utf-8").write(html_out)
            print(f"✓ Report (meeting-roadmap): {latest}")
            print(f"  {len(meetings)} cuộc họp | {len(mr_issues)} task Jira trong vault")
            return
        invs = load_invoices(vault)
        sid = (args.source_ids or "").strip()
        if sid and sid.lower() not in ("all", "*"):
            ids = {s.strip() for s in sid.split(",") if s.strip()}
            invs = [v for v in invs if v.get("source_id") in ids or "invoice" in ids]
        if not invs:
            die("Không có note hoá đơn (source: invoice) trong vault. "
                "Chạy tools/invoice-report/import_invoice.py trước, hoặc kiểm --source-ids.")
        tmpl_html, title = None, "Báo cáo chi phí — Hoá đơn"
        if rtype == "custom" and not args.template:
            die("report-type custom cần --template <name>. Liệt kê trong templates/reports/_index.json.")
        if args.template:
            tmpl_html, _base, ttl = load_report_template(args.template, DATA)
            if ttl:
                title = ttl
        html_out = render_invoice_report(invs, title, tmpl_html)
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        latest = os.path.join(out_dir, "invoice-report-latest.html")
        open(latest, "w", encoding="utf-8").write(html_out)
        open(os.path.join(out_dir, f"invoice-report-{stamp}.html"), "w", encoding="utf-8").write(html_out)
        tot = sum(float(v.get("total") or 0) for v in invs)
        print(f"✓ Report ({rtype}{'/'+args.template if args.template else ''}): {latest}")
        print(f"  {len(invs)} hoá đơn | TỔNG {_vnd(tot)}")
        return

    issues = load_issues(vault)
    # ── CỔNG CHẶN NGUỒN: vault có >1 nguồn mà KHÔNG chỉ định --source-ids → TỪ CHỐI build ──
    # Biến "skip im lặng câu hỏi chọn nguồn → build sai/lẫn nguồn" thành DỪNG + buộc đi hỏi user.
    # `--source-ids all|*` = mọi nguồn (cho lịch nền). Vault 1 nguồn → không chặn (tương thích ngược).
    available_sources = set()
    for _i in issues:
        _src = (_i.get("source") or "jira")
        if _src == "jira":
            available_sources.add(_i.get("source_id") or "jira")   # tách Jira THEO INSTANCE khi note có source_id; else token "jira"
        else:
            available_sources.add(_i.get("source_id") or "excel")
    sid_raw = (args.source_ids or "").strip()
    if sid_raw.lower() in ("all", "*"):
        sid_raw = ""   # all = mọi nguồn → bỏ lọc (đã chủ ý chọn tất cả)
    elif not sid_raw and len(available_sources) > 1:
        die("❌ Vault có NHIỀU NGUỒN: " + ", ".join(sorted(available_sources)) + ".\n"
            "   PHẢI truyền --source-ids để báo cáo CHỈ gồm nguồn user đã chọn — vd:\n"
            "     --source-ids jira              (MỌI instance Jira — wildcard)\n"
            "     --source-ids jira__foxproject  (CHỈ 1 instance Jira theo source_id)\n"
            "     --source-ids jira,sp_standup   (Jira + 1 import SharePoint)\n"
            "     --source-ids all               (tất cả nguồn)\n"
            "   ⛔ KHÔNG build report khi CHƯA hỏi user chọn nguồn: chạy /claude-knowledge-daily-report bước 2 "
            "(AskUserQuestion 3 nhóm [Jira·SharePoint·Local Excel]) TRƯỚC, rồi truyền --source-ids tương ứng.")
    if sid_raw:
        ids = {s.strip() for s in sid_raw.split(",") if s.strip()}
        issues = [i for i in issues
                  if (i.get("source") or "jira") in ids or (i.get("source_id") or "") in ids]
        if not issues:
            die(f"Không có note nào khớp nguồn {sorted(ids)} trong vault {vault}.\n"
                f"   → Kiểm tra: 'jira' cho note Jira; đúng --source-id của lần import Excel/SharePoint. "
                f"Hãy quét/import nguồn đó trước rồi báo cáo lại.")
    if args.projects:
        keys = {k.strip() for k in args.projects.split(",") if k.strip()}
        issues = [i for i in issues if (i.get("project") or "") in keys]
        if not issues:
            die(f"Không có note Jira cho project {sorted(keys)} trong vault {vault}.\n"
                f"   → Project này có thể thuộc một NGUỒN Jira đã kết nối nhưng CHƯA ĐƯỢC QUÉT (vd nguồn MCP/Cloud, "
                f"hoặc một domain Jira khác). Mở /claude-knowledge-daily-report → chọn ĐÚNG nguồn chứa project này (multi-select nếu "
                f"nhiều nguồn) rồi quét lại — KHÔNG phải mất dữ liệu.")
    if not issues:
        die(f"Vault chưa có note Jira nào (source: jira) tại {vault}. Hãy 'quét jira' trước.")

    issues, scope_label = apply_scope(issues, args.scope, args.recent_days)
    if args.scope != "all":
        print(f"ℹ️  Phạm vi báo cáo: {scope_label} ({len(issues)} issue).")

    today = datetime.now().strftime("%Y-%m-%d")
    m = compute(issues, smap, today, complexity_high=args.complexity_high, qc_members=qc_members, pm_members=pm_members)
    m["scope_label"] = scope_label
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
        banner_url = "https://raw.githubusercontent.com/isc-fkit/Kora-Framework/main/assets/banner-daily-report.jpg"

    out = args.out or os.path.join(DATA, "reports")
    os.makedirs(out, exist_ok=True)
    okr = load_okr_blocks(out)   # section RIÊNG cho file OKR/Standing-Meeting (Claude lập reports/_okr-blocks.json); None → bỏ qua
    fragment = render_fragment(m, vault, okr)

    now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y-%m-%d_%H%M")            # NGÀY-GIỜ tạo → gắn vào tên file (mỗi lần chạy 1 bản riêng)
    fragment_html = standalone(fragment)
    ebody = render_email_body(m, vault, banner_url, okr)   # email body (mobile) — Claude điền AI giữa <!--KR-AI-->
    data_json = json.dumps(m, ensure_ascii=False, indent=2)
    # 1) LỊCH SỬ THEO NGÀY — reports/<YYYY-MM-DD>/<file>-<ngày-giờ>.html (không ghi đè; nhiều lần/ngày = nhiều bản)
    day_dir = os.path.join(out, day)
    os.makedirs(day_dir, exist_ok=True)
    report_dated = os.path.join(day_dir, f"progress-report-{stamp}.html")
    open(report_dated, "w", encoding="utf-8").write(fragment_html)
    open(os.path.join(day_dir, f"email-body-{stamp}.html"), "w", encoding="utf-8").write(ebody)
    open(os.path.join(day_dir, f"progress-data-{stamp}.json"), "w", encoding="utf-8").write(data_json)
    # 2) Bản -latest ở GỐC (mailer/orchestrator dùng) + progress-data-{day}.json ở gốc (orchestrator AI đọc)
    latest_p = os.path.join(out, "progress-report-latest.html")
    ebody_latest = os.path.join(out, "email-body-latest.html")
    json_p = os.path.join(out, f"progress-data-{day}.json")
    open(latest_p, "w", encoding="utf-8").write(fragment_html)
    open(ebody_latest, "w", encoding="utf-8").write(ebody)
    open(json_p, "w", encoding="utf-8").write(data_json)

    # 3) PREVIEW EMAIL — bản XEM TRƯỚC mail (Cowork/trình duyệt): banner nhúng BASE64 để hiện được tại chỗ
    #    (email-body-latest.html dùng URL remote cho send_report swap→CID; trình duyệt có thể chặn URL đó).
    #    KHÔNG dùng cho gửi mail (Gmail/Outlook chặn data: URI) — chỉ để preview.
    banner_data_uri = banner_url
    asset = os.path.join(REPO_ROOT, "assets", "banner-daily-report.jpg")
    try:
        if os.path.exists(asset):
            b64 = base64.b64encode(open(asset, "rb").read()).decode("ascii")
            banner_data_uri = f"data:image/jpeg;base64,{b64}"
    except Exception:
        pass
    epreview = render_email_body(m, vault, banner_data_uri, okr)
    epreview_latest = os.path.join(out, "email-preview-latest.html")
    open(epreview_latest, "w", encoding="utf-8").write(epreview)
    open(os.path.join(day_dir, f"email-preview-{stamp}.html"), "w", encoding="utf-8").write(epreview)

    print(f"Report tiến độ đã tạo từ {len(issues)} issue.")
    print(f"  - Bản lịch sử (ngày-giờ): {report_dated}")
    print(f"  - Email body (gửi mail): {ebody_latest}")
    print(f"  - Email PREVIEW (xem trước, banner base64): {epreview_latest}")
    print(f"  - Dashboard mới nhất: {latest_p}")
    print(f"  - Dữ liệu (UI Cowork inline): {json_p}")
    print(f"Tổng: {m['total']} hạng mục công việc · {m['pct_done']}% done · "
          f"{len(m['active_sprints'])} sprint active · log {human_seconds(m['time']['spent_s'])}/"
          f"{human_seconds(m['time']['estimate_s'])}")


if __name__ == "__main__":
    main()
