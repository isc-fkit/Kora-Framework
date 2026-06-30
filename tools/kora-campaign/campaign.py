#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
campaign.py — Động cơ CAMPAIGN n8n-lite: chuỗi bước TUYẾN TÍNH (không nhánh điều kiện),
hẹn ngày tự chạy. Mỗi bước TÁI DÙNG tool Kora sẵn có (shell out).

   campaign.py list
   campaign.py create --file <campaign.json>        # merge 1 campaign vào registry
   campaign.py run <id> [--dry-run]                 # chạy tuần tự các bước
   campaign.py delete --id <id>

Bước hỗ trợ HEADLESS: scan · reindex · report · geo · mail · post · sync.
Bước cần MODEL (analyze · canva) → headless BỎ QUA (chạy qua skill /claude-knowledge-campaign khi tương tác).
Bước OUTWARD (mail/post/sync) qua cổng KORA_OPS_PW (verify_ops_password.py). Chỉ thư viện chuẩn.

campaigns.json: {"campaigns": [{"id","name","schedule"(cron|date),"enabled",
  "steps": [{"type": "report", "report_type":"invoice", "source_ids":"invoice__demo"}, ...]}]}
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "campaigns.json")
OUTWARD = {"mail", "post", "sync"}
MODEL_STEPS = {"analyze", "canva"}


def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(2)


def tool_root():
    """tools/ trong project nếu có, else CORE ~/.claude/kora-framework/tools."""
    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, "tools", "progress-report")):
        return os.path.join(cwd, "tools")
    return os.path.expanduser("~/.claude/kora-framework/tools")


def load_reg():
    if os.path.exists(REG):
        try:
            return json.load(open(REG, encoding="utf-8"))
        except Exception:
            pass
    return {"campaigns": []}


def save_reg(reg):
    json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def find(reg, cid):
    return next((c for c in reg.get("campaigns", []) if c.get("id") == cid), None)


def ops_gate(T):
    vp = os.path.join(T, "archive-gate", "verify_ops_password.py")
    if not os.path.exists(vp):
        return False, "không thấy verify_ops_password.py"
    r = subprocess.run([sys.executable, vp])
    return (r.returncode == 0), ("OK" if r.returncode == 0 else "cổng KORA_OPS_PW sai/thiếu")


def build_cmd(step, T):
    """Dựng lệnh shell cho 1 bước headless. Trả (cmd_list) hoặc ('SKIP', lý do) / ('ERR', lý do)."""
    py = sys.executable
    t = lambda *rel: os.path.join(T, *rel)
    typ = step.get("type")
    if typ in MODEL_STEPS:
        return ("SKIP", f"bước '{typ}' cần MODEL (AI/Canva) — chạy qua skill khi tương tác")
    if typ == "scan":
        src = step.get("source", "")
        if src == "invoice":
            return [py, t("invoice-report", "import_invoice.py"), "--from-rows", step["from_rows"],
                    "--source-id", step.get("source_id", "invoice__import")]
        if src == "meeting":
            return [py, t("meeting-report", "import_meeting.py"), "--from-rows", step["from_rows"],
                    "--source-id", step.get("source_id", "meeting__import")]
        if src == "jira":
            cmd = [py, t("jira-to-obsidian", "import_jira.py")]
            if step.get("jql"):
                cmd += ["--jql", step["jql"]]
            if step.get("source_id"):
                cmd += ["--source-id", step["source_id"]]
            return cmd
        if src == "excel":
            return [py, t("excel-to-obsidian", "import_excel.py"), "--from-rows", step["from_rows"],
                    "--source-id", step.get("source_id", "excel__import")]
        return ("ERR", f"scan source '{src}' chưa hỗ trợ headless")
    if typ == "reindex":
        return [py, t("kb-indexer", "build_index.py"), "--root", "."]
    if typ == "report":
        cmd = [py, t("progress-report", "build_report.py"), "--report-type", step.get("report_type", "progress"),
               "--roles-confirmed"]   # campaign nền không hỏi UI → waive cổng vai trò (dùng role config nếu có)
        for k, flag in (("source_ids", "--source-ids"), ("projects", "--projects"),
                        ("template", "--template"), ("meetings", "--meetings"), ("scope", "--scope")):
            if step.get(k):
                cmd += [flag, str(step[k])]
        return cmd
    if typ == "geo":
        # Chiến dịch GEO theo roadmap: render lại scorecard/roadmap từ reports/_geo-rows.json
        # (Agent GEO Analyst làm tươi _geo-rows.json ở lượt interactive; step nền chỉ render + để mail).
        cmd = [py, t("geo-strategy", "geo_strategy.py"),
               "--rows", step.get("rows", "reports/_geo-rows.json")]
        for k, flag in (("brand", "--brand"), ("period", "--period"), ("out", "--out")):
            if step.get(k):
                cmd += [flag, str(step[k])]
        return cmd
    if typ == "mail":
        cmd = [py, t("report-mailer", "send_report.py"), "--to", step.get("to", ""),
               "--html-file", step.get("html_file", "reports/email-body-latest.html")]
        for a in step.get("attach", []):
            cmd += ["--attach", a]
        return cmd
    if typ in ("post", "sync"):
        target = step.get("target", "confluence")
        sub = {"confluence": ("confluence-sync", "sync_confluence.py"),
               "github": ("github-sync", "sync_github.py"),
               "sharepoint": ("sharepoint-sync", "sync_sharepoint.py")}.get(target)
        if not sub:
            return ("ERR", f"target '{target}' không hỗ trợ")
        return [py, t(*sub), "--push"]
    return ("ERR", f"step type '{typ}' không nhận diện")


def cmd_run(args):
    reg = load_reg()
    c = find(reg, args.id)
    if not c:
        die(f"Không thấy campaign '{args.id}'. Xem: campaign.py list")
    if not c.get("enabled", True) and not args.dry_run:
        die(f"Campaign '{args.id}' đang TẮT (enabled=false).")
    T = tool_root()
    steps = c.get("steps", [])
    print(f"▶ Campaign '{c['id']}' — {c.get('name','')} — {len(steps)} bước"
          + (" [DRY-RUN]" if args.dry_run else ""))
    gate_ok = None
    for i, step in enumerate(steps, 1):
        typ = step.get("type", "?")
        built = build_cmd(step, T)
        if isinstance(built, tuple):
            kind, detail = built
            icon = "⏭" if kind == "SKIP" else "✗"
            print(f"  {i}. {typ}: {icon} {detail}")
            if kind == "ERR" and not args.dry_run:
                print("  ⛔ Dừng (chuỗi tuyến tính).")
                break
            continue
        # bước outward → cổng KORA_OPS_PW (chỉ khi chạy thật)
        if typ in OUTWARD and not args.dry_run:
            if gate_ok is None:
                gate_ok, msg = ops_gate(T)
            if not gate_ok:
                print(f"  {i}. {typ}: ⛔ BỎ QUA (cổng KORA_OPS_PW): {msg}")
                continue
        if args.dry_run:
            print(f"  {i}. {typ}: · {' '.join(built)}")
            continue
        r = subprocess.run(built)
        if r.returncode == 0:
            print(f"  {i}. {typ}: ✓")
        else:
            print(f"  {i}. {typ}: ✗ exit {r.returncode} — {' '.join(built)}")
            print("  ⛔ Dừng campaign do bước lỗi (chuỗi tuyến tính).")
            break
    print("Xong.")


def cmd_list(args):
    reg = load_reg()
    cs = reg.get("campaigns", [])
    if not cs:
        print("ℹ️  Chưa có campaign. Tạo: campaign.py create --file <campaign.json>")
        return
    for c in cs:
        steps = " → ".join(s.get("type", "?") for s in c.get("steps", []))
        en = "ON " if c.get("enabled", True) else "OFF"
        print(f"[{en}] {c.get('id'):28} | {c.get('schedule','-'):18} | {steps}")
        print(f"        {c.get('name','')}")


def cmd_create(args):
    if not os.path.exists(args.file):
        die(f"Không thấy file: {args.file}")
    spec = json.load(open(args.file, encoding="utf-8"))
    items = spec.get("campaigns", [spec]) if isinstance(spec, dict) else spec
    reg = load_reg()
    for c in items:
        if not c.get("id"):
            die("Mỗi campaign cần 'id'.")
        reg["campaigns"] = [x for x in reg["campaigns"] if x.get("id") != c["id"]]  # replace-in-place
        reg["campaigns"].append(c)
        print(f"✓ Lưu campaign '{c['id']}' ({len(c.get('steps', []))} bước, schedule {c.get('schedule','-')})")
    save_reg(reg)


def cmd_delete(args):
    reg = load_reg()
    n0 = len(reg["campaigns"])
    reg["campaigns"] = [x for x in reg["campaigns"] if x.get("id") != args.id]
    if len(reg["campaigns"]) == n0:
        die(f"Không thấy campaign '{args.id}'.")
    save_reg(reg)
    print(f"✓ Xoá campaign '{args.id}'.")


def main():
    ap = argparse.ArgumentParser(description="Kora campaign engine (n8n-lite).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    pc = sub.add_parser("create"); pc.add_argument("--file", required=True)
    pr = sub.add_parser("run"); pr.add_argument("id"); pr.add_argument("--dry-run", action="store_true")
    pd = sub.add_parser("delete"); pd.add_argument("--id", required=True)
    args = ap.parse_args()
    {"list": cmd_list, "create": cmd_create, "run": cmd_run, "delete": cmd_delete}[args.cmd](args)


if __name__ == "__main__":
    main()
