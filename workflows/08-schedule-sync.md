# Workflow 08 — Lịch tự động đồng bộ Jira (scheduled sync)

> Trigger: "đặt lịch quét jira", "tự động đồng bộ jira", "lên lịch sync" (confirm ý định trước).
> Cũng được hỏi ở Bước 4 của setup khi user bật quét Jira.

## Điều kiện

- Đã cấu hình `.env.local` (token + URL) và quét đầy đủ ít nhất 1 lần (có mốc
  `_system/last-import-<host>.txt`).

## ⏰ Cách lịch chạy — NÓI RÕ cho user trước khi đặt

- **Chạy tại máy bạn khi app Claude đang mở** — KHÔNG phải cron đám mây chạy 24/7.
- **Đặt 9h mà 9h máy tắt / app đóng?** → task **chạy bù NGAY lần mở app kế tiếp** (vd 10h);
  không sót gì vì `--since` lấy mọi issue cập nhật **kể từ lần đồng bộ trước**.
- **Chỉ lấy MỚI:** mỗi lần chạy `import_jira.py --since` chỉ kéo issue tạo/sửa từ mốc lần
  trước rồi merge vào vault — không quét lại từ đầu.
- Cron tính theo **giờ địa phương** của máy.
- Mạng: chạy ở máy user nên dùng mạng/VPN của user → tới được cả Jira nội bộ
  (`company.vn`) lẫn Cloud. (Nếu môi trường chạy không ra được host nội bộ → lịch
  chuyển sang **nhắc user** chạy lệnh Terminal `python3 "<TOOL_DIR>/import_jira.py" --since`.)

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

### Đa nguồn Jira (vd vừa `company.vn` vừa `myteam.atlassian.net`)

Mỗi nguồn = một file cấu hình riêng + một scheduled task riêng:
- Tạo `.env.<tên-nguồn>` (vd `.env.company`, `.env.cloud`) trong `tools/jira-to-obsidian/`,
  mỗi file là một bản `.env.local` trỏ đúng Jira đó.
- Lệnh trong prompt của từng task: `JIRA_ENV_FILE=.env.<tên-nguồn> python3 import_jira.py --since`.
- Mốc `--since` tách riêng theo host (`last-import-<host>.txt`) → 2 nguồn KHÔNG đè nhau;
  notes mỗi project ở thư mục riêng; quét full giờ cũng **merge** an toàn, không xoá nguồn kia.
- ⚠️ **Tránh 2 Jira trùng MÃ project** (vd cả hai đều có `PROJ`): node graph định danh theo mã
  issue → trùng mã sẽ đè nhau. Đặt `PROJECT_KEYS` không giao nhau giữa các nguồn.

## Xử lý lỗi khi chạy nền

- Phiên scheduled gặp lỗi (401 token hết hạn / mất mạng / Jira nội bộ không tới) → **báo cho
  user** (giữ `notifyOnCompletion`), KHÔNG im lặng. Mốc `last-import` chỉ cập nhật khi quét
  THÀNH CÔNG (script không lưu mốc nếu `die()`), nên lần sau tự quét lại từ mốc cũ — không sót.

## Bước 3 — Xác nhận

Báo user: lịch đã đặt, chạy lúc nào, đồng bộ kiểu gì, đổi/huỷ bằng cách nào
("đổi lịch sync" / "huỷ lịch sync" → dùng update/list scheduled task).
