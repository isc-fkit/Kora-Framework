#!/usr/bin/env python3
"""
schedule.py — Quản lý LỊCH cấp HỆ ĐIỀU HÀNH cho Kora (chạy cả khi đóng app Claude).

register | list | edit | remove | enable | disable. Ghi registry tools/kora-scheduler/schedules.json VÀ cài
artifact OS tương ứng:
  - macOS  → launchd plist ~/Library/LaunchAgents/com.kora.scheduler.<id>.plist
  - Linux  → khối crontab có tag '# >>> KORA <id>' … '# <<< KORA <id>'
  - Windows→ Task Scheduler 'Kora\\<id>' (schtasks)
Mỗi lần chạy gọi: <python> tools/kora-scheduler/orchestrator.py --run <id>

Chỉ thư viện chuẩn Python 3. Ví dụ:
  python3 tools/kora-scheduler/schedule.py register --id daily --cron "0 8 * * 1-5" \
        --scan jira:local,confluence:KB --post confluence:KB --email a@x.com
  python3 tools/kora-scheduler/schedule.py list
  python3 tools/kora-scheduler/schedule.py remove --id daily
"""
import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
REGISTRY = HERE / "schedules.json"
ORCH = HERE / "orchestrator.py"
PY = sys.executable or "python3"
LOG_DIR = REPO_ROOT / "reports" / "scheduler-logs"


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def detect_os(arg):
    if arg and arg != "auto":
        return arg
    s = platform.system().lower()
    return {"darwin": "macos", "linux": "linux", "windows": "windows"}.get(s, s)


def load_registry():
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {"version": 1, "schedules": []}


def save_registry(data):
    REGISTRY.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def split_list(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


# ───────────────────────────── cron → OS ───────────────────────────────────
_CRON_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]  # minute, hour, dom, mon, dow


def cron_fields(cron):
    parts = (cron or "").split()
    if len(parts) != 5:
        raise ValueError(f"cron phải có 5 trường, nhận: '{cron}'")
    # Soát khoảng giá trị (bỏ qua '*' và '*/N') để chặn cron rác kiểu '99 99 * * *'.
    for val, (lo, hi) in zip(parts, _CRON_RANGES):
        if val == "*" or val.startswith("*/"):
            continue
        for chunk in val.split(","):
            for x in chunk.split("-"):
                if not x.isdigit() or not (lo <= int(x) <= hi):
                    raise ValueError(f"cron trường '{val}' ngoài khoảng [{lo},{hi}]")
    return parts  # [minute, hour, dom, mon, dow]


def _expand(field):
    """'*'→[None]; '1-5'→[1,2,3,4,5]; '8,12'→[8,12]; '8'→[8]."""
    if field == "*":
        return [None]
    vals = []
    for chunk in field.split(","):
        if "-" in chunk:
            a, b = chunk.split("-")
            vals.extend(range(int(a), int(b) + 1))
        else:
            vals.append(int(chunk))
    return vals


def cron_to_launchd(cron):
    """Trả ('interval', seconds) hoặc ('calendar', [dict,...]).

    Hỗ trợ NHIỀU mốc giờ/phút: sinh MỘT StartCalendarInterval cho MỖI tổ hợp
    (minute × hour × weekday × day × month) — nên '0 8,12,17 * * 1-5' chạy ĐỦ
    3 mốc giờ × 5 ngày (trước đây chỉ lấy mốc đầu)."""
    m, h, dom, mon, dow = cron_fields(cron)
    if m.startswith("*/") and h == "*" and dom == "*" and mon == "*" and dow == "*":
        return "interval", int(m[2:]) * 60
    if h.startswith("*/") and m.isdigit() and dom == "*" and mon == "*" and dow == "*":
        return "interval", int(h[2:]) * 3600

    dicts = []
    for mo in _expand(mon):
        for d_ow in _expand(dow):
            for d_om in _expand(dom):
                for hh in _expand(h):
                    for mm in _expand(m):
                        entry = {}
                        if mm is not None:
                            entry["Minute"] = mm
                        if hh is not None:
                            entry["Hour"] = hh
                        if d_ow is not None:
                            entry["Weekday"] = d_ow % 7  # launchd: 0/7=CN
                        if d_om is not None:
                            entry["Day"] = d_om
                        if mo is not None:
                            entry["Month"] = mo
                        dicts.append(entry or {"Minute": 0})
    return "calendar", dicts


def build_cron(times, days):
    """Dựng cron 5-trường từ danh sách mốc giờ + chế độ ngày (cho UI thân thiện).

    times: ['08:00','14:00'] — PHẢI cùng số phút (cron 1 dòng không biểu diễn được
           phút khác nhau; mốc khác phút → tạo lịch riêng).
    days : 'every'|'daily'|'*'  → mọi ngày
           'mon-fri'|'weekday'   → thứ 2–6 (1-5)
           '1,3,5' | 'mon,wed,fri' → ngày tùy chọn.
    """
    pairs = []
    for t in times:
        t = t.strip()
        if ":" not in t:
            raise ValueError(f"giờ '{t}' phải dạng HH:MM")
        hh, mm = t.split(":", 1)
        if not (hh.isdigit() and mm.isdigit() and 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
            raise ValueError(f"giờ '{t}' không hợp lệ (HH:MM, 00:00–23:59)")
        pairs.append((int(hh), int(mm)))
    if not pairs:
        raise ValueError("cần ít nhất 1 mốc giờ")
    minutes = {p[1] for p in pairs}
    if len(minutes) > 1:
        raise ValueError("các mốc giờ phải CÙNG số phút (vd 08:00 & 14:00). "
                         "Mốc khác phút → tạo lịch riêng cho mốc đó.")
    minute = pairs[0][1]
    hours = ",".join(str(x) for x in sorted({p[0] for p in pairs}))
    dmap = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 0}
    d = (days or "every").strip().lower()
    if d in ("every", "everyday", "daily", "*", ""):
        dow = "*"
    elif d in ("mon-fri", "monfri", "weekday", "weekdays", "1-5"):
        dow = "1-5"
    else:
        nums = []
        for tok in d.replace(" ", "").split(","):
            if tok.isdigit():
                nums.append(tok)
            elif tok in dmap:
                nums.append(str(dmap[tok]))
            else:
                raise ValueError(f"ngày '{tok}' không hợp lệ (mon..sun hoặc 0-7)")
        dow = ",".join(nums) if nums else "*"
    return f"{minute} {hours} * * {dow}"


def label_of(sid):
    return f"com.kora.scheduler.{sid}"


def plist_path(sid):
    return Path.home() / "Library" / "LaunchAgents" / f"{label_of(sid)}.plist"


def build_plist(sid, cron):
    kind, val = cron_to_launchd(cron)
    logf = LOG_DIR / f"{sid}.log"
    args_xml = "".join(f"      <string>{a}</string>\n"
                       for a in [PY, str(ORCH), "--run", sid])
    if kind == "interval":
        sched_xml = f"  <key>StartInterval</key>\n  <integer>{val}</integer>\n"
    else:
        if len(val) == 1:
            inner = "".join(f"    <key>{k}</key><integer>{v}</integer>\n" for k, v in val[0].items())
            sched_xml = f"  <key>StartCalendarInterval</key>\n  <dict>\n{inner}  </dict>\n"
        else:
            items = ""
            for d in val:
                inner = "".join(f"      <key>{k}</key><integer>{v}</integer>\n" for k, v in d.items())
                items += f"    <dict>\n{inner}    </dict>\n"
            sched_xml = f"  <key>StartCalendarInterval</key>\n  <array>\n{items}  </array>\n"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{label_of(sid)}</string>
  <key>ProgramArguments</key>
  <array>
{args_xml}  </array>
  <key>WorkingDirectory</key><string>{REPO_ROOT}</string>
  <key>StandardOutPath</key><string>{logf}</string>
  <key>StandardErrorPath</key><string>{logf}</string>
  <key>RunAtLoad</key><false/>
{sched_xml}</dict>
</plist>
"""


def install_macos(sid, cron):
    """Trả (artifact, ok). ok=False nếu launchctl load thất bại (caller sẽ enabled=false)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    p = plist_path(sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(build_plist(sid, cron), encoding="utf-8")
    except OSError as e:
        print(f"⚠️  Không ghi được plist: {e}", file=sys.stderr)
        return str(p), False
    subprocess.run(["launchctl", "unload", str(p)], capture_output=True)
    r = subprocess.run(["launchctl", "load", str(p)], capture_output=True, text=True)
    ok = r.returncode == 0
    if not ok:
        print(f"⚠️  launchctl load báo: {r.stderr.strip()}", file=sys.stderr)
    return str(p), ok


def remove_macos(sid):
    p = plist_path(sid)
    if p.exists():
        subprocess.run(["launchctl", "unload", str(p)], capture_output=True)
        p.unlink()
        return True
    return False


def _cron_command(sid):
    logf = LOG_DIR / f"{sid}.log"
    return f'cd "{REPO_ROOT}" && {PY} tools/kora-scheduler/orchestrator.py --run {sid} >> "{logf}" 2>&1'


def _read_crontab():
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def _write_crontab(text):
    p = subprocess.run(["crontab", "-"], input=text, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)


def _strip_block(text, sid):
    out, skip = [], False
    for ln in text.splitlines():
        if ln.strip() == f"# >>> KORA {sid}":
            skip = True
            continue
        if ln.strip() == f"# <<< KORA {sid}":
            skip = False
            continue
        if not skip:
            out.append(ln)
    return "\n".join(out).strip()


def install_linux(sid, cron):
    """Trả (artifact, ok). ok=False nếu ghi crontab thất bại."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        cur = _strip_block(_read_crontab(), sid)
        block = f"# >>> KORA {sid}\n{cron} {_cron_command(sid)}\n# <<< KORA {sid}"
        new = (cur + "\n" + block + "\n").lstrip("\n")
        _write_crontab(new)
        return f"crontab:KORA {sid}", True
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  crontab báo: {e}", file=sys.stderr)
        return f"crontab:KORA {sid}", False


def remove_linux(sid):
    cur = _read_crontab()
    if f"# >>> KORA {sid}" not in cur:
        return False
    _write_crontab(_strip_block(cur, sid) + "\n")
    return True


_WDAY_NAMES = {0: "SUN", 1: "MON", 2: "TUE", 3: "WED", 4: "THU", 5: "FRI", 6: "SAT", 7: "SUN"}


def _win_days(dow):
    """'1-5'→'MON,TUE,WED,THU,FRI'; '1,3,5'→'MON,WED,FRI'; '*'→'' (nghĩa là DAILY).

    SỬA lỗi cũ: trước đây dùng dow.replace('-', ',') nên '1-5' biến thành 'MON,FRI'
    (mất T3/T4/T5). Nay expand range đầy đủ."""
    nums = _expand(dow)
    if nums == [None]:
        return ""
    return ",".join(_WDAY_NAMES.get(n % 7, "MON") for n in nums)


def _win_task_specs(sid, cron):
    """Trả [(task_name, schtasks_args), ...] — MỘT task cho MỖI mốc giờ.

    schtasks /create chỉ nhận 1 /st → nhiều mốc giờ ⇒ nhiều task (tên có hậu tố giờ),
    để '0 8,14 * * 1-5' tạo đủ 2 mốc 08:00 và 14:00 (trước đây gộp về 1 mốc)."""
    m, h, dom, mon, dow = cron_fields(cron)
    # /tr là MỘT chuỗi; path có dấu cách → bọc nháy escape \" cho schtasks.
    tr = f'\\"{PY}\\" \\"{ORCH}\\" --run {sid}'
    if m.startswith("*/"):
        tn = f"Kora\\{sid}"
        return [(tn, ["schtasks", "/create", "/tn", tn, "/tr", tr,
                      "/sc", "MINUTE", "/mo", m[2:], "/f"])]
    minute = int(m.split(",")[0]) if m.split(",")[0].split("-")[0].isdigit() else 0
    hours = [x for x in _expand(h) if x is not None] or [8]
    days = _win_days(dow)
    specs = []
    for i, hh in enumerate(sorted(set(hours))):
        st = f"{int(hh):02d}:{int(minute):02d}"
        tn = f"Kora\\{sid}" if i == 0 else f"Kora\\{sid}__{int(hh):02d}{int(minute):02d}"
        if days:
            args = ["schtasks", "/create", "/tn", tn, "/tr", tr,
                    "/sc", "WEEKLY", "/d", days, "/st", st, "/f"]
        else:
            args = ["schtasks", "/create", "/tn", tn, "/tr", tr,
                    "/sc", "DAILY", "/st", st, "/f"]
        specs.append((tn, args))
    return specs


def _schtasks_args(sid, cron):
    """(Tương thích ngược) arg-list của task ĐẦU TIÊN — dùng cho self-check/đơn-mốc."""
    return _win_task_specs(sid, cron)[0][1]


def install_windows(sid, cron, native):
    """Trả (artifact, ok). Tạo 1 task cho mỗi mốc giờ; ok=False nếu BẤT KỲ task nào lỗi."""
    specs = _win_task_specs(sid, cron)
    names = [tn for tn, _ in specs]
    artifact = "schtasks:" + ",".join(names)
    if native:
        ok = True
        for tn, args in specs:
            r = subprocess.run(args, capture_output=True, text=True)
            if r.returncode != 0:
                ok = False
                print(f"⚠️  schtasks báo ({tn}): {r.stderr.strip()}", file=sys.stderr)
        return artifact, ok
    print("ℹ️  Chạy (các) lệnh sau trên Windows để tạo lịch:")
    for _, args in specs:
        print("   " + " ".join(f'"{c}"' if " " in c else c for c in args))
    return artifact, True


def remove_windows(sid, native, cron=None):
    """Xóa MỌI task của lịch (kể cả các mốc giờ phụ Kora\\<id>__HHMM)."""
    names = [f"Kora\\{sid}"]
    if cron:
        try:
            names = [tn for tn, _ in _win_task_specs(sid, cron)]
        except Exception:  # noqa: BLE001
            pass
    removed = False
    for tn in names:
        cmd = ["schtasks", "/delete", "/tn", tn, "/f"]
        if native:
            r = subprocess.run(cmd, capture_output=True)
            removed = removed or (r.returncode == 0)
        else:
            print("ℹ️  Chạy trên Windows: " + " ".join(cmd))
    return removed


INSTALL_FAIL_HINT = ("CHƯA cài được vào HĐH — lịch đã LƯU nhưng để enabled=false. "
                     "Thử lại 'enable --id <id>', hoặc dùng cơ chế Cowork trong /kora-schedule làm fallback.")


def _os_install(osname, sid, cron, native):
    """Trả (artifact, ok). Cài chéo-OS (không native) coi như deferred → ok=True."""
    if osname == "macos":
        return install_macos(sid, cron) if native else ("(plist sẽ tạo trên macOS)", True)
    if osname == "linux":
        return install_linux(sid, cron) if native else ("(crontab trên Linux)", True)
    if osname == "windows":
        return install_windows(sid, cron, native)
    return "", True


def _os_remove(osname, sid, native, cron=None):
    if osname == "macos":
        return remove_macos(sid)
    if osname == "linux":
        return remove_linux(sid)
    if osname == "windows":
        return remove_windows(sid, native, cron)
    return False


# ───────────────────────────── lệnh chính ──────────────────────────────────
def cmd_register(args):
    osname = detect_os(args.os)
    native = osname == detect_os("auto")
    cron_fields(args.cron)  # validate sớm (chặn cron rác)
    sid = args.id
    if osname not in ("macos", "linux", "windows"):
        print(f"❌ OS không hỗ trợ: {osname}", file=sys.stderr); sys.exit(1)
    if osname == "macos" and not native:
        print("ℹ️  Lịch macOS chỉ cài được trên máy macOS.")

    reg = load_registry()
    reg["schedules"] = [s for s in reg["schedules"] if s.get("id") != sid]  # replace-in-place
    artifact, ok = _os_install(osname, sid, args.cron, native)

    rp = getattr(args, "report_projects", None)
    st = getattr(args, "sync_targets", None)
    entry = {
        "id": sid, "cron": args.cron, "freq_human": args.freq_human or args.cron,
        "scan_list": split_list(args.scan), "post_list": split_list(args.post),
        "report": {"enabled": rp is not None, "projects": split_list(rp), "members": []},
        "email": {"enabled": bool(args.email),
                  "provider": getattr(args, "mail_provider", None) or "smtp",
                  "to": split_list(args.email)},
        "sync": {"enabled": bool(split_list(st)), "targets": split_list(st), "password_gated": True},
        "enabled": ok, "os_engine": {"macos": "launchd", "linux": "cron", "windows": "schtasks"}[osname],
        "os_artifact": artifact, "created_at": now_iso(), "updated_at": now_iso(),
    }
    if not ok:
        entry["install_error"] = INSTALL_FAIL_HINT
    reg["schedules"].append(entry)
    save_registry(reg)
    if ok:
        print(f"✅ Đã đăng ký lịch '{sid}' ({osname}, {args.cron}). Scan={entry['scan_list']} "
              f"Post={entry['post_list']} → {artifact}")
    else:
        print(f"⚠️  Lịch '{sid}' đã LƯU vào danh sách nhưng {INSTALL_FAIL_HINT}")
    _warn_if_ops_pw_missing()


def _warn_if_ops_pw_missing():
    """Lịch nền gác CẢ lượt bằng KORA_OPS_PW. launchd/cron không có shell env → cần file ops-pw.env.
    Thiếu file → mỗi lượt nền bỏ TOÀN BỘ. Nhắc user tạo (KHÔNG in/hỏi mật khẩu)."""
    candidates = [Path.home() / ".config" / "kora" / "ops-pw.env",
                  Path.home() / ".kora" / "ops-pw.env"]
    if any(p.exists() for p in candidates):
        return
    target = candidates[0]
    print("🔑 LƯU Ý: lịch nền cần mật khẩu vận hành trong file (launchd/cron không có shell env).")
    print(f"   Tạo 1 lần:  mkdir -p \"{target.parent}\" && printf 'KORA_OPS_PW=<mật khẩu>\\n' > \"{target}\" && chmod 600 \"{target}\"")
    print("   (Windows: %USERPROFILE%\\.kora\\ops-pw.env). Thiếu file → mỗi lượt nền BỎ TOÀN BỘ (kể cả scan).")


def cmd_remove(args):
    osname = detect_os(args.os)
    native = osname == detect_os("auto")
    sid = args.id
    reg = load_registry()
    entry = next((s for s in reg["schedules"] if s.get("id") == sid), None)
    cron = entry.get("cron") if entry else None
    removed = _os_remove(osname, sid, native, cron)
    before = len(reg["schedules"])
    reg["schedules"] = [s for s in reg["schedules"] if s.get("id") != sid]
    save_registry(reg)
    print(f"✅ Đã gỡ lịch '{sid}' (artifact OS: {'có' if removed else 'không thấy'}, "
          f"registry: {'đã xoá' if len(reg['schedules']) < before else 'không có'}).")


def cmd_disable(args):
    """Tắt (inactive): gỡ artifact OS nhưng GIỮ entry trong registry (enabled=false)."""
    reg = load_registry()
    entry = next((s for s in reg["schedules"] if s.get("id") == args.id), None)
    if not entry:
        print(f"❌ Không thấy lịch '{args.id}'", file=sys.stderr); sys.exit(1)
    osname = detect_os(args.os); native = osname == detect_os("auto")
    removed = _os_remove(osname, args.id, native, entry.get("cron"))
    entry["enabled"] = False
    entry["updated_at"] = now_iso()
    save_registry(reg)
    print(f"⏸️  Đã TẮT (inactive) lịch '{args.id}' — gỡ artifact OS ({'có' if removed else 'không thấy'}), "
          f"vẫn giữ trong danh sách (bật lại: enable --id {args.id}).")


def cmd_enable(args):
    """Bật (active): cài lại artifact OS từ cron đã lưu (enabled=true)."""
    reg = load_registry()
    entry = next((s for s in reg["schedules"] if s.get("id") == args.id), None)
    if not entry:
        print(f"❌ Không thấy lịch '{args.id}'", file=sys.stderr); sys.exit(1)
    osname = detect_os(args.os); native = osname == detect_os("auto")
    cron_fields(entry.get("cron", ""))
    artifact, ok = _os_install(osname, args.id, entry["cron"], native)
    entry["enabled"] = ok
    entry["os_artifact"] = artifact
    if ok:
        entry.pop("install_error", None)
    else:
        entry["install_error"] = INSTALL_FAIL_HINT
    entry["updated_at"] = now_iso()
    save_registry(reg)
    if ok:
        print(f"▶️  Đã BẬT (active) lịch '{args.id}' ({osname}, {entry.get('cron')}) → {artifact}.")
    else:
        print(f"⚠️  Bật lịch '{args.id}' nhưng {INSTALL_FAIL_HINT}")


def cmd_edit(args):
    reg = load_registry()
    entry = next((s for s in reg["schedules"] if s.get("id") == args.id), None)
    if not entry:
        print(f"❌ Không thấy lịch '{args.id}'", file=sys.stderr); sys.exit(1)
    cron_changed = args.cron and args.cron != entry["cron"]
    if args.cron:
        entry["cron"] = args.cron
        entry["freq_human"] = args.freq_human or args.cron
    if args.scan is not None:
        entry["scan_list"] = split_list(args.scan)
    if args.post is not None:
        entry["post_list"] = split_list(args.post)
    if args.report_projects is not None:
        entry["report"] = {"enabled": True, "projects": split_list(args.report_projects),
                           "members": entry.get("report", {}).get("members", [])}
    if args.email is not None or args.mail_provider is not None:
        em = entry.get("email", {"enabled": False, "provider": "smtp", "to": []})
        if args.email is not None:
            em["enabled"] = bool(args.email)
            em["to"] = split_list(args.email)
        if args.mail_provider is not None:
            em["provider"] = args.mail_provider
        entry["email"] = em
    if args.sync_targets is not None:
        entry["sync"] = {"enabled": bool(split_list(args.sync_targets)),
                         "targets": split_list(args.sync_targets), "password_gated": True}
    entry["updated_at"] = now_iso()
    save_registry(reg)
    # scan/post/email/report/sync đọc lúc chạy → KHÔNG cần cài lại OS; chỉ cài lại khi đổi giờ.
    if cron_changed:
        cmd_register(argparse.Namespace(
            id=args.id, cron=entry["cron"], freq_human=entry["freq_human"],
            scan=",".join(entry["scan_list"]), post=",".join(entry["post_list"]),
            email=",".join(entry.get("email", {}).get("to", [])),
            mail_provider=entry.get("email", {}).get("provider", "smtp"),
            report_projects=",".join(entry.get("report", {}).get("projects", [])),
            sync_targets=",".join(entry.get("sync", {}).get("targets", [])), os=args.os))
    else:
        print(f"✅ Đã cập nhật '{args.id}' (scan/post/email đọc lúc chạy — không cài lại OS).")


def cmd_list(args):
    reg = load_registry()
    schedules = reg.get("schedules", [])
    if not schedules:
        print("ℹ️  Chưa có lịch HĐH nào. Tạo bằng: schedule.py register …")
    else:
        print(f"{'ID':18} {'ENGINE':9} {'CRON':16} {'ENABLED':8} SCAN→POST | report/mail/sync")
        for s in schedules:
            em, sy, rp = s.get("email", {}), s.get("sync", {}), s.get("report", {})
            extra = []
            if rp.get("enabled"):
                extra.append(f"report={','.join(rp.get('projects', [])) or 'all'}")
            if em.get("enabled"):
                extra.append(f"mail:{em.get('provider', 'smtp')}→{','.join(em.get('to', []))}")
            if sy.get("enabled"):
                extra.append(f"sync🔒:{','.join(sy.get('targets', []))}")
            if s.get("install_error"):
                extra.append("⚠️CHƯA-CÀI-HĐH")
            print(f"{s['id']:18} {s.get('os_engine','?'):9} {s.get('cron','?'):16} "
                  f"{str(s.get('enabled')):8} {','.join(s.get('scan_list',[]))}→{','.join(s.get('post_list',[]))}"
                  + ("  | " + "  ".join(extra) if extra else ""))
    # đối chiếu OS thật (bọc try — công cụ lịch có thể không có trên máy hiện tại)
    osname = detect_os(args.os)
    print("\n— Artifact OS thực tế —")
    try:
        if osname == "macos":
            r = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
            hits = [ln for ln in r.stdout.splitlines() if "com.kora.scheduler" in ln]
            print("\n".join(hits) or "(không thấy launchd job com.kora.scheduler)")
        elif osname == "linux":
            cur = _read_crontab()
            hits = [ln for ln in cur.splitlines() if "KORA" in ln or "orchestrator.py" in ln]
            print("\n".join(hits) or "(không thấy khối KORA trong crontab)")
        elif osname == "windows":
            r = subprocess.run(["schtasks", "/query", "/fo", "LIST"], capture_output=True, text=True)
            hits = [ln for ln in r.stdout.splitlines() if "Kora" in ln]
            print("\n".join(hits) or "(không thấy task Kora)")
    except FileNotFoundError:
        print(f"(công cụ lịch của '{osname}' không có trên máy này — chạy schedule.py TRÊN máy đích)")


def main():
    ap = argparse.ArgumentParser(description="Quản lý lịch HĐH Kora.")
    sub = ap.add_subparsers(dest="action", required=True)

    def add_common(p):
        p.add_argument("--id", required=True)
        p.add_argument("--cron")
        p.add_argument("--times", help="Mốc giờ HH:MM, cách nhau phẩy (vd 08:00,14:00) — cùng số phút. "
                                       "Dùng kèm --days; là cách thân thiện thay cho --cron.")
        p.add_argument("--days", help="every|daily | mon-fri|weekday | csv (1-5 / mon,wed,fri)")
        p.add_argument("--freq-human", dest="freq_human")
        p.add_argument("--scan")
        p.add_argument("--post")
        p.add_argument("--email")
        p.add_argument("--mail-provider", dest="mail_provider", help="smtp|gmail|outlook")
        p.add_argument("--report-projects", dest="report_projects",
                       help="Project keys cho report, cách nhau dấu phẩy (rỗng = tất cả)")
        p.add_argument("--sync-targets", dest="sync_targets",
                       help="confluence,github — bật bước SYNC (có cổng mật khẩu) trong lịch")
        p.add_argument("--os", default="auto", help="auto|macos|linux|windows")

    pr = sub.add_parser("register"); add_common(pr); pr.set_defaults(func=cmd_register)
    pe = sub.add_parser("edit"); add_common(pe); pe.set_defaults(func=cmd_edit)
    prm = sub.add_parser("remove")
    prm.add_argument("--id", required=True); prm.add_argument("--os", default="auto")
    prm.set_defaults(func=cmd_remove)
    pl = sub.add_parser("list"); pl.add_argument("--os", default="auto"); pl.set_defaults(func=cmd_list)
    pen = sub.add_parser("enable"); pen.add_argument("--id", required=True); pen.add_argument("--os", default="auto"); pen.set_defaults(func=cmd_enable)
    pdi = sub.add_parser("disable"); pdi.add_argument("--id", required=True); pdi.add_argument("--os", default="auto"); pdi.set_defaults(func=cmd_disable)

    args = ap.parse_args()
    # UI thân thiện: --times/--days → dựng cron (ưu tiên hơn --cron nếu được truyền).
    if getattr(args, "times", None):
        try:
            args.cron = build_cron(split_list(args.times), getattr(args, "days", None) or "every")
            if not getattr(args, "freq_human", None):
                args.freq_human = f"{args.times} ({getattr(args, 'days', None) or 'every'})"
        except ValueError as e:
            ap.error(str(e))
    if args.action == "register" and not args.cron:
        ap.error("register cần --cron (hoặc --times [--days])")
    args.func(args)


if __name__ == "__main__":
    main()
