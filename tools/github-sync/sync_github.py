#!/usr/bin/env python3
"""
sync_github.py — Đẩy Knowledge Base → repo GitHub RIÊNG TƯ (private) qua GIT PUSH.

Anh em với tools/confluence-sync: cùng triết lý "gom tri thức cục bộ → đẩy lên 1 nơi chung",
nhưng target là 1 git repo. Đây là đường HEADLESS (chạy được trong cron/scheduler).

Bảo mật:
  - PAT đọc từ tools/github-sync/.env.local (KORA_GITHUB_SYNC_TOKEN) — đã gitignore.
  - Token KHÔNG vào .git/config, KHÔNG vào argv/ps: bơm qua GIT_CONFIG_* (env) dưới dạng
    http.extraHeader. Mọi output git đều được "scrub" token trước khi in.
  - Repo đích là 1 GƯƠNG (mirror sink) 1 chiều: mỗi push reset cứng worktree theo origin rồi
    chép lại note → KHÔNG có khái niệm "skip_human_edited" (lịch sử git là vết kiểm toán).

Chỉ thư viện chuẩn Python 3 + lệnh `git`. Tái dùng helper của sync_confluence.

Ví dụ:
  python3 tools/github-sync/sync_github.py --check
  python3 tools/github-sync/sync_github.py --push --dry-run
  python3 tools/github-sync/sync_github.py --push
  python3 tools/github-sync/sync_github.py --pull
  # Windows: thay python3 bằng py
"""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Tái dùng helper của confluence-sync (load_env/load_config/vault_dir/parse_note/collect_notes/...).
sys.path.insert(0, str(HERE.parents[0] / "confluence-sync"))
import sync_confluence as cs  # noqa: E402

REPO_ROOT = cs.REPO_ROOT
WORK_DIR = HERE / "work"
TOKEN_KEYS = ("KORA_GITHUB_SYNC_TOKEN", "KORA_GITHUB_TOKEN", "GITHUB_TOKEN")


# ───────────────────────────── tiện ích ──────────────────────────────
def die(msg, code=1):
    cs.die(msg, code)


def warn(msg):
    cs.warn(msg)


def resolve_token(env: dict) -> str:
    for k in TOKEN_KEYS:
        v = env.get(k) or os.getenv(k)
        if v and not v.strip().startswith("PASTE_"):
            return v.strip()
    return ""


def scrub(text: str, token: str) -> str:
    if not text:
        return text
    if token:
        text = text.replace(token, "***")
        try:
            b64 = base64.b64encode(("x-access-token:" + token).encode()).decode()
            text = text.replace(b64, "***")
        except Exception:  # noqa: BLE001
            pass
    return text


def gh_cfg(cfg: dict, args) -> dict:
    repo = (getattr(args, "repo", None) or cfg.get("github.repo") or "").strip().strip("/")
    if "/" not in repo:
        die("Thiếu repo đích. Đặt github.repo = \"owner/name\" trong config hoặc truyền --repo.")
    base_url = (cfg.get("github.base_url") or "https://github.com").rstrip("/")
    return {
        "repo": repo,
        "owner": repo.split("/")[0],
        "name": repo.split("/", 1)[1],
        "branch": getattr(args, "branch", None) or cfg.get("github.branch") or "main",
        "base_url": base_url,
        "url": f"{base_url}/{repo}.git",
        "permission": (cfg.get("github.permission") or "read_write").lower(),
        "source": getattr(args, "source", None) or cfg.get("github.push.source") or "both",
        "scope": getattr(args, "scope", None) or cfg.get("github.push.scope") or "",
        "subdir": (getattr(args, "subdir", None) or cfg.get("github.push.subdir") or "").strip("/"),
        "slug": repo.replace("/", "-"),
    }


def git_env(token: str) -> dict:
    """Env cho git: bơm token qua GIT_CONFIG_* (KHÔNG vào argv/ps/.git-config); tắt prompt."""
    e = dict(os.environ)
    e["GIT_TERMINAL_PROMPT"] = "0"
    e.setdefault("GIT_AUTHOR_NAME", os.getenv("KORA_GITHUB_SYNC_AUTHOR_NAME", "Kora Sync"))
    e.setdefault("GIT_AUTHOR_EMAIL", os.getenv("KORA_GITHUB_SYNC_AUTHOR_EMAIL", "kora-sync@local"))
    e["GIT_COMMITTER_NAME"] = e["GIT_AUTHOR_NAME"]
    e["GIT_COMMITTER_EMAIL"] = e["GIT_AUTHOR_EMAIL"]
    if token:
        hdr = "Authorization: Basic " + base64.b64encode(
            ("x-access-token:" + token).encode()).decode()
        e["GIT_CONFIG_COUNT"] = "1"
        e["GIT_CONFIG_KEY_0"] = "http.extraHeader"
        e["GIT_CONFIG_VALUE_0"] = hdr
    return e


def run_git(args, cwd, token, check=True):
    """Chạy git, trả (rc, stdout, stderr) đã scrub token. Không bao giờ in token."""
    p = subprocess.run(["git"] + args, cwd=str(cwd) if cwd else None,
                       env=git_env(token), capture_output=True, text=True)
    out, err = scrub(p.stdout, token), scrub(p.stderr, token)
    if check and p.returncode != 0:
        die(f"git {args[0]} lỗi (rc={p.returncode}): {err.strip() or out.strip()}")
    return p.returncode, out, err


def gh_sysdir(cfg: dict) -> Path:
    d = cs.vault_dir(cfg) / "_system" / "github"
    d.mkdir(parents=True, exist_ok=True)
    return d


def map_path(cfg, g) -> Path:
    return gh_sysdir(cfg) / f"github-map-{g['owner']}-{g['name']}.json"


def load_map(cfg, g) -> dict:
    p = map_path(cfg, g)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"repo": g["repo"], "branch": g["branch"], "subdir": g["subdir"], "files": {}}


def save_map(cfg, g, data):
    data["generated_at"] = cs.now_iso()
    map_path(cfg, g).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def content_hash(title, body) -> str:
    return "sha256:" + hashlib.sha256((title + "\n" + body).encode("utf-8")).hexdigest()


def plan_files(cfg, g):
    """Trả list (kb_id, title, body, source_rel, repo_rel, content_hash) cho note sẽ đẩy."""
    notes = cs.collect_notes(cfg, g["source"], g["scope"])
    out = []
    for path in notes:
        kb_id, title, body = cs.parse_note(path)
        source_rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        repo_rel = (g["subdir"] + "/" + source_rel).lstrip("/") if g["subdir"] else source_rel
        out.append((kb_id, title, body, source_rel, repo_rel, content_hash(title, body)))
    return out


# ──────────────────────────── git worktree ─────────────────────────────
def ensure_worktree(cfg, g, token) -> Path:
    """Clone (lần đầu) hoặc fetch+reset cứng worktree về đúng branch của origin."""
    wt = WORK_DIR / g["slug"]
    if not (wt / ".git").exists():
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        if wt.exists():
            shutil.rmtree(wt, ignore_errors=True)
        run_git(["clone", "--no-tags", g["url"], str(wt)], cwd=None, token=token)
    run_git(["remote", "set-url", "origin", g["url"]], cwd=wt, token=token)
    run_git(["fetch", "--no-tags", "origin"], cwd=wt, token=token)
    # branch có trên origin? → checkout + reset cứng; chưa có → tạo nhánh mới (orphan-ish).
    rc, out, _ = run_git(["ls-remote", "--heads", "origin", g["branch"]], cwd=wt, token=token,
                         check=False)
    if out.strip():
        run_git(["checkout", "-B", g["branch"], f"origin/{g['branch']}"], cwd=wt, token=token)
        run_git(["reset", "--hard", f"origin/{g['branch']}"], cwd=wt, token=token)
    else:
        run_git(["checkout", "-B", g["branch"]], cwd=wt, token=token)
    return wt


# ──────────────────────────────── lệnh ─────────────────────────────────
def cmd_check(cfg, g, token):
    if not token:
        die("Chưa có token. Tạo tools/github-sync/.env.local (copy .env.example) và điền "
            "KORA_GITHUB_SYNC_TOKEN = PAT (scope 'repo').")
    rc, out, err = run_git(["ls-remote", "--heads", g["url"]], cwd=None, token=token, check=False)
    if rc != 0:
        die(f"Không truy cập được repo {g['repo']} (kiểm tra token/quyền/private): "
            f"{(err or out).strip()[:200]}")
    nbranch = len([l for l in out.splitlines() if l.strip()])
    print(f"✅ Kết nối GitHub OK — repo {g['repo']} ({nbranch} nhánh) — branch đích: {g['branch']}")
    return 0


def cmd_push(cfg, g, token, dry_run=False, force=False):
    if g["permission"] == "read_only":
        die("github.permission = read_only → KHÔNG được đẩy (push).")
    if not token and not dry_run:
        die("Chưa có token. Điền KORA_GITHUB_SYNC_TOKEN trong tools/github-sync/.env.local.")

    files = plan_files(cfg, g)
    if not files:
        print("ℹ️  Không có note nào để đẩy."); return 0
    cmap = load_map(cfg, g)
    prev = cmap.get("files", {})

    if dry_run:
        create = update = 0
        for kb_id, title, _b, _s, repo_rel, ch in files:
            rec = prev.get(kb_id)
            if rec and rec.get("content_hash") == ch and not force:
                continue
            if rec:
                update += 1; act = "update"
            else:
                create += 1; act = "create"
            print(f"  [dry] {act}: {repo_rel}  ({kb_id})")
        new_paths = {f[4] for f in files}
        deletes = [r.get("repo_path") for r in prev.values() if r.get("repo_path") not in new_paths]
        for d in deletes:
            print(f"  [dry] delete: {d}")
        print(f"ℹ️  [dry-run] +{create} tạo, ~{update} cập nhật, -{len(deletes)} xóa → {g['repo']}")
        return 0

    wt = ensure_worktree(cfg, g, token)
    # 1) xóa các file Kora từng quản lý (để propagate xóa), 2) chép lại bộ hiện tại.
    new_paths = {f[4] for f in files}
    for rec in prev.values():
        rp = rec.get("repo_path")
        if rp and rp not in new_paths:
            fp = wt / rp
            if fp.exists():
                fp.unlink()
    for kb_id, title, body, source_rel, repo_rel, ch in files:
        dest = wt / repo_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        # chép NGUYÊN file nguồn (giữ frontmatter) để repo phản chiếu KB cục bộ.
        shutil.copyfile(REPO_ROOT / source_rel, dest)

    run_git(["add", "-A"], cwd=wt, token=token)
    _rc, out, _ = run_git(["status", "--porcelain"], cwd=wt, token=token)
    if not out.strip():
        print(f"ℹ️  Không có thay đổi — bỏ qua commit/push ({g['repo']}).")
        # vẫn cập nhật map (hash) để lần sau so khớp.
        _save_map_from_files(cfg, g, cmap, files, wt, token)
        return 0
    run_git(["commit", "-m", f"Kora sync {cs.today_str()}"], cwd=wt, token=token)
    run_git(["push", "-u", "origin", g["branch"]], cwd=wt, token=token)
    _save_map_from_files(cfg, g, cmap, files, wt, token)
    n = len([l for l in out.splitlines() if l.strip()])
    print(f"✅ Push xong: {n} file thay đổi → {g['repo']}@{g['branch']}")
    return 0


def _save_map_from_files(cfg, g, cmap, files, wt, token):
    new = {}
    for kb_id, title, body, source_rel, repo_rel, ch in files:
        git_sha = ""
        rc, out, _ = run_git(["rev-parse", f"HEAD:{repo_rel}"], cwd=wt, token=token, check=False)
        if rc == 0:
            git_sha = out.strip()
        new[kb_id] = {
            "repo_path": repo_rel, "source_path": source_rel,
            "content_hash": ch, "last_pushed_at": cs.now_iso(), "git_sha": git_sha,
        }
    cmap["files"] = new
    cmap["repo"], cmap["branch"], cmap["subdir"] = g["repo"], g["branch"], g["subdir"]
    save_map(cfg, g, cmap)


# ───────── chuyển file GitHub → document chuẩn wiki (frontmatter + link nguồn) ─────────
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _parse_fm(text: str):
    """Tách frontmatter YAML đầu file → (dict, body). Không có thì ({}, text)."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("-"):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, text[m.end():]


def _yaml_val(v) -> str:
    s = str(v)
    if s == "" or s != s.strip() or any(c in s for c in ':#"\''):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def _emit_fm(meta: dict) -> str:
    return "---\n" + "".join(f"{k}: {_yaml_val(v)}\n" for k, v in meta.items()) + "---\n"


def _first_h1(body: str) -> str:
    m = _H1_RE.search(body)
    return m.group(1).strip() if m else ""


def _build_github_index(dest_root: Path):
    """Dựng lại trang hub _GitHub-Index.md từ MỌI document GitHub đã kéo (idempotent)."""
    if not dest_root.exists():
        return
    groups = {}
    for p in sorted(dest_root.rglob("*.md")):
        if p.name.startswith("_"):
            continue
        fm, _ = _parse_fm(p.read_text(encoding="utf-8", errors="replace"))
        if fm.get("source") != "github":
            continue
        repo = fm.get("github_repo", "?")
        rel = p.relative_to(dest_root).as_posix()
        groups.setdefault(repo, []).append(
            (fm.get("title") or p.stem, rel, fm.get("github_url", "")))
    out = [_emit_fm({"title": "GitHub — Index", "source": "github",
                     "type": "index", "generated": "true", "imported_at": cs.now_iso()}),
           "# GitHub — Index tri thức", "",
           "> Trang điều hướng TỰ SINH từ tài liệu kéo về từ GitHub (mỗi lần `--pull`). "
           "Chỉnh tay sẽ bị ghi đè.", ""]
    total = 0
    for repo in sorted(groups):
        items = sorted(groups[repo])
        out.append(f"## {repo}  ({len(items)})")
        out.append("")
        for title, rel, url in items:
            src_link = f" · [↗ nguồn]({url})" if url else ""
            out.append(f"- [{title}]({rel}){src_link}")
        out.append("")
        total += len(items)
    out.append("---")
    out.append(f"*Tổng {total} tài liệu GitHub.*")
    (dest_root / "_GitHub-Index.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def cmd_pull(cfg, g, token, dry_run=False):
    if not token:
        die("Chưa có token để pull.")
    wt = ensure_worktree(cfg, g, token)
    _rc, sha, _ = run_git(["rev-parse", "HEAD"], cwd=wt, token=token, check=False)
    commit = sha.strip()[:40]
    src = wt / g["subdir"] if g["subdir"] else wt
    dest_root = cs.vault_dir(cfg) / "GitHub"
    repo_dir = dest_root / g["slug"]               # namespace theo repo: tránh trùng đường dẫn giữa các repo
    base, repo, branch = g["base_url"], g["repo"], g["branch"]
    md = [p for p in sorted(src.rglob("*.md")) if ".git" not in p.parts]

    if dry_run:
        for p in md:
            print(f"  [dry] pull+enrich: {p.relative_to(src)}")
        print(f"  [dry] {len(md)} file → {repo_dir} (+ frontmatter, link nguồn, _GitHub-Index.md)")
        return 0

    if repo_dir.exists():
        shutil.rmtree(repo_dir, ignore_errors=True)   # đồng bộ: file xoá trên repo cũng biến mất
    n = 0
    for p in md:
        rel = p.relative_to(src)
        gh_path = ((g["subdir"] + "/") if g["subdir"] else "") + rel.as_posix()
        gh_url = f"{base}/{repo}/blob/{branch}/{urllib.parse.quote(gh_path)}"
        ofm, body = _parse_fm(p.read_text(encoding="utf-8", errors="replace"))
        title = ofm.get("title") or _first_h1(body) or p.stem
        meta = {
            "source": "github",
            "github_repo": repo,
            "github_branch": branch,
            "github_path": gh_path,
            "github_url": gh_url,
            "github_commit": commit,
            "title": title,
            "type": ofm.get("type") or "reference",
            "imported_at": cs.now_iso(),
        }
        for k, v in ofm.items():                    # giữ key gốc của repo (không đè key của ta)
            if k not in meta:
                meta[k] = v
        link = f"> 📎 Nguồn GitHub: [{repo}/{gh_path}]({gh_url})\n\n"
        out = repo_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_emit_fm(meta) + "\n" + link + body.lstrip("\n"), encoding="utf-8")
        n += 1
    _build_github_index(dest_root)
    print(f"✅ Pull xong: {n} file (đã thêm frontmatter + link nguồn) → {repo_dir}; cập nhật _GitHub-Index.md")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Đẩy KB → repo GitHub riêng tư (git push).")
    ap.add_argument("--check", action="store_true", help="Kiểm tra token + truy cập repo (không ghi).")
    ap.add_argument("--push", action="store_true", help="Đẩy KB cục bộ → repo (idempotent).")
    ap.add_argument("--pull", action="store_true", help="Kéo file repo → <vault>/GitHub/.")
    ap.add_argument("--dry-run", action="store_true", help="Chỉ in kế hoạch, KHÔNG ghi.")
    ap.add_argument("--force", action="store_true", help="Bỏ qua hash, chép lại tất cả.")
    ap.add_argument("--source", choices=["vault", "docs", "both"], help="Nguồn note để đẩy.")
    ap.add_argument("--scope", help="Lọc theo thư mục/glob khi đẩy.")
    ap.add_argument("--subdir", help="Thư mục con trong repo đích.")
    ap.add_argument("--repo", help="owner/name (mặc định github.repo).")
    ap.add_argument("--branch", help="Branch đích (mặc định github.branch).")
    args = ap.parse_args()

    env = cs.load_env(HERE / ".env.local")
    cfg = cs.load_config(REPO_ROOT / "config" / "factory-config.yaml")
    token = resolve_token(env)
    g = gh_cfg(cfg, args)

    if args.check:
        sys.exit(cmd_check(cfg, g, token))
    if args.push:
        sys.exit(cmd_push(cfg, g, token, dry_run=args.dry_run, force=args.force))
    if args.pull:
        sys.exit(cmd_pull(cfg, g, token, dry_run=args.dry_run))
    ap.print_help()


if __name__ == "__main__":
    main()
