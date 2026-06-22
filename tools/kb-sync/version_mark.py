#!/usr/bin/env python3
"""
version_mark.py — Đánh dấu PHIÊN BẢN US ↔ Change Request trước khi /claude-knowledge-sync đẩy lên.

Khi 1 User Story cũ có 1 "change request" mới (phát hiện qua issue-link Jira: 'supersedes',
'clones', 'relates'… HOẶC issue type 'Change Request'), tool này:
  • GIỮ NGUYÊN note US cũ, nhưng đánh dấu frontmatter `superseded: true` + banner cảnh báo + link CR.
  • Thêm vào note CR: `supersedes: <US>` + mục "## Thay thế" trỏ ngược về US.
  • Thêm cạnh đồ thị {from: CR, to: US, relation: "supersedes"} vào relation-graph.

Vì thay đổi nằm NGAY trong markdown → content_hash đổi → lần push kế (confluence/github) tự cập
nhật trang US cũ TẠI CHỖ (giữ, không nhân bản) và đẩy CR mới lên. Idempotent: đã mark thì bỏ qua.

Thuần stdlib. Dùng:
  python3 tools/kb-sync/version_mark.py --root . --dry-run
  python3 tools/kb-sync/version_mark.py --root . --apply
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
SENT_OLD = "<!-- kora:superseded -->"
SENT_NEW = "<!-- kora:supersedes -->"

DEFAULT_LINK_TYPES = ["supersedes", "is superseded by", "clones", "is cloned by", "relates"]
DEFAULT_ISSUE_TYPES = ["Change Request", "Thay đổi yêu cầu"]


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_config_scalars(cfg_path: Path) -> dict:
    """Đọc config → dict dotted-key (scalar). Giống load_config của sync_confluence (rút gọn)."""
    result, stack = {}, []
    if not cfg_path.exists():
        return result
    for raw in cfg_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or raw.lstrip().startswith("- "):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, rawval = line.partition(":")
        key, rawval = key.strip(), rawval.strip()
        quoted = rawval[:1] in ('"', "'")
        if quoted:
            q = rawval[0]
            end = rawval.find(q, 1)
            val = rawval[1:end] if end != -1 else rawval[1:]
        else:
            val = re.sub(r"(^|\s)#.*$", "", rawval).strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        dotted = ".".join([k for _, k in stack] + [key])
        if val == "" and not quoted:
            stack.append((indent, key))
            continue
        result[dotted] = val
    return result


def cfg_list(cfg: dict, key: str, default: list) -> list:
    raw = cfg.get(key)
    if not raw:
        return default
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else default
    except Exception:  # noqa: BLE001
        return default


def read_vault(root: Path, cfg: dict) -> Path:
    v = cfg.get("knowledge_base.vault_path") or "Project_Name_Brain"
    p = Path(v)
    return p if p.is_absolute() else (root / p)


def parse_fm(text: str):
    m = FM_RE.match(text)
    if not m:
        return None, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("-"):
            k, _, val = line.partition(":")
            fm[k.strip()] = val.strip().strip('"').strip("'")
    return m, fm


def index_notes(vault: Path):
    """Quét vault → map jira_key -> {path, file(stem), issue_type, type}."""
    notes = {}
    for p in sorted(vault.rglob("*.md")):
        if "_system" in p.parts or "_wiki" in p.parts or p.name.startswith("."):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        m, fm = parse_fm(text)
        key = (fm or {}).get("jira_key")
        if not key:
            continue
        notes[key] = {
            "path": p, "file": p.stem,
            "issue_type": (fm or {}).get("jira_issue_type", ""),
            "type": (fm or {}).get("type", ""),
            "superseded_by": (fm or {}).get("superseded_by", ""),
        }
    return notes


def node_issue_types(graph: dict) -> dict:
    return {n.get("id"): n.get("issue_type", "") for n in graph.get("nodes", [])}


def detect_pairs(graph, itypes, link_types, issue_types):
    """Trả set (old_us_key, cr_key)."""
    lt_set = {x.lower() for x in link_types}
    it_set = {x.lower() for x in issue_types}
    pairs = set()
    for e in graph.get("edges", []):
        if e.get("relation") != "linked":
            continue
        fr, to = e.get("from"), e.get("to")
        if not fr or not to:
            continue
        lt = (e.get("link_type") or "").lower()
        fr_cr = (itypes.get(fr, "") or "").lower() in it_set
        to_cr = (itypes.get(to, "") or "").lower() in it_set
        # cổng: link_type thuộc nhóm CR HOẶC 1 đầu là issue type Change Request.
        if lt not in lt_set and not (fr_cr or to_cr):
            continue
        # 'relates' yếu: chỉ tính khi 1 đầu là Change Request.
        if lt == "relates" and not (fr_cr or to_cr):
            continue
        # Xác định cũ (US) vs mới (CR).
        if lt in ("supersedes", "clones"):
            old, new = to, fr
        elif lt in ("is superseded by", "is cloned by"):
            old, new = fr, to
        elif fr_cr and not to_cr:
            old, new = to, fr
        elif to_cr and not fr_cr:
            old, new = fr, to
        else:
            continue
        pairs.add((old, new))
    return pairs


def set_fm_key(fm_lines, key, val):
    for i, ln in enumerate(fm_lines):
        if ln.split(":", 1)[0].strip() == key:
            fm_lines[i] = f"{key}: {val}"
            return
    fm_lines.append(f"{key}: {val}")


def patch_old_us(path: Path, cr_key, cr_file, mark, apply):
    text = path.read_text(encoding="utf-8", errors="replace")
    m, fm = parse_fm(text)
    if fm is None:
        return False
    if fm.get("superseded_by") == cr_key:
        return False  # idempotent
    if not apply:
        return True
    fm_lines = m.group(1).splitlines()
    set_fm_key(fm_lines, "superseded", "true")
    set_fm_key(fm_lines, "superseded_by", cr_key)
    set_fm_key(fm_lines, "superseded_at", now_iso())
    body = text[m.end():]
    banner = (f"{SENT_OLD}\n> ⚠️ **ĐÃ THAY THẾ** bởi change request [[{cr_file}]] ({cr_key}). "
              f"Giữ lại để truy vết.\n\n")
    if SENT_OLD not in body:
        body = banner + body
    path.write_text("---\n" + "\n".join(fm_lines) + "\n---\n\n" + body, encoding="utf-8")
    return True


def patch_cr(path: Path, us_key, us_file, apply):
    text = path.read_text(encoding="utf-8", errors="replace")
    m, fm = parse_fm(text)
    if fm is None:
        return
    if not apply:
        return
    fm_lines = m.group(1).splitlines()
    set_fm_key(fm_lines, "supersedes", us_key)
    body = text[m.end():]
    if SENT_NEW not in body:
        body = body.rstrip() + f"\n\n## Thay thế\n{SENT_NEW}\n- [[{us_file}]] ({us_key})\n"
    path.write_text("---\n" + "\n".join(fm_lines) + "\n---\n\n" + body, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Đánh dấu US cũ ↔ Change Request (versioning) trước khi sync.")
    ap.add_argument("--root", default=".", help="Thư mục gốc project (mặc định .)")
    ap.add_argument("--apply", action="store_true", help="Ghi thay đổi (mặc định chỉ dry-run).")
    ap.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê cặp phát hiện, KHÔNG ghi.")
    args = ap.parse_args()
    apply = args.apply and not args.dry_run

    root = Path(args.root).resolve()
    cfg = load_config_scalars(root / "config" / "factory-config.yaml")
    vault = read_vault(root, cfg)
    if not vault.exists():
        print(f"⚠️  Không thấy vault: {vault}")
        return 0
    gpath = vault / "_system" / "relation-graph.json"
    if not gpath.exists():
        print("ℹ️  Chưa có relation-graph.json — không có gì để đánh dấu.")
        return 0
    graph = json.loads(gpath.read_text(encoding="utf-8"))

    link_types = cfg_list(cfg, "sync.versioning.cr_link_types", DEFAULT_LINK_TYPES)
    issue_types = cfg_list(cfg, "sync.versioning.cr_issue_types", DEFAULT_ISSUE_TYPES)
    itypes = node_issue_types(graph)
    notes = index_notes(vault)
    pairs = detect_pairs(graph, itypes, link_types, issue_types)

    if not pairs:
        print("ℹ️  Không phát hiện cặp US↔Change-Request nào.")
        return 0

    if not any(e.get("link_type") for e in graph.get("edges", [])):
        print("⚠️  Đồ thị chưa có 'link_type' (vault quét bằng bản cũ) — chỉ nhận diện theo issue-type. "
              "Nên quét lại nguồn để đầy đủ.", file=sys.stderr)

    changed = 0
    new_edges = []
    for old, new in sorted(pairs):
        if old not in notes:
            print(f"  ⚠️ Không thấy note US cũ {old} trong vault — bỏ qua.", file=sys.stderr)
            continue
        cr_file = notes.get(new, {}).get("file", new)
        us_file = notes[old]["file"]
        did = patch_old_us(notes[old]["path"], new, cr_file, "superseded", apply)
        action = "MARK" if did else "đã mark (skip)"
        print(f"  {action}: US {old} ← thay bởi CR {new}")
        if new in notes:
            patch_cr(notes[new]["path"], old, us_file, apply)
        if did:
            changed += 1
            new_edges.append({"from": new, "to": old, "relation": "supersedes"})

    if apply and new_edges:
        seen = {(e["from"], e["to"], e["relation"]) for e in graph["edges"]}
        for e in new_edges:
            if (e["from"], e["to"], e["relation"]) not in seen:
                graph["edges"].append(e)
                seen.add((e["from"], e["to"], e["relation"]))
        gpath.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")

    mode = "Đã ghi" if apply else "[dry-run] sẽ ghi"
    print(f"✅ {mode}: {changed if apply else len(pairs)} cặp US↔CR ({len(pairs)} phát hiện).")
    return 0


if __name__ == "__main__":
    main()
