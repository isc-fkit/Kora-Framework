# excel-to-obsidian — Nạp Excel / Google Sheet vào báo cáo (gộp chung với Jira)

Biến mỗi DÒNG của 1 bảng task/tiến độ thành note trong vault **cùng định dạng `import_jira.py`** → báo cáo
(`build_report.py`) **gộp chung** task Excel với task Jira (cùng biểu đồ status / assignee / độ phức tạp / giờ-công,
vai trò PM/QC vẫn áp). **Chỉ thư viện chuẩn Python 3** — KHÔNG cần cài gì.

## Dùng
```bash
# 1) File Excel local (.xlsx):
python3 tools/excel-to-obsidian/import_excel.py --file data/ke-hoach.xlsx --sheet "Tasks" --source-id kehoach

# 2) Rows đã chuẩn hoá (CSV header dòng đầu, hoặc JSON list[dict]):
python3 tools/excel-to-obsidian/import_excel.py --from-rows reports/_sheet-q2.csv --source-id q2

# 3) Tải từ URL (.xlsx/.csv) — SharePoint downloadUrl hoặc Google publish-CSV (honor HTTPS_PROXY):
python3 tools/excel-to-obsidian/import_excel.py --from-url "<url>" --source-id sp --map '{...}'
```

## Excel trên SharePoint 365 (qua MCP, chỉ tương tác)
Cần connector **Microsoft 365** đã *connected* trong Claude App. Trong Cowork:
1. `sharepoint_search` `query="<tên file>" fileType="xlsx"` → chọn file → URI `file:///{driveId}/{itemId}`.
2. `read_resource` URI → lấy **`@microsoft.graph.downloadUrl`** (pre-authenticated, ngắn hạn).
3. `import_excel.py --from-url "<downloadUrl>" --sheet <ten> --map <map> --source-id <id>` → tải .xlsx thật + parse ô chuẩn.

*read_resource trả text trích xuất cho .xlsx (không phải ô) → LUÔN ưu tiên `--from-url` với downloadUrl.* Nền/scheduled cần Graph API token riêng (không dùng MCP).

## Google Sheet
Chưa có MCP connector → **Publish to web → CSV** rồi `--from-url "<csv_url>"`; hoặc tải .xlsx → `--file`.

## Tạo file mẫu (~100 dòng)
`python3 tools/excel-to-obsidian/make_sample.py [out.xlsx] [số_dòng]` → file mẫu format Import_Task + sheet Guideline.
Windows: thay `python3` bằng `py`. Sau khi nạp: `python3 tools/kb-indexer/build_index.py --root .` rồi gõ **"báo cáo tiến độ"**.

## Mapping cột (header → field báo cáo)
Tự nhận tên cột phổ biến **Việt/Anh** (Mã/Key, Tên/Title/Summary, Loại/Type, Trạng thái/Status, Người làm/Assignee,
Story Points/Điểm, Độ phức tạp/Complexity, Ước tính/Estimate, Đã log/Spent, Hạn/Due…). Cột KHÁC chuẩn → khai:
```bash
--map '{"Mã CV":"excel_key","Nội dung":"summary","Phụ trách":"assignee","Điểm":"story_points"}'
```
**Field đích hợp lệ:** `excel_key, summary, type, status, status_category, assignee, reporter, project,
story_points, complexity, estimate_hours, spent_hours, remaining_hours, duedate, sprint_name, sprint_state, sprint_end, updated`.
- **Bắt buộc tối thiểu:** `summary` + `status` (thiếu cả 2 → báo lỗi). Không có cột key → tự sinh `<source_id>-<số dòng>`.
- **Giờ** (`estimate_hours/spent_hours/remaining_hours`) → tự ×3600 thành giây. **Ngày** (Due/Updated…) nhận cả
  serial-number của Excel lẫn chuỗi (YYYY-MM-DD, dd/mm/yyyy…) → chuẩn hoá YYYY-MM-DD.
- **status_category** (todo/in_progress/done): nếu không khai cột, tự suy theo từ khoá (Done/Hoàn thành→done; Đang/In Progress→in_progress; Chưa/To Do→todo).

## Cờ
`--file` (.xlsx) · `--sheet` · `--from-rows` (.csv|.json) · `--map` (JSON inline/đường dẫn) · `--project` (mã project
mặc định) · `--source-id` (quyết định thư mục `07_Imported/<id>/` + marker) · `--vault` (mặc định đọc `vault_path` config).

## Idempotent
Mỗi lần nạp **xoá sạch note cũ của nguồn đó** (`07_Imported/<source_id>/`) rồi ghi lại — sheet = trạng thái hiện tại
đầy đủ, không bao giờ nhân đôi. Nguồn khác nhau (`--source-id` khác) không đụng nhau.

## Giới hạn
- Đọc 1 sheet/lần. Ô gộp lấy giá trị ô góc. Công thức → lấy giá trị đã tính (cached value) nếu file có.
- Chỉ TƯƠNG TÁC cho nguồn MCP (Google Sheet/SharePoint): token connector do app Claude giữ → không chạy lịch nền.
  Muốn nền → dùng file local .xlsx.
