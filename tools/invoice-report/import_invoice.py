#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_invoice.py — Nạp HOÁ ĐƠN (rows đã OCR từ ảnh) vào VAULT thành note tri thức.
Schema riêng cho hoá đơn (source: invoice) — KHÁC import_excel.py (hướng task summary/status).

   python3 tools/invoice-report/import_invoice.py \
       --from-rows reports/_invoice-rows.json --source-id invoice__demo

Mỗi hoá đơn → 1 note: <vault>/Invoices/<source_id>/<invoice_no>.md
Frontmatter: type/source/source_id/invoice_no/date/vendor/category/currency/subtotal/vat/vat_rate/total.
Ghi marker last-import-<source_id>.txt để báo cáo biết độ mới. Stdlib-only.
"""
import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta


def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(2)


def now_iso():
    return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%dT%H:%M:%S+07:00")


def read_vault_path(cwd):
    """Đọc vault_path trong config/factory-config.yaml (regex đơn giản, không pyyaml)."""
    cfg = os.path.join(cwd, "config", "factory-config.yaml")
    if os.path.exists(cfg):
        for line in open(cfg, encoding="utf-8"):
            m = re.match(r"\s*vault_path:\s*(.+?)\s*(#.*)?$", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return None


def load_rows(path):
    if not os.path.exists(path):
        die(f"Không thấy file rows: {path}")
    if path.lower().endswith(".json"):
        return json.load(open(path, encoding="utf-8"))
    return list(csv.DictReader(open(path, encoding="utf-8-sig", newline="")))


def num(v):
    try:
        return float(str(v).replace(",", "").replace("₫", "").strip() or 0)
    except ValueError:
        return 0.0


def slug(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", str(s)).strip("-") or "HD"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-rows", dest="from_rows", required=True, help="rows .json (list[dict]) hoặc .csv")
    ap.add_argument("--source-id", dest="source_id", default="invoice__import", help="ID nguồn (thư mục + marker).")
    ap.add_argument("--vault", help="Đường dẫn vault (mặc định đọc vault_path trong config).")
    args = ap.parse_args()

    cwd = os.getcwd()
    vault = args.vault or read_vault_path(cwd)
    if not vault:
        die("Không xác định được vault. Truyền --vault hoặc đặt vault_path trong config/factory-config.yaml.")
    if not os.path.isabs(vault):
        vault = os.path.join(cwd, vault)
    if not os.path.isdir(vault):
        die(f"Vault không tồn tại: {vault}")

    rows = load_rows(args.from_rows)
    if not rows:
        die("File rows rỗng.")

    dest = os.path.join(vault, "Invoices", args.source_id)
    os.makedirs(dest, exist_ok=True)
    written = 0
    for r in rows:
        no = str(r.get("invoice_no") or r.get("no") or f"HD-{written+1}").strip()
        subtotal, vat, total = num(r.get("subtotal")), num(r.get("vat")), num(r.get("total"))
        if total == 0:
            total = subtotal + vat
        vendor = str(r.get("vendor") or "").strip()
        fm = [
            "---",
            "type: invoice",
            "source: invoice",
            f"source_id: {args.source_id}",
            f"invoice_no: {no}",
            f"date: {str(r.get('date') or '').strip()}",
            f'vendor: "{vendor}"',
            f'category: "{str(r.get("category") or "Khác").strip()}"',
            f"currency: {str(r.get('currency') or 'VND').strip()}",
            f"subtotal: {subtotal:.0f}",
            f"vat_rate: {num(r.get('vat_rate'))}",
            f"vat: {vat:.0f}",
            f"total: {total:.0f}",
            f"imported_at: {now_iso()}",
            "---",
            "",
            f"# {no} — {vendor}",
            "",
            f"- Ngày: {str(r.get('date') or '').strip()}",
            f"- Phân loại: {str(r.get('category') or 'Khác').strip()}",
            f"- Mặt hàng: {str(r.get('items') or '').strip()}",
            f"- Tiền hàng: {subtotal:,.0f} | VAT: {vat:,.0f} | Tổng: {total:,.0f}",
            "",
        ]
        open(os.path.join(dest, f"{slug(no)}.md"), "w", encoding="utf-8").write("\n".join(fm))
        written += 1

    marker = os.path.join(vault, "_system", f"last-import-{args.source_id}.txt")
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    open(marker, "w", encoding="utf-8").write(now_iso())

    print(f"✓ Nạp {written} hoá đơn → {dest}")
    print(f"  source_id={args.source_id} | marker: {marker}")


if __name__ == "__main__":
    main()
