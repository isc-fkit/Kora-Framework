# System Lessons — Bài học tầng QUY TRÌNH (workflow & rule)

> Ghi mỗi khi một WORKFLOW/RULE lộ lỗi, mâu thuẫn, hoặc bị cải tiến lớn (KHÁC `.kb/lessons.md` là
> bài học tầng TRI THỨC/feature). `workflows/13-evolve-system.md` đọc file này để không lặp lỗi
> quy trình cũ. Format mỗi mục:
>
> ## YYYY-MM-DD — <bối cảnh / workflow>
> - **Sai gì:** ...
> - **Sửa gì:** ...
> - **Rút ra / áp dụng từ nay:** ...

## 2026-06-22 — AskUserQuestion "Invalid tool parameters" do SCHEMA (header >12 ký tự)
- **Sai gì:** `/claude-knowledge-send-mail` bước "Gửi ngay hay đặt lịch?" báo `Invalid tool parameters`. Khác lỗi "Failed"
  (2026-06-14, do input tự do) và khác "could not be parsed as JSON" (sai cú pháp): đây là **vi phạm SCHEMA** —
  thường do `header` >12 ký tự, hoặc option thiếu `description`, hoặc thiếu `multiSelect`. Guidance ghi terse
  "AskUserQuestion [A] / [B]" (28+ chỗ) không nêu ràng buộc → model dễ dựng header dài / thiếu field.
- **Sửa gì:** CLAUDE.md rule #8 thêm **HỢP ĐỒNG SCHEMA** (header ≤12 ký tự · mỗi option có `label`+`description` ·
  `multiSelect` bắt buộc · 2–4 option, >4 phân trang). Ghi shape ngắn ở claude-knowledge-send-mail bước 2b/4. (v2.9.3)
- **Rút ra / áp dụng từ nay:** Mọi thẻ chọn — `header` NGẮN ≤12 ("Gửi/Lịch", "Phạm vi", "Kênh gửi"), KHÔNG nhồi
  cả câu vào header; mỗi option luôn kèm `description`; luôn set `multiSelect`. >4 lựa chọn → phân trang, không nhồi.

## 2026-06-14 — AskUserQuestion cho input tự do → "Failed"
- **Sai gì:** Setup hỏi tên project bằng AskUserQuestion (vốn cần options cố định) → hiển thị "Failed".
- **Sửa gì:** Nguyên tắc 8 cấm AskUserQuestion cho input tự do + xử lý case "lai"; workflow 00 Bước 2
  hỏi tên bằng câu thường.
- **Rút ra:** Input TỰ DO (tên/URL/đường dẫn/mã/cron) luôn hỏi câu thường; AskUserQuestion chỉ để
  chọn nhánh hữu hạn. Lựa chọn dẫn tới nhập tự do → hỏi giá trị ở lượt kế bằng câu thường.

## 2026-06-14 — ĐÍNH CHÍNH: AskUserQuestion CÓ nhận free text qua ô "Other"
- **Sai gì:** Kết luận bài học trên ("luôn hỏi câu thường cho input tự do") là **over-correction**.
  User phản hồi: bắt gõ vào chat trải nghiệm kém — muốn hiện THẺ có gợi ý + ô trống để nhập.
- **Sửa gì:** Nguyên tắc 8 viết lại — **input tự do KHÔNG nhạy cảm vẫn dùng AskUserQuestion: đưa
  gợi ý làm option + ô "Other" để user tự gõ**. "Failed" trước kia là do thiếu option cố định,
  không phải bản chất. Workflow 00 Bước 2/3 đổi sang card-gợi-ý-+-Other (fallback câu thường nếu lỗi).
- **Rút ra:** AskUserQuestion = option cố định + ô "Other" (free text). Dùng cho cả nhập liệu
  không nhạy cảm. **NGOẠI LỆ tuyệt đối:** token/secret KHÔNG đưa vào card (nhập qua `.env.local`).

## 2026-06-14 — "quét jira" thiếu chọn nguồn/domain
- **Sai gì:** Workflow 01 khóa cứng `.env.local`, không lộ cơ chế đa nguồn (đã có trong code) ra lúc quét.
- **Sửa gì:** Thêm Bước 0 chọn nguồn/domain (Server nội bộ / Cloud Atlassian) + `JIRA_ENV_FILE`.
- **Rút ra:** Năng lực đã có trong code PHẢI được surface ở bước người dùng thấy, đừng chôn trong config.

## 2026-06-14 — Setup: sub-step "thêm/bớt rule" mở bằng free-text thay vì thẻ chọn
- **Sai gì:** Sau khi chọn domain, bước hỏi "thêm/bớt rule?" được để là nhập tự do (câu thường) →
  user phải gõ tay thay vì bấm chọn. User phản hồi 2 lần rằng "mọi sub-step setup đều phải hiện thẻ".
  Bản v1.0.3 mới chỉ ép "mỗi bước dừng hỏi" nhưng chưa đổi các sub-step free-text thành thẻ.
- **Sửa gì:** Đổi "thêm/bớt rule" và "đặt lịch sync" thành AskUserQuestion (Có/Không) trước; chỉ rơi
  xuống câu thường SAU khi user chọn nhánh cần nhập. Thêm rule 🔑 vào workflow 00 + CLAUDE.md §1.8.
- **Rút ra:** MỞ ĐẦU mọi quyết định (kể cả câu dẫn tới nhập tự do) bằng AskUserQuestion tối thiểu
  Có/Không — TUYỆT ĐỐI không mở một bước bằng câu hỏi free-text trống. Free-text chỉ ở lượt kế sau khi chọn nhánh.
