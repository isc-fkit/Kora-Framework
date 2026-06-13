#!/usr/bin/env python3
"""
build_index.py — Bộ tự-dựng-chỉ-mục cho Knowledge Base (lớp "tự tiến hóa").

Chạy bằng máy, KHÔNG tốn token, KHÔNG cần thư viện ngoài. Quét docs/ + vault →
dựng lại .kb/index.json + .kb/relation-graph.json (gộp graph raw của vault) +
xuất .kb/health-report.md (orphan, dead-link, stale, coverage gap).

Dùng:
  python3 build_index.py                 # chạy từ gốc project (mặc định)
  python3 build_index.py --root <path>   # chỉ định gốc project
  python3 build_index.py --stale-days 60 # ngưỡng "lỗi thời" (mặc định 60)

Triết lý: tri thức tự dựng lại sau mỗi thay đổi → index không bao giờ lệch docs/.
Đây là phần "Nạp" và "tự kiểm" của vòng lặp Nạp → Xử lý → Tự cải tiến.
"""

import argparse
import glob
import json
import os
import re
from datetime import datetime, timezone

NOW = datetime.now(timezone.utc)
ID_RE = re.compile(r"\b(F-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*|BR-[A-Za-z0-9-]+|AC-[A-Za-z0-9-]+|ADR-\d+)\b")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")


def read_frontmatter(text):
    """Trả về dict frontmatter YAML đơn giản (key: value) nếu có."""
    fm = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                line = line.strip()
                if not line or ":" not in line or line.startswith("#"):
                    continue
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def file_mtime_days(path):
    try:
        m = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
        return (NOW - m).days
    except OSError:
        return 0


def scan_docs(root):
    """Quét docs/ — mỗi .md có frontmatter là một entry tri thức."""
    entries, refs = [], []
    docs = os.path.join(root, "docs")
    for path in glob.glob(os.path.join(docs, "**", "*.md"), recursive=True):
        rel = os.path.relpath(path, root)
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        fm = read_frontmatter(text)
        # ID suy ra từ frontmatter hoặc từ tên thư mục feature F-xxx
        fid = fm.get("feature_id") or fm.get("jira_key") or ""
        if not fid:
            m = re.search(r"(F-[A-Za-z0-9-]+)", rel)
            fid = m.group(1) if m else ""
        entry = {
            "id": fid or rel,
            "path": rel,
            "type": fm.get("type", "doc"),
            "title": fm.get("title", os.path.basename(path)[:-3]),
            "status": fm.get("status", ""),
            "version": fm.get("version", ""),
            "stale_days": file_mtime_days(path),
        }
        entries.append(entry)
        # 07-research là tài liệu tham khảo (chứa ID ví dụ) → index nhưng KHÔNG dò edge
        # để tránh dead-link giả. Tương tự bỏ qua README.
        if os.sep + "07-research" + os.sep in os.sep + rel + os.sep or os.path.basename(path).lower() == "readme.md":
            continue
        # tham chiếu: wikilink + ID nhắc trong nội dung (để dựng edge + bắt dead-link)
        body = text
        for mid in set(ID_RE.findall(body)):
            if fid and mid != fid:
                refs.append({"from": fid, "to": mid, "relation": "references", "src": rel})
        for wl in set(WIKILINK_RE.findall(body)):
            refs.append({"from": fid or rel, "to": wl.strip(), "relation": "links", "src": rel})
    return entries, refs


def load_json(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return default


def find_vault(root):
    """Tìm thư mục vault: đọc vault_path từ config nếu có, không thì *_Brain."""
    cfg = os.path.join(root, "config", "factory-config.yaml")
    if os.path.exists(cfg):
        for line in open(cfg, encoding="utf-8"):
            m = re.search(r"vault_path:\s*(\S+)", line)
            if m:
                vp = os.path.join(root, m.group(1).strip())
                if os.path.isdir(vp):
                    return vp
    for cand in glob.glob(os.path.join(root, "*_Brain")) + [os.path.join(root, "Project_Name_Brain")]:
        if os.path.isdir(cand):
            return cand
    return ""


def merge_vault_graph(root, nodes_by_id, edges):
    """Gộp relation-graph raw mà import_jira.py đã sinh trong vault/_system."""
    vault = find_vault(root)
    if not vault:
        return 0
    g = load_json(os.path.join(vault, "_system", "relation-graph.json"), {"nodes": [], "edges": []})
    for n in g.get("nodes", []):
        nodes_by_id.setdefault(n["id"], {"id": n["id"], "type": n.get("type", ""),
                                         "title": n.get("title", ""), "status": n.get("status", ""),
                                         "origin": "vault_raw"})
    seen = {(e["from"], e["to"], e["relation"]) for e in edges}
    for e in g.get("edges", []):
        key = (e["from"], e["to"], e.get("relation", "linked"))
        if key not in seen:
            edges.append({"from": e["from"], "to": e["to"], "relation": e.get("relation", "linked")})
            seen.add(key)
    return len(g.get("nodes", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--stale-days", type=int, default=60)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    kb = os.path.join(root, ".kb")
    os.makedirs(kb, exist_ok=True)

    entries, refs = scan_docs(root)
    nodes_by_id = {}
    for e in entries:
        nodes_by_id[e["id"]] = {"id": e["id"], "type": e["type"], "title": e["title"],
                                "status": e["status"], "origin": "docs"}
    edges = []
    seen = set()
    for r in refs:
        key = (r["from"], r["to"], r["relation"])
        if key not in seen:
            edges.append({"from": r["from"], "to": r["to"], "relation": r["relation"]})
            seen.add(key)
    vault_nodes = merge_vault_graph(root, nodes_by_id, edges)

    # ---- index.json ----
    index = {"generated_at": NOW.isoformat(), "count": len(entries), "entries": entries}
    json.dump(index, open(os.path.join(kb, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # ---- relation-graph.json ----
    graph = {"generated_at": NOW.isoformat(), "nodes": list(nodes_by_id.values()), "edges": edges}
    json.dump(graph, open(os.path.join(kb, "relation-graph.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # ---- HEALTH CHECK ----
    ids = set(nodes_by_id)
    # dead link: edge trỏ tới ID dạng F-/BR-/AC-/ADR- nhưng không có node
    dead = sorted({e["to"] for e in edges
                   if ID_RE.fullmatch(e["to"] or "") and e["to"] not in ids})
    # orphan feature: feature không có edge nào tới BR hoặc AC
    feats = [n for n in nodes_by_id.values() if str(n["type"]).startswith(("feature", "user_story")) or str(n["id"]).startswith("F-")]
    has_br = {e["from"] for e in edges if str(e["to"]).startswith("BR-")}
    has_ac = {e["from"] for e in edges if str(e["to"]).startswith("AC-")}
    no_br = sorted(f["id"] for f in feats if f["id"] not in has_br)
    no_ac = sorted(f["id"] for f in feats if f["id"] not in has_ac)
    stale = sorted(((e["id"], e["stale_days"]) for e in entries if e["stale_days"] > args.stale_days),
                   key=lambda x: -x[1])

    lines = [
        "# KB Health Report", "",
        f"_Tự dựng lúc {NOW.strftime('%Y-%m-%d %H:%M UTC')} — bằng tools/kb-indexer/build_index.py_", "",
        "## Tổng quan",
        f"- Tài liệu docs/ đã lập chỉ mục: **{len(entries)}**",
        f"- Node tri thức (docs + vault raw): **{len(nodes_by_id)}** (vault raw: {vault_nodes})",
        f"- Quan hệ (edges): **{len(edges)}**", "",
        "## ⚠️ Cần chú ý", "",
        f"### Dead links — tham chiếu tới ID không tồn tại ({len(dead)})",
        ("\n".join(f"- `{d}`" for d in dead) or "- (không có) ✅"), "",
        f"### Feature chưa có Business Rule ({len(no_br)})",
        ("\n".join(f"- `{x}`" for x in no_br[:50]) or "- (không có) ✅"), "",
        f"### Feature chưa có Acceptance Criteria ({len(no_ac)})",
        ("\n".join(f"- `{x}`" for x in no_ac[:50]) or "- (không có) ✅"), "",
        f"### Tài liệu lỗi thời (>{args.stale_days} ngày chưa sửa) ({len(stale)})",
        ("\n".join(f"- `{i}` — {d} ngày" for i, d in stale[:50]) or "- (không có) ✅"), "",
        "## Gợi ý tiến hóa",
        "- Dead link → sửa tham chiếu hoặc tạo node còn thiếu.",
        "- Feature thiếu BR/AC → bổ sung khi rảnh hoặc khi feature đó được động tới.",
        "- Tài liệu lỗi thời → rà soát lại độ chính xác (chạy `tiến hóa KB`).",
    ]
    open(os.path.join(kb, "health-report.md"), "w", encoding="utf-8").write("\n".join(lines))

    print(f"✓ index.json: {len(entries)} entries")
    print(f"✓ relation-graph.json: {len(nodes_by_id)} nodes, {len(edges)} edges")
    print(f"✓ health-report.md: {len(dead)} dead-link, {len(no_br)} thiếu BR, "
          f"{len(no_ac)} thiếu AC, {len(stale)} lỗi thời")


if __name__ == "__main__":
    main()
