#!/usr/bin/env python3
"""
merge_config.py — Thêm KEY MỚI từ factory-config.example.yaml vào factory-config.yaml của user
mà GIỮ NGUYÊN mọi giá trị + comment + thứ tự user đang có. CHỈ thư viện chuẩn (không pyyaml).

Mục đích: khi app lên version mới có thêm config key (vd jira.start_field / worktype_field),
update phải tự BỔ SUNG key đó vào config CŨ của user — nếu không, tính năng mới thiếu config → lỗi.

Nguyên tắc AN TOÀN:
  • CHỈ THÊM key example mà user CHƯA có (theo đường dẫn parent.key hoặc key top-level).
  • TUYỆT ĐỐI không sửa/đổi thứ tự/ghi đè giá trị hay comment user đã có.
  • Cấu trúc factory-config: key top-level (indent 0) + 1 cấp lồng (vd dưới `jira:` / `reports:` / `knowledge_base:`).

Dùng:
  python3 merge_config.py --user <factory-config.yaml> --example <factory-config.example.yaml> [--write] [--quiet]
    --write : ghi đè file user (mặc định: in kết quả ra stdout, không đụng file).
  Exit 0. In JSON {added:[...], unchanged:bool} ra stderr (trừ --quiet).
"""
import argparse
import json
import re
import sys


def _split_key(line):
    """(indent, key) nếu là dòng 'key:' (top-level/nested); None nếu là comment/blank/list/giá trị tiếp."""
    if not line.strip() or line.lstrip().startswith("#"):
        return None
    m = re.match(r"^(\s*)([A-Za-z0-9_.\-]+)\s*:", line)
    if not m:
        return None
    return len(m.group(1)), m.group(2)


def parse_structure(lines):
    """Trả (paths, blocks). paths = set 'parent.key'|'key'. blocks = {parent: last_line_index} cho key top-level có con."""
    paths = set()
    top_block_last = {}        # top-level key -> chỉ số dòng cuối cùng thuộc block đó
    cur_top = None
    cur_top_indent = 0
    for i, line in enumerate(lines):
        sk = _split_key(line)
        if sk is None:
            # dòng comment/blank/giá trị → nếu đang trong 1 top-block, vẫn coi thuộc block (cập nhật last khi có nội dung thụt vào)
            if cur_top is not None and line.strip() and (len(line) - len(line.lstrip())) > cur_top_indent:
                top_block_last[cur_top] = i
            continue
        indent, key = sk
        if indent == 0:
            cur_top = key
            cur_top_indent = 0
            paths.add(key)
            top_block_last[key] = i
        else:
            # nested dưới cur_top
            if cur_top is not None:
                paths.add(f"{cur_top}.{key}")
                top_block_last[cur_top] = i
    return paths, top_block_last


def example_items(lines):
    """Liệt kê theo thứ tự example: list (path, indent, key, parent, full_line)."""
    out = []
    cur_top = None
    for line in lines:
        sk = _split_key(line)
        if sk is None:
            continue
        indent, key = sk
        if indent == 0:
            cur_top = key
            out.append((key, 0, key, None, line))
        else:
            parent = cur_top
            out.append((f"{parent}.{key}", indent, key, parent, line))
    return out


def merge(user_lines, example_lines):
    user_paths, top_last = parse_structure(user_lines)
    ex_items = example_items(example_lines)
    out = list(user_lines)
    added = []

    # Đảm bảo mỗi dòng (trừ dòng cuối) kết thúc bằng \n để chèn an toàn.
    def _nl(s):
        return s if s.endswith("\n") else s + "\n"

    # 1) Key NESTED thiếu, dưới parent ĐÃ CÓ trong user → chèn vào cuối block đó.
    #    Gom theo parent để chèn 1 lượt (offset dịch khi chèn).
    inserts = {}  # parent_top_index -> list of lines to insert after it
    add_after_eof = []  # các top-level/parent mới
    # tái dựng top_last theo out khi chèn → để đơn giản, xử lý nested-existing trước, rồi top-new sau.

    # map: với mỗi nested key thiếu, parent có trong user?
    for path, indent, key, parent, line in ex_items:
        if path in user_paths:
            continue
        if parent is None:
            # top-level key thiếu → thêm cả block (key + các con của nó trong example) ở cuối file
            # gom con của top-level này từ example:
            block = [line]
            collecting = False
            for p2, ind2, k2, par2, ln2 in ex_items:
                if p2 == path:
                    collecting = True
                    continue
                if collecting:
                    if ind2 == 0:
                        break
                    block.append(ln2)
            add_after_eof.append(("top", path, block))
            user_paths.add(path)
            for b in block:
                sk = _split_key(b)
                if sk and sk[0] > 0:
                    user_paths.add(f"{key}.{sk[1]}")
        else:
            # nested thiếu, parent đã có trong user → chèn cuối block parent
            if parent in top_last:
                inserts.setdefault(parent, []).append(line)
                user_paths.add(path)
            # parent KHÔNG có trong user → sẽ được xử lý khi gặp top-level parent thiếu ở vòng này (đã thêm ở nhánh trên)
        if path not in added:
            added.append(path)

    # Thực hiện chèn nested-existing (xử lý từ index lớn → nhỏ để không lệch offset).
    for parent in sorted(inserts.keys(), key=lambda p: top_last[p], reverse=True):
        idx = top_last[parent]
        ins = [_nl(x) for x in inserts[parent]]
        # đảm bảo dòng tại idx có newline
        out[idx] = _nl(out[idx])
        out[idx + 1:idx + 1] = ins

    # Thêm top-level block mới ở cuối file.
    if add_after_eof:
        if out and not out[-1].endswith("\n"):
            out[-1] = _nl(out[-1])
        if out and out[-1].strip():
            out.append("\n")
        for _kind, _path, block in add_after_eof:
            for b in block:
                out.append(_nl(b))

    return out, added


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
    except OSError as e:
        print(json.dumps({"error": f"không đọc được user config: {e}"}), file=sys.stderr)
        return 2
    try:
        with open(args.example, encoding="utf-8") as f:
            example_lines = f.readlines()
    except OSError as e:
        print(json.dumps({"error": f"không đọc được example config: {e}"}), file=sys.stderr)
        return 2

    merged, added = merge(user_lines, example_lines)

    if args.write:
        if added:
            with open(args.user, "w", encoding="utf-8") as f:
                f.writelines(merged)
    else:
        sys.stdout.write("".join(merged))

    if not args.quiet:
        print(json.dumps({"added": added, "unchanged": not added}, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
