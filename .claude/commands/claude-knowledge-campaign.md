---
description: Build & manage an automated CAMPAIGN — a linear chain of steps (scan → analyze → make report/Canva → send mail → post/sync) that runs on a schedule (n8n-lite). Create, list, run (or dry-run), enable/disable, delete. Outward steps (mail/post/sync) are operations-password gated; model steps (AI analysis, Canva) run interactively. Triggers (vi): «tạo campaign», «tự động hoá quy trình a-z», «chuỗi tự động như n8n», «đặt lịch chiến dịch», «pipeline tự động» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-campaign` — dựng/quản lý **campaign tự động** (chuỗi bước TUYẾN TÍNH, hẹn ngày chạy). Tool: `python3 "$T/kora-campaign/campaign.py" …` (`T=tools; [ -e "$T/kora-campaign/campaign.py" ] || T="$HOME/.claude/kora-framework/tools"`).

> 🧩 **Campaign = chuỗi bước, KHÔNG nhánh điều kiện** (n8n-lite). Bước HEADLESS: `scan · reindex · report · mail · post · sync`.
> Bước cần MODEL: `analyze` (AI phân tích) · `canva` (tạo design) → chạy **interactive** (trong phiên này); headless tự BỎ QUA.
> ⛔ Bước OUTWARD (`mail/post/sync`) qua cổng **`KORA_OPS_PW`**. Mọi thao tác GHI/đăng ký lịch → **user CHỐT trước**.

### Bước 1 — Chọn (AskUserQuestion, header "Campaign")
**[Tạo campaign mới] · [Xem & quản lý] · [← Huỷ]**.
- **[Xem & quản lý]** → `campaign.py list` → AskUserQuestion cho từng campaign: **[Chạy thử (dry-run)] · [Chạy ngay] · [Bật/Tắt] · [Xoá]**.
  `run <id> --dry-run` (xem chuỗi lệnh, KHÔNG thực thi) / `run <id>` (thật) / `delete --id <id>`. Bật/Tắt = sửa `enabled` (đọc-sửa registry).
  - ⚠️ **[Chạy ngay] = chạy THẬT (gửi mail / đẩy post/sync ra ngoài) → ✋ XÁC NHẬN trước** (nên đề nghị `--dry-run` trước). [Xoá] cũng xác nhận.

### Bước 2 — Tạo campaign mới (hỏi từng bước → CHỐT → tạo → đặt lịch)
1. **Tên + id** (AskUserQuestion gợi ý + ô "Other").
2. **Chọn các BƯỚC theo thứ tự** (multi-select, rồi xác nhận thứ tự) — mỗi loại hỏi tham số:
   - `scan` → nguồn (`invoice` từ ảnh hoá đơn / `meeting` / `jira` jql / `excel`) + `from_rows`/`jql` + `source_id`.
   - `analyze` → AI phân tích gì (rủi ro chi phí, bất thường…). *(chạy interactive)*
   - `report` → `report_type` (progress/invoice/meeting-roadmap/custom) + `template`/`source_ids`/`scope`.
   - `canva` → sản phẩm/thuyết trình (mô tả). *(chạy interactive — gọi `/claude-knowledge-canva`)*
   - `mail` → `to` + `html_file` (+ `attach`). **(gated)**
   - `post`/`sync` → `target` (confluence/github/sharepoint). **(gated)**
3. **Dựng spec JSON** (`{"campaigns":[{id,name,schedule,enabled,steps:[…]}]}`) → **trình cho user → ✋ CHỐT**.
4. Sau chốt → `campaign.py create --file <spec.json>`.
5. **HỎI LỊCH** (AskUserQuestion): **[Lịch Cowork /schedule — quan sát được (khuyến nghị)] / [Lịch nền OS (launchd/cron)] / [Chạy tay khi cần]**.
   - **[Lịch Cowork /schedule]** → tạo scheduled task qua `/claude-knowledge-schedule` (chạy khi MỞ app, theo dõi/ bật-tắt trong Cowork).
     ƯU TIÊN: chạy được **CẢ bước model** (analyze/canva) vì có Claude trong phiên — phù hợp campaign có OCR/AI/Canva.
   - **[Lịch nền OS]** → `tools/kora-scheduler/schedule.py` (cron/launchd) gọi `campaign.py run <id>` đúng giờ —
     **CHỈ chạy bước HEADLESS** (analyze/canva BỊ BỎ QUA vì không có model). Bước outward cần `KORA_OPS_PW` ở `~/.config/claude-knowledge/ops-pw.env`.
6. **Chạy thử ngay:** đề nghị `campaign.py run <id> --dry-run` để user xem chuỗi trước khi chạy thật.

> Khi chạy INTERACTIVE: gặp bước `analyze`/`canva` → Claude thực hiện tại chỗ (phân tích AI / gọi skill Canva, hỏi-rõ→chốt),
> các bước headless gọi `campaign.py` hoặc tool tương ứng. Lỗi 1 bước → DỪNG chuỗi (tuyến tính), báo rõ bước nào.
