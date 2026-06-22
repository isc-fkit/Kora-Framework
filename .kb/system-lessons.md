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

### 2026-06-23 — Quét/báo-cáo Jira MCP KHÔNG lưu vault (tham chiếu vòng tròn)
- **Bối cảnh:** user báo "quét jira MCP + cập nhật báo cáo không lưu tri thức".
- **Sai gì:** `kora-scan` Bước 2 ghi "Jira (API/MCP) → WF01", nhưng `WF01` Bước 0 lại ghi "MCP xử lý ở tầng
  trên kora-scan" → **vòng tròn, KHÔNG chỗ nào gọi `import_jira.py --from-mcp`** → Claude fetch MCP rồi chỉ
  ĐỌC inline, không ghi note vào vault. (Code `--from-mcp` vốn đúng — đã smoke-test New Feature→US, Improvement→Task.)
- **Rút ra:** mỗi luồng MCP→vault PHẢI nêu MINH BẠCH bước `import_jira.py --from-mcp <file> --names <names>` +
  reindex NGAY tại skill chạy nó (kora-scan), KHÔNG "đẩy lên tầng trên/xuống tầng dưới" rồi không tầng nào làm.
  "Chỉ coi là đã quét khi đã chạy `--from-mcp`". Kéo MCP phải PHÂN TRANG lấy HẾT (đừng dừng trang đầu).
- **Áp dụng:** kora-scan Bước 2 (block Jira MCP) + WF14 Bước 0.5 + CLAUDE.md trigger quét/báo-cáo.

### 2026-06-23 — Banner daily-report VỠ trong Outlook (ảnh remote bị chặn)
- **Bối cảnh:** email báo cáo (lịch nền) hiện banner vỡ + chỉ còn alt "Cập nhật tiến độ dự án mỗi ngày".
- **Sai gì:** default `banner_url` của build_report là **URL remote** GitHub raw. `send_report` chỉ thay bằng
  `cid:kora-banner` (inline) KHI tìm thấy file banner LOCAL. **Installer (install.command/bat) KHÔNG copy `assets/`
  vào CORE** → bản cài không có file → giữ URL remote → **Outlook chặn ảnh remote → vỡ**. (Gmail web thì vẫn hiện.)
- **Rút ra:** asset nào email cần nhúng inline (CID) PHẢI được installer/update SHIP vào CORE; tool tìm asset phải
  có path CORE chuẩn `~/.claude/kora-framework/assets` (không chỉ dựa cwd / HERE.parents). Remote URL chỉ là last-resort.
- **Áp dụng:** install.command + install.bat thêm `assets` vào danh sách copy; send_report.py thêm candidate CORE.

### 2026-06-23 — Banner CID không hiện trong Outlook khi email CÓ đính kèm
- **Bối cảnh:** banner nhúng CID hiện tốt khi gửi mail KHÔNG đính kèm, nhưng VỠ ("Download pictures") khi
  email có file đính kèm (báo cáo daily kèm dashboard HTML).
- **Sai gì:** `EmailMessage` + `set_content` + `add_alternative(html)` + `get_payload()[-1].add_related(img)` tạo
  `multipart/related` BỊ CHÔN dưới `alternative`, rồi `add_attachment` bọc thêm `mixed` →
  `mixed > alternative > related`. Outlook FPT/Exchange KHÔNG traverse related chôn sâu → coi cid là ảnh NGOÀI.
- **Rút ra:** email có inline-CID + đính kèm phải dựng `multipart/related` NGAY DƯỚI `multipart/mixed` (sibling của
  đính kèm): `mixed[ related[ alternative[text,html], image(cid) ], đính-kèm ]`. `add_related` của EmailMessage
  KHÔNG bọc được `alternative` (raise "Cannot convert alternative to related") → phải dựng MIME thủ công
  (MIMEMultipart/MIMEImage/MIMEBase). Đã xác minh end-to-end trên Outlook (v3 có đính kèm → banner hiện ngay).
- **Áp dụng:** tools/report-mailer/send_report.py (dựng body related-trên-cùng). + banner asset nén 120KB→57KB.
