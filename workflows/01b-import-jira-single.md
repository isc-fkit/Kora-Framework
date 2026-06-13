# Workflow 01b — Quét RIÊNG task/epic/story Jira (trigger: "quét task <KEY>")

> Dùng khi user chỉ muốn lấy 1 hoặc vài issue cụ thể (vd vừa có story mới trên Jira)
> thay vì quét lại cả project. Script dùng chung `tools/jira-to-obsidian/import_jira.py`
> với tham số `--keys` hoặc `--jql`.

## Bước 1 — Xác định phạm vi quét

Từ tin nhắn user, rút ra danh sách key (vd `PROJ-102`, `PROJ-102,PROJ-105`).
Nếu user mô tả mơ hồ → hỏi rõ:

> "Bạn muốn quét theo cách nào?"
> - [A] Theo mã issue — liệt kê key, cách nhau dấu phẩy (vd PROJ-102,PROJ-105)
> - [B] Theo điều kiện — vd "tất cả issue trong epic PROJ-101" → Claude dịch thành JQL,
>   đọc lại cho user xác nhận
> - [C] **Lấy cái MỚI từ lần quét trước** (request/issue mới tạo hoặc vừa cập nhật trên
>   Jira/Atlassian) → dùng chế độ incremental: `python3 import_jira.py --since`
>   (tự đọc mốc thời gian lần quét cuối ở `_system/last-import.txt`). Muốn chỉ định mốc:
>   `--since 2026-06-01`. Chỉ quét issue thay đổi → nhanh, merge vào vault, không quét lại toàn bộ.

**Confirm trước khi chạy**: "Tôi sẽ quét N issue: ... — đúng không?"

## Bước 2 — Chọn nguồn + kiểm tra cấu hình

- **Nguồn nào?** Có nhiều file `tools/jira-to-obsidian/.env*` (đa nguồn) → hỏi user quét lẻ
  từ nguồn nào (như `workflows/01-import-jira.md` Bước 0); dùng `JIRA_ENV_FILE=.env.<tên>` cho
  lệnh bên dưới. Chỉ 1 nguồn → dùng `.env.local`.
- `.env.local` (hoặc file nguồn đã chọn) có token chưa? Chưa → chạy Bước 2 của
  `workflows/01-import-jira.md` (tự tạo file, mở cho user điền, hỏi xác nhận) rồi quay lại đây.

## Bước 3 — Chạy quét

> ⚠️ Như workflow 01 Bước 3-4: đọc `factory-config.yaml > jira.run_mode` —
> `sandbox` → Claude tự chạy; `user_terminal` → sinh lệnh theo `jira.user_os`
> (macOS/Linux dùng bash, Windows dùng PowerShell), user chạy xong Claude đọc
> kết quả trong vault. `auto`/chưa biết → thử sandbox trước rồi mới chuyển.

```bash
cd "<đường dẫn tuyệt đối tới tools/jira-to-obsidian>"
# Theo key:
python3 import_jira.py --keys PROJ-102,PROJ-105
# Hoặc theo JQL:
python3 import_jira.py --jql "parent = PROJ-101"
```

Script chỉ tạo/cập nhật note của các issue đó (kèm epic/parent được nhắc đến trong
backlink) và **merge** vào `_system/relation-graph.json` + `source-registry.json`
hiện có — không đụng các note khác.

## Bước 4 — Báo cáo + hỏi bước tiếp

1. Tóm tắt: đã quét những issue nào, trạng thái, thuộc epic nào, note nằm ở đâu.
2. Hỏi user:
   - [A] Phân tích ngay các issue này thành tri thức (BR/AC/feature) → `workflows/03-request.md`
   - [B] Chỉ lưu raw, xử lý sau
3. Merge graph/registry vào `.kb/` (đánh dấu `status: raw`) → chạy
   `python3 tools/kb-indexer/build_index.py --root .` để index phản ánh issue vừa quét
   (auto-phân tích tra được ngay) → ghi changelog.

## Guardrails

Như workflow 01: không in token, issue raw chưa phải tri thức chính thức,
không suy diễn BR khi chưa phân tích + duyệt.
