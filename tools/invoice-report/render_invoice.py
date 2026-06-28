#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_invoice.py — Report HOÁ ĐƠN / KẾ TOÁN (PoC Pha 1).
Đọc rows đã chuẩn hoá (JSON/CSV từ bước OCR ảnh hoá đơn) → tổng hợp → HTML report.

   python3 tools/invoice-report/render_invoice.py \
       --rows reports/_invoice-rows.json --out reports/invoice-report-latest.html \
       --title "Báo cáo chi phí Quý 2/2026"

Stdlib-only. Pha 2 sẽ gộp thành build_report.py --report-type invoice.
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict


def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(2)


def load_rows(path):
    if not os.path.exists(path):
        die(f"Không thấy file rows: {path}")
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
    else:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    norm = []
    for r in rows:
        norm.append({
            "invoice_no": str(r.get("invoice_no") or r.get("no") or "").strip(),
            "date": str(r.get("date") or "").strip(),
            "vendor": str(r.get("vendor") or "").strip(),
            "category": str(r.get("category") or "Khác").strip(),
            "currency": str(r.get("currency") or "VND").strip(),
            "subtotal": float(r.get("subtotal") or 0),
            "vat": float(r.get("vat") or 0),
            "total": float(r.get("total") or 0),
            "items": str(r.get("items") or "").strip(),
        })
    if not norm:
        die("File rows rỗng.")
    return norm


def vnd(n):
    return f"{n:,.0f}".replace(",", ".") + " ₫"


def bars_svg(pairs, width=520, bar_h=26, gap=12):
    """pairs: list[(label, value)] → SVG cột ngang."""
    if not pairs:
        return ""
    mx = max(v for _, v in pairs) or 1
    h = len(pairs) * (bar_h + gap) + gap
    out = [f'<svg viewBox="0 0 {width} {h}" width="100%" height="{h}" '
           f'xmlns="http://www.w3.org/2000/svg" role="img">']
    y = gap
    palette = ["#2b50c2", "#2e9e8f", "#c2772b", "#8a4fc2", "#c23b5e", "#3b8ac2"]
    for i, (label, val) in enumerate(pairs):
        bw = max(2, int((width - 230) * (val / mx)))
        c = palette[i % len(palette)]
        out.append(f'<text x="0" y="{y+bar_h*0.7}" font-size="13" fill="#333">{esc(label)[:26]}</text>')
        out.append(f'<rect x="170" y="{y}" width="{bw}" height="{bar_h}" rx="4" fill="{c}"/>')
        out.append(f'<text x="{170+bw+6}" y="{y+bar_h*0.7}" font-size="12" fill="#555">{vnd(val)}</text>')
        y += bar_h + gap
    out.append("</svg>")
    return "".join(out)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default="reports/_invoice-rows.json")
    ap.add_argument("--out", default="reports/invoice-report-latest.html")
    ap.add_argument("--title", default="Báo cáo chi phí — Hoá đơn")
    args = ap.parse_args()

    rows = load_rows(args.rows)
    n = len(rows)
    sum_sub = sum(r["subtotal"] for r in rows)
    sum_vat = sum(r["vat"] for r in rows)
    sum_total = sum(r["total"] for r in rows)

    by_cat = defaultdict(float)
    by_vendor = defaultdict(float)
    by_month = defaultdict(float)
    for r in rows:
        by_cat[r["category"]] += r["total"]
        by_vendor[r["vendor"]] += r["total"]
        by_month[(r["date"] or "0000-00")[:7]] += r["total"]
    cat_pairs = sorted(by_cat.items(), key=lambda x: -x[1])
    vendor_pairs = sorted(by_vendor.items(), key=lambda x: -x[1])
    month_pairs = sorted(by_month.items())

    dates = sorted(r["date"] for r in rows if r["date"])
    period = f"{dates[0]} → {dates[-1]}" if dates else "—"

    kpi = [
        ("Số hoá đơn", str(n)),
        ("Tổng tiền hàng", vnd(sum_sub)),
        ("Tổng VAT", vnd(sum_vat)),
        ("TỔNG CHI", vnd(sum_total)),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-v">{esc(v)}</div><div class="kpi-l">{esc(l)}</div></div>'
        for l, v in kpi)

    trows = "".join(
        f"<tr><td>{esc(r['invoice_no'])}</td><td>{esc(r['date'])}</td>"
        f"<td>{esc(r['vendor'])}</td><td>{esc(r['category'])}</td>"
        f"<td class='num'>{vnd(r['subtotal'])}</td><td class='num'>{vnd(r['vat'])}</td>"
        f"<td class='num b'>{vnd(r['total'])}</td></tr>"
        for r in sorted(rows, key=lambda x: x["date"]))

    vendor_rows = "".join(
        f"<tr><td>{esc(v)}</td><td class='num b'>{vnd(t)}</td>"
        f"<td class='num'>{t/sum_total*100:.1f}%</td></tr>"
        for v, t in vendor_pairs)

    html = f"""<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(args.title)}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#f4f6fb;color:#1c2540}}
 .wrap{{max-width:980px;margin:0 auto;padding:24px}}
 .hd{{background:linear-gradient(135deg,#1c2e6e,#2b50c2);color:#fff;border-radius:14px;padding:24px 28px}}
 .hd h1{{margin:0 0 4px;font-size:24px}} .hd .sub{{opacity:.85;font-size:14px}}
 .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}}
 .kpi{{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.07);text-align:center}}
 .kpi-v{{font-size:20px;font-weight:700;color:#1c2e6e}} .kpi-l{{font-size:12px;color:#6a7390;margin-top:4px}}
 .card{{background:#fff;border-radius:12px;padding:18px 20px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.07)}}
 .card h2{{font-size:16px;margin:0 0 12px;color:#1c2e6e}}
 table{{width:100%;border-collapse:collapse;font-size:13px}}
 th,td{{padding:8px 10px;text-align:left;border-bottom:1px solid #eef0f6}}
 th{{background:#eef1fb;color:#33406e;font-weight:600}}
 td.num{{text-align:right;font-variant-numeric:tabular-nums}} td.b{{font-weight:700;color:#1c2e6e}}
 tr:nth-child(even) td{{background:#fafbfe}}
 .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
 .foot{{color:#9aa1b8;font-size:12px;text-align:center;margin:18px 0}}
 @media(max-width:760px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.grid2{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">
 <div class="hd"><h1>{esc(args.title)}</h1>
   <div class="sub">Kỳ: {esc(period)} · {n} hoá đơn · Nguồn: ảnh hoá đơn quét (OCR) · Tiền tệ: VND</div></div>
 <div class="kpis">{kpi_html}</div>
 <div class="grid2">
   <div class="card"><h2>Chi theo phân loại</h2>{bars_svg(cat_pairs)}</div>
   <div class="card"><h2>Chi theo tháng</h2>{bars_svg([(m, v) for m, v in month_pairs])}</div>
 </div>
 <div class="card"><h2>Tổng theo nhà cung cấp</h2>
   <table><thead><tr><th>Nhà cung cấp</th><th class="num">Tổng chi</th><th class="num">Tỷ trọng</th></tr></thead>
   <tbody>{vendor_rows}</tbody></table></div>
 <div class="card"><h2>Chi tiết hoá đơn ({n})</h2>
   <table><thead><tr><th>Số HĐ</th><th>Ngày</th><th>Nhà cung cấp</th><th>Phân loại</th>
   <th class="num">Tiền hàng</th><th class="num">VAT</th><th class="num">Tổng</th></tr></thead>
   <tbody>{trows}</tbody>
   <tfoot><tr><td colspan="4" class="b">TỔNG CỘNG</td>
   <td class="num b">{vnd(sum_sub)}</td><td class="num b">{vnd(sum_vat)}</td>
   <td class="num b">{vnd(sum_total)}</td></tr></tfoot></table></div>
 <div class="foot">Kora — Report hoá đơn (PoC) · sinh tự động từ {esc(os.path.basename(args.rows))}</div>
</div></body></html>"""

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ Report: {args.out}")
    print(f"  {n} hoá đơn | tiền hàng {vnd(sum_sub)} | VAT {vnd(sum_vat)} | TỔNG {vnd(sum_total)}")
    print(f"  Theo phân loại: " + " · ".join(f"{c} {vnd(t)}" for c, t in cat_pairs))


if __name__ == "__main__":
    main()
