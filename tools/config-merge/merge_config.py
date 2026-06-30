#!/usr/bin/env python3
"""
merge_config.py — Thêm KEY MỚI từ factory-config.example.yaml vào factory-config.yaml của user mà GIỮ NGUYÊN
mọi giá trị + comment + thứ tự user. CHỈ thư viện chuẩn (KHÔNG pyyaml). Parser THEO INDENT-STACK (nhiều cấp).

⚠️ AN TOÀN TUYỆT ĐỐI (config user là DATA): CHỈ THÊM key example mà user CHƯA có (theo ĐƯỜNG DẪN ĐẦY ĐỦ
parent.child.grandchild). TUYỆT ĐỐI không sửa/đổi/đảo dòng user đang có. Đặt key con vào ĐÚNG block cha,
ĐÚNG indent của sibling user. Nếu cha trong user là SCALAR (vd `domain: healthcare`) mà example là block →
BỎ QUA (không inject → tránh YAML hỏng). File user dùng TAB để thụt → chỉ thêm block TOP-LEVEL, bỏ qua nested.

Dùng:
  python3 merge_config.py --user <factory-config.yaml> --example <factory-config.example.yaml> [--write] [--quiet]
  --write : ghi đè file user (mặc định in ra stdout). In JSON {added:[...], skipped:[...], unchanged:bool} ra stderr.
"""
import argparse
import json
import re
import sys

_KEY_RE = re.compile(r"^([ \t]*)([A-Za-z0-9_.\-]+):(.*)$")


def _key_line(line):
    """(indent_str, key, rest_sau_dau_colon) nếu là dòng 'key:'; None nếu comment/blank/list/giá-trị-tiếp."""
    s = line.rstrip("\n")
    if not s.strip() or s.lstrip().startswith("#"):
        return None
    m = _KEY_RE.match(s)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


def parse_nodes(lines):
    """List node {idx, indent, key, path, parent, has_value} + has_tabs. indent = số ký tự thụt (space)."""
    nodes, stack, has_tabs = [], [], False
    for idx, line in enumerate(lines):
        info = _key_line(line)
        if info is None:
            continue
        ind_str, key, rest = info
        if "\t" in ind_str:
            has_tabs = True
        indent = len(ind_str)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = ".".join(k for _, k in stack)
        path = f"{parent}.{key}" if parent else key
        stack.append((indent, key))
        has_value = bool(rest.strip()) and not rest.lstrip().startswith("#")
        nodes.append({"idx": idx, "indent": indent, "key": key, "path": path,
                      "parent": parent, "has_value": has_value})
    return nodes, has_tabs


def index_user(lines, nodes):
    """by_path[path] = node + child_indent + subtree_end (dòng cuối subtree, đã bỏ blank đuôi)."""
    by_path = {}
    for i, n in enumerate(nodes):
        # subtree_end: tới ngay trước node kế có indent <= n.indent
        end = len(lines) - 1
        for m in nodes[i + 1:]:
            if m["indent"] <= n["indent"]:
                end = m["idx"] - 1
                break
        while end > n["idx"] and not lines[end].strip():   # bỏ blank đuôi
            end -= 1
        n["subtree_end"] = end
        # child_indent = indent của con TRỰC TIẾP đầu tiên
        n["child_indent"] = None
        for m in nodes[i + 1:]:
            if m["indent"] <= n["indent"]:
                break
            if m["parent"] == n["path"]:
                n["child_indent"] = m["indent"]
                break
        by_path[n["path"]] = n
    return by_path


def _reindent(line, delta):
    if delta == 0:
        return line
    lead = len(line) - len(line.lstrip(" "))
    return " " * max(0, lead + delta) + line[lead:]


def _nl(s):
    return s if s.endswith("\n") else s + "\n"


def merge(user_lines, example_lines):
    u_nodes, u_tabs = parse_nodes(user_lines)
    e_nodes, _ = parse_nodes(example_lines)
    u_by = index_user(user_lines, u_nodes)
    present = set(u_by)
    out = list(user_lines)
    added, skipped = [], []

    # bước thụt phổ biến của user (để đặt con khi cha CHƯA có con nào)
    steps = [n["indent"] - u_by[n["parent"]]["indent"]
             for n in u_nodes if n["parent"] in u_by and n["indent"] > u_by[n["parent"]]["indent"]]
    step = min((s for s in steps if s > 0), default=2)

    inserts = {}      # anchor_line_idx (chèn SAU) -> [dòng]
    eof_blocks = []   # block top-level mới (thêm cuối file)

    def subtree(i):
        """(các DÒNG example của node i, list path trong subtree, index node kế tiếp ngoài subtree)."""
        n = e_nodes[i]
        j = i + 1
        paths = [n["path"]]
        while j < len(e_nodes) and e_nodes[j]["indent"] > n["indent"]:
            paths.append(e_nodes[j]["path"])
            j += 1
        sub_end = e_nodes[j]["idx"] - 1 if j < len(e_nodes) else len(example_lines) - 1
        while sub_end > n["idx"] and not example_lines[sub_end].strip():
            sub_end -= 1
        return example_lines[n["idx"]:sub_end + 1], paths, j

    i = 0
    while i < len(e_nodes):
        n = e_nodes[i]
        if n["path"] in present:
            i += 1
            continue
        sub_lines, sub_paths, nxt = subtree(i)
        par = n["parent"]
        if par == "":
            # top-level mới → thêm nguyên block ở cuối file (giữ indent example)
            eof_blocks.append(sub_lines)
            added.append(n["path"])
            present.update(sub_paths)
        elif par in u_by and not u_by[par]["has_value"]:
            # cha CÓ trong user và là MAPPING (không phải scalar) → chèn con đúng chỗ, đúng indent
            if u_tabs:
                skipped.append(n["path"])           # file user dùng TAB → không mạo hiểm re-indent nested
            else:
                tci = u_by[par]["child_indent"]
                if tci is None:
                    tci = u_by[par]["indent"] + step
                delta = tci - n["indent"]
                # Chèn NGAY SAU DÒNG KEY của cha (đầu block) — mỗi cha 1 anchor RIÊNG → không trộn indent
                # giữa con của cha (vd reports, indent 2) và con của sub-block (vd reports.email, indent 4).
                anchor = u_by[par]["idx"]
                inserts.setdefault(anchor, []).extend(_reindent(x, delta) for x in sub_lines)
                added.append(n["path"])
            present.update(sub_paths)
        else:
            # cha là SCALAR (xung đột) hoặc không xác định → BỎ QUA (tránh làm hỏng config)
            skipped.append(n["path"])
            present.update(sub_paths)
        i = nxt

    # chèn nested từ DƯỚI lên (anchor lớn → nhỏ) để không lệch index
    for anchor in sorted(inserts, reverse=True):
        out[anchor] = _nl(out[anchor])
        out[anchor + 1:anchor + 1] = [_nl(x) for x in inserts[anchor]]

    if eof_blocks:
        if out and not out[-1].endswith("\n"):
            out[-1] = _nl(out[-1])
        if out and out[-1].strip():
            out.append("\n")
        for blk in eof_blocks:
            out.extend(_nl(x) for x in blk)

    return out, added, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--example", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    try:
        with open(args.user, encoding="utf-8") as f:
            user_lines = f.readlines()
        with open(args.example, encoding="utf-8") as f:
            example_lines = f.readlines()
    except OSError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2

    merged, added, skipped = merge(user_lines, example_lines)

    if args.write:
        if added:
            with open(args.user, "w", encoding="utf-8") as f:
                f.writelines(merged)
    else:
        sys.stdout.write("".join(merged))

    if not args.quiet:
        print(json.dumps({"added": added, "skipped": skipped, "unchanged": not added},
                         ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
