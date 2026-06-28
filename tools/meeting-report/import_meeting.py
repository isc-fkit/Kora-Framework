#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_meeting.py — Nạp BIÊN BẢN HỌP (đã được AI tóm tắt) vào VAULT thành note tri thức.
Schema riêng (type: meeting, source: meeting) — phục vụ report-type meeting-roadmap (Pha 4).

   python3 tools/meeting-report/import_meeting.py \
       --from-rows reports/_meeting-rows.json --source-id meeting__demo

Mỗi cuộc họp → 1 note: <vault>/Meetings/<source_id>/<slug-title>.md
rows json = list[dict]: title, date, attendees, summary, decisions[], action_items[], risks[].
Stdlib-only.
"""
import argparse
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
    cfg = os.path.join(cwd, "config", "factory-config.yaml")
    if os.path.exists(cfg):
        for line in open(cfg, encoding="utf-8"):
            m = re.match(r"\s*vault_path:\s*(.+?)\s*(#.*)?$", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return None


def slug(s):
    return (re.sub(r"[^A-Za-z0-9_-]+", "-", str(s)).strip("-") or "meeting")[:60]


def _bullets(items):
    return "\n".join(f"- {x}" for x in (items or [])) or "- (không có)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-rows", dest="from_rows", required=True, help="rows .json (list[dict]) biên bản họp đã tóm tắt")
    ap.add_argument("--source-id", dest="source_id", default="meeting__import")
    ap.add_argument("--vault", help="Đường dẫn vault (mặc định đọc vault_path trong config).")
    args = ap.parse_args()

    cwd = os.getcwd()
    vault = args.vault or read_vault_path(cwd)
    if not vault:
        die("Không xác định được vault. Truyền --vault hoặc đặt vault_path trong config.")
    if not os.path.isabs(vault):
        vault = os.path.join(cwd, vault)
    if not os.path.isdir(vault):
        die(f"Vault không tồn tại: {vault}")

    rows = json.load(open(args.from_rows, encoding="utf-8"))
    if not rows:
        die("File rows rỗng.")

    dest = os.path.join(vault, "Meetings", args.source_id)
    os.makedirs(dest, exist_ok=True)
    n = 0
    for r in rows:
        title = str(r.get("title") or f"Họp {n+1}").strip()
        decisions = r.get("decisions") or []
        actions = r.get("action_items") or []
        risks = r.get("risks") or []
        fm = [
            "---", "type: meeting", "source: meeting", f"source_id: {args.source_id}",
            f'title: "{title}"', f"date: {str(r.get('date') or '').strip()}",
            f'attendees: "{str(r.get("attendees") or "").strip()}"',
            f"n_decisions: {len(decisions)}", f"n_actions: {len(actions)}", f"n_risks: {len(risks)}",
            f"imported_at: {now_iso()}", "---", "",
            f"# {title}", "",
            f"- Ngày: {str(r.get('date') or '').strip()}",
            f"- Thành phần: {str(r.get('attendees') or '').strip()}", "",
            "## Tóm tắt", str(r.get("summary") or "").strip(), "",
            "## Quyết định", _bullets(decisions), "",
            "## Hành động (action items)", _bullets(actions), "",
            "## Rủi ro", _bullets(risks), "",
        ]
        open(os.path.join(dest, f"{slug(title)}.md"), "w", encoding="utf-8").write("\n".join(fm))
        n += 1

    marker = os.path.join(vault, "_system", f"last-import-{args.source_id}.txt")
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    open(marker, "w", encoding="utf-8").write(now_iso())
    print(f"✓ Nạp {n} biên bản họp → {dest}")


if __name__ == "__main__":
    main()
