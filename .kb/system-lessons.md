# System Lessons — Bài học tầng QUY TRÌNH (workflow & rule)

> Ghi mỗi khi một WORKFLOW/RULE lộ lỗi, mâu thuẫn, hoặc bị cải tiến lớn (KHÁC `.kb/lessons.md` là
> bài học tầng TRI THỨC/feature). `workflows/13-evolve-system.md` đọc file này để không lặp lỗi
> quy trình cũ. Format mỗi mục:
>
> ## YYYY-MM-DD — <bối cảnh / workflow>
> - **Sai gì:** ...
> - **Sửa gì:** ...
> - **Rút ra / áp dụng từ nay:** ...

## 2026-06-14 — AskUserQuestion cho input tự do → "Failed"
- **Sai gì:** Setup hỏi tên project bằng AskUserQuestion (vốn cần options cố định) → hiển thị "Failed".
- **Sửa gì:** Nguyên tắc 8 cấm AskUserQuestion cho input tự do + xử lý case "lai"; workflow 00 Bước 2
  hỏi tên bằng câu thường.
- **Rút ra:** Input TỰ DO (tên/URL/đường dẫn/mã/cron) luôn hỏi câu thường; AskUserQuestion chỉ để
  chọn nhánh hữu hạn. Lựa chọn dẫn tới nhập tự do → hỏi giá trị ở lượt kế bằng câu thường.

## 2026-06-14 — "quét jira" thiếu chọn nguồn/domain
- **Sai gì:** Workflow 01 khóa cứng `.env.local`, không lộ cơ chế đa nguồn (đã có trong code) ra lúc quét.
- **Sửa gì:** Thêm Bước 0 chọn nguồn/domain (Server nội bộ / Cloud Atlassian) + `JIRA_ENV_FILE`.
- **Rút ra:** Năng lực đã có trong code PHẢI được surface ở bước người dùng thấy, đừng chôn trong config.
