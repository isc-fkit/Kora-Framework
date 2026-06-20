#!/usr/bin/env python3
"""
synthesize.py — TỔNG HỢP NHẸ: từ note thô trong vault → trang "wiki hub" liên kết cho mỗi project.

Thuần máy (KHÔNG token, KHÔNG gọi LLM). Mỗi lần chạy dựng lại các trang `<...>/_wiki/<Project>-Wiki.md`
(idempotent, đánh dấu `generated: true` — chỉnh tay sẽ bị ghi đè ở lần scan kế). Backlink giữa các note
đã có sẵn qua wikilink trong từng note; tool này thêm TRANG ĐIỀU HƯỚNG tổng hợp + mục "Quan hệ".

Dùng:
  python3 tools/kb-synth/synthesize.py --root .
"""
import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
TYPE_ORDER = [("epic", "Epics"), ("user_story", "User Stories"), ("task", "Tasks"),
              ("bug", "Bugs"), ("sub-task", "Sub-tasks"), ("subtask", "Sub-tasks")]


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_vault_path(root: Path) -> str:
    cfg = root / "config" / "factory-config.yaml"
    if cfg.exists():
        for line in cfg.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("vault_path:"):
                v = s.split(":", 1)[1]
                v = re.sub(r"(^|\s)#.*$", "", v).strip().strip('"').strip("'")
                if v:
                    return v
    return "Project_Name_Brain"


def parse_note(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body = {}, text
    m = FM_RE.match(text)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.lstrip().startswith("-"):
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip('"').strip("'")
        body = text[m.end():]
    title = fm.get("title")
    if not title:
        mh = H1_RE.search(body)
        title = mh.group(1).strip() if mh else path.stem
    return fm, title


def main():
    ap = argparse.ArgumentParser(description="Tổng hợp nhẹ: dựng wiki hub liên kết cho mỗi project.")
    ap.add_argument("--root", default=".", help="Thư mục gốc project (mặc định .)")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    vault = Path(read_vault_path(root))
    vault = vault if vault.is_absolute() else (root / vault)
    if not vault.exists():
        print(f"⚠️  Không thấy vault: {vault}")
        return 0
    sysdir = vault / "_system"

    # 1) Gom note Jira (có frontmatter jira_key/feature_id), bỏ _system & _wiki.
    notes = {}
    for p in sorted(vault.rglob("*.md")):
        if "_system" in p.parts or "_wiki" in p.parts or p.name.startswith("."):
            continue
        fm, title = parse_note(p)
        key = fm.get("jira_key") or fm.get("feature_id")
        if not key:
            continue
        notes[key] = {
            "key": key, "file": p.stem, "path": p,
            "type": (fm.get("type") or "").strip(),
            "title": title, "status": fm.get("status", ""),
            "project": fm.get("project", "") or "KHÁC", "parent": fm.get("parent", ""),
            "superseded": fm.get("superseded", "") == "true",
            "superseded_by": fm.get("superseded_by", ""),
        }
    if not notes:
        print("ℹ️  Chưa có note Jira nào để tổng hợp.")
        return 0

    # 2) Edges (để dựng mục "Quan hệ"; có link_type cho issue-link).
    edges = []
    g = sysdir / "relation-graph.json"
    if g.exists():
        try:
            edges = json.loads(g.read_text(encoding="utf-8")).get("edges", [])
        except Exception:  # noqa: BLE001
            edges = []

    # 3) Nhóm theo project → dựng wiki hub đặt ở thư mục CHA CHUNG của note project đó.
    by_proj = {}
    for m in notes.values():
        by_proj.setdefault(m["project"], []).append(m)

    made = []
    for proj, items in sorted(by_proj.items()):
        common = Path(os.path.commonpath([str(m["path"].parent) for m in items]))
        try:
            common.relative_to(vault)
        except ValueError:
            common = vault
        wikidir = common / "_wiki"
        wikidir.mkdir(parents=True, exist_ok=True)
        keyset = {m["key"] for m in items}

        out = ["---", "generated: true", "type: wiki", f"project: {proj}",
               f'title: "{proj} — Wiki"', f"generated_at: {now_iso()}", "---", "",
               f"# {proj} — Wiki tổng hợp", "",
               "> Trang do Kora tự dựng (tổng hợp nhẹ). Sửa tay sẽ bị ghi đè ở lần scan kế.", ""]
        used = set()
        for tkey, label in TYPE_ORDER:
            grp = [m for m in items if m["type"] == tkey]
            if not grp:
                continue
            out.append(f"## {label}")
            for m in sorted(grp, key=lambda x: x["key"]):
                used.add(m["key"])
                mark = f"  ⚠️ *superseded → {m['superseded_by']}*" if m["superseded"] else ""
                out.append(f"- [[{m['file']}]] — {m['title']} (`{m['status']}`){mark}")
            out.append("")
        other = [m for m in items if m["key"] not in used]
        if other:
            out.append("## Khác")
            for m in sorted(other, key=lambda x: x["key"]):
                mark = f"  ⚠️ *superseded → {m['superseded_by']}*" if m["superseded"] else ""
                out.append(f"- [[{m['file']}]] — {m['title']} (`{m['status']}` / {m['type'] or '?'}){mark}")
            out.append("")

        rel_lines = []
        for e in edges:
            fr, to = e.get("from"), e.get("to")
            if fr in keyset and to in keyset and e.get("relation") in ("parent_of", "linked", "supersedes"):
                lt = f" ({e.get('link_type')})" if e.get("link_type") else ""
                ff = notes.get(fr, {}).get("file", fr)
                tf = notes.get(to, {}).get("file", to)
                rel_lines.append(f"- [[{ff}]] —{e.get('relation')}{lt}→ [[{tf}]]")
        if rel_lines:
            out.append("## Quan hệ")
            out.extend(sorted(set(rel_lines)))
            out.append("")

        hub = wikidir / f"{re.sub(r'[^-\w]+', '-', proj).strip('-') or 'project'}-Wiki.md"
        hub.write_text("\n".join(out), encoding="utf-8")
        made.append(hub)

    print(f"✅ Tổng hợp nhẹ xong: {len(made)} trang wiki hub ({len(notes)} note, {len(by_proj)} project).")
    for h in made:
        try:
            print(f"   - {h.relative_to(root)}")
        except ValueError:
            print(f"   - {h}")
    return 0


if __name__ == "__main__":
    main()
