# tools/kora-scheduler — Lịch cấp HỆ ĐIỀU HÀNH (chạy cả khi đóng app)

Khác với lịch Cowork (chỉ chạy khi app Claude mở), lịch này đăng ký **ở tầng OS** nên
**thức dậy đúng giờ kể cả khi đóng app**:

| OS | Cơ chế | Vị trí |
|---|---|---|
| macOS | launchd | `~/Library/LaunchAgents/com.kora.scheduler.<id>.plist` |
| Linux | crontab (khối có tag) | `crontab -l` → `# >>> KORA <id>` … `# <<< KORA <id>` |
| Windows | Task Scheduler | task `Kora\<id>` (schtasks) |

Mỗi lần chạy gọi `orchestrator.py --run <id>` — script Python thuần (KHÔNG cần app Claude).

## orchestrator.py — chu trình 1 lượt
SCAN nguồn (lỗi thì **skip + ghi log**) → reindex → **POST lên Confluence chung** → đánh dấu
độ mới → sinh report → gửi mail (chỉ **HOST**) → **có lỗi thì tạo TICKET SỰ CỐ + email** danh
sách nhận. Không fail im; exit 0/2/1 = ok/partial/failed. Ghi `reports/scheduler-logs/last-run-<id>.json`.

## schedule.py — đăng ký / liệt kê / sửa / gỡ
```
python3 tools/kora-scheduler/schedule.py register --id daily --cron "0 8 * * 1-5" \
      --scan jira:local,confluence:KB --post confluence:KB --email a@x.com,b@y.com
python3 tools/kora-scheduler/schedule.py list
python3 tools/kora-scheduler/schedule.py edit   --id daily --scan jira:local   # scan/post/email đọc lúc chạy → không cài lại OS
python3 tools/kora-scheduler/schedule.py remove --id daily
```
Hoặc dùng wrapper `scripts/schedule.command` (macOS/Linux) / `scripts/schedule.bat` (Windows).
Registry: `tools/kora-scheduler/schedules.json` (gitignore, máy-cục-bộ). Token `scan/post` = `type:name`:
`jira:<env>`, `confluence:<space>`, `github:<owner/repo>` (scan = KÉO KB host về local), `sharepoint:<site>`.
`--sync-targets confluence,github,sharepoint`. Lệnh sinh artifact OS đúng theo `--os auto|macos|linux|windows`.

> ⚠️ Tạo lịch = đăng ký tiến trình nền chạy đúng giờ → **luôn confirm trước** (Approval Gate).
> Cron không có PATH → orchestrator dùng python tuyệt đối + neo path theo vị trí script.
> Nguồn chỉ kết nối qua MCP **không** quét được trong cron (không có connector nền) → dùng API/token.
