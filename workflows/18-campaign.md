# Workflow 18 — Campaign tự động (n8n-lite)

> Tương đương skill `/claude-knowledge-campaign`. Động cơ: `tools/kora-campaign/campaign.py`.
> Chuỗi bước TUYẾN TÍNH (không nhánh). Tool path: `T=tools; [ -e "$T/kora-campaign/campaign.py" ] || T="$HOME/.claude/kora-framework/tools"`.

## Khái niệm
- Campaign = `{id, name, schedule (cron|date), enabled, steps[]}` trong `tools/kora-campaign/campaigns.json` (gitignore, DATA).
- Bước HEADLESS: `scan · reindex · report · mail · post · sync` (shell tool Kora). Bước MODEL: `analyze · canva` (interactive).
- Outward (`mail/post/sync`) qua cổng `KORA_OPS_PW`. Lỗi 1 bước → DỪNG chuỗi.

## Lệnh
- `campaign.py list` — liệt kê.
- `campaign.py create --file <spec.json>` — tạo/thay (replace theo id).
- `campaign.py run <id> [--dry-run]` — chạy tuần tự (dry-run xem chuỗi lệnh, không thực thi).
- `campaign.py delete --id <id>` — xoá. Bật/Tắt = sửa `enabled` trong registry.

## Tạo (hỏi từng bước → CHỐT)
1. Tên + id (AskUserQuestion).
2. Chọn các bước + tham số (xem skill: scan/analyze/report/canva/mail/post/sync).
3. Dựng spec JSON → **trình → ✋ CHỐT** → `create --file`.
4. **Hỏi lịch**: đặt lịch nền (OS) qua `tools/kora-scheduler/schedule.py` gọi `campaign.py run <id>` đúng giờ, HOẶC chạy tay.
5. Đề nghị `run <id> --dry-run` trước khi chạy thật.

## Chạy interactive
Gặp `analyze`/`canva` → Claude làm tại chỗ (phân tích AI / gọi `/claude-knowledge-canva`, hỏi-rõ→chốt); bước headless gọi tool.

> ⚠️ Lịch nền (cron/launchd) chỉ chạy bước HEADLESS — bước cần MODEL bỏ qua. Sandbox Cowork chặn API/SMTP → lịch chạy ở MÁY (OS).
