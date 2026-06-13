# Workflow 08 — Lịch tự động đồng bộ Jira (scheduled sync)

> Trigger: "đặt lịch quét jira", "tự động đồng bộ jira", "lên lịch sync" (confirm ý định trước).
> Cũng được hỏi ở Bước 4 của setup khi user bật quét Jira.

## Điều kiện

- Đã cấu hình `.env.local` (token + URL) và quét full ít nhất 1 lần (có mốc
  `_system/last-import.txt`).
- **Quan trọng — chỗ chạy:** scheduled task chạy trong môi trường của Claude.
  - Jira **Cloud/Atlassian hoặc public** (sandbox ra được) → chạy `--since` tự động hoàn toàn.
  - Jira **nội bộ/VPN** (sandbox không ra được) → lịch chỉ có thể **nhắc user** chạy file
    `quet-jira.command`/`.bat`, KHÔNG tự quét được. Nói rõ điều này cho user trước khi đặt lịch.

## Bước 1 — Hỏi tần suất

> "Bạn muốn tự động lấy issue mới/cập nhật từ Jira bao lâu một lần?"
> - [A] Mỗi sáng (vd 8:00) — khuyến nghị
> - [B] Mỗi giờ làm việc
> - [C] Hằng tuần (thứ Hai)
> - [D] Tần suất khác — user tự nêu

## Bước 2 — Tạo scheduled task

Gọi `mcp__scheduled-tasks__create_scheduled_task` với:
- `cronExpression` theo lựa chọn (vd "0 8 * * *" cho mỗi sáng 8h).
- `prompt`: nội dung để phiên tự động chạy, đại ý:

  > "Chạy đồng bộ Jira tăng dần cho project này: vào `tools/jira-to-obsidian`,
  > chạy `python3 import_jira.py --since`. Đọc kết quả, nếu có issue mới/cập nhật thì
  > tóm tắt ngắn gọn (bao nhiêu issue, thuộc project/epic nào) và báo cho tôi.
  > KHÔNG ghi vào KB chính — chỉ cập nhật vault raw + relation graph. Có gì đáng chú ý
  > (vd story mới chưa có AC) thì nêu để tôi xử lý sau."

- Ghi `jira.scheduled_sync` (tần suất + task id) vào `factory-config.yaml`.

## Bước 3 — Xác nhận

Báo user: lịch đã đặt, chạy lúc nào, đồng bộ kiểu gì, đổi/huỷ bằng cách nào
("đổi lịch sync" / "huỷ lịch sync" → dùng update/list scheduled task).
