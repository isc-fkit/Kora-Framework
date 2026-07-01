---
description: Phân tích GEO (Generative Engine Optimization) — đưa ra VIỆC CẦN LÀM để nội dung/thương hiệu được AI (ChatGPT·Perplexity·Google AI Overviews·Gemini·Claude·Copilot) trích dẫn, dựng ROADMAP 1 năm/5 năm từ nội dung SharePoint, rồi (tùy chọn) lên CHIẾN DỊCH tự động theo roadmap. Quét nội dung marketing/SEO → chấm 8 chiều GEO → scorecard + action-list ưu tiên + roadmap. Password-gated (operations password). Triggers (vi): «phân tích GEO», «tăng GEO», «tối ưu AI search», «generative engine optimization», «chiến lược nội dung AI», «roadmap GEO», «được AI trích dẫn» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-geo-strategy` — phân tích **GEO (Generative Engine Optimization)** rồi dựng roadmap & (tùy chọn) chiến dịch. Thực hiện theo `workflows/20-geo-strategy.md`.

> 🛑 **GIAO THỨC — KHÔNG NHẢY BƯỚC.** Thứ tự HỢP LỆ: **(1)** cổng mật khẩu `verify_ops_password.py`; **(2)**
> **AskUserQuestion chọn NGUỒN nội dung** ([SharePoint]·[Local folder]·[Đã có trong vault]); **(3)** nếu = **SharePoint**
> → **BẮT BUỘC hỏi FOLDER** (`sharepoint_folder_search`) **rồi hỏi FILE** trước khi đọc — CẤM tự lấy "file mới nhất".
> **🛑 SAU mỗi câu → DỪNG, CHỜ user.** ⛔ KHÔNG gọi tool quét/đọc nào trước khi user trả lời câu chọn nguồn.

Resolve path tool: `T=tools; [ -e "$T/geo-strategy/geo_strategy.py" ] || T="$HOME/.claude/kora-framework/tools"`.

1. 🔒 **Cổng `KORA_OPS_PW`** TRƯỚC (kéo nội dung live + có thể tạo campaign): `python3 "$T/archive-gate/verify_ops_password.py"` — exit ≠ 0 → DỪNG.
2. **Chọn nguồn** (AskUserQuestion) → SharePoint thì **hỏi FOLDER → hỏi FILE** (`sharepoint_folder_search` → `sharepoint_search folderName=<f>` → `read_resource`); Local thì hỏi đường dẫn; hoặc dùng note `source: content` sẵn có. Import → vault (`type: content`, `source_id: content__<batch>`) → reindex.
3. **🤖 BẮT BUỘC SPAWN Agent GEO Analyst** (Agent tool, **model `opus`** — chấm 8 chiều cần suy luận sâu; môi trường không hỗ trợ tham số `model` → kế thừa model phiên, KHÔNG fail): đọc TỪNG nội dung → chấm **8 chiều 0–100** (extractability·statistics·citations·authority·schema·offsite·technical·freshness — rubric ở `tools/geo-strategy/README.md`) + liệt kê **gaps** → ghi `reports/_geo-rows.json` đúng schema (`{brand,period,competitors,overall_notes,pieces:[{id,title,url,scores{8 chiều},gaps[]}]}`). KHÔNG render HTML, chỉ JSON. *(Không có Agent tool → Claude tự chấm theo rubric.)*
4. **Sinh strategy:** `python3 "$T/geo-strategy/geo_strategy.py" --rows reports/_geo-rows.json --brand "<thương hiệu>" --period "<kỳ>"` → `reports/geo-strategy-latest.html` (điểm GEO tổng · 8 chiều · **VIỆC CẦN LÀM ưu tiên** effort×impact · **roadmap 1 năm/5 năm** · nội dung yếu nhất · metrics) + `_subject-latest.txt`. **Hiển thị inline** qua `show_widget`; báo điểm tổng + 3 chiều yếu nhất + top quick-win.
5. **Bước kế (AskUserQuestion):** **[Lên chiến dịch theo roadmap]** (`claude-knowledge-campaign` — map giai đoạn roadmap → chuỗi đo GEO→phân tích→report→mail/post + đặt lịch, gated `KORA_OPS_PW`) · **[Gửi mail báo cáo GEO]** (`send_report.py --html-file reports/geo-strategy-latest.html`, tiêu đề tự đọc `_subject-latest.txt`) · **[Xuất tài liệu docx/pdf]** · **[Quét thêm nội dung]** · **[Dừng]**.

**Guardrails:** không in token; chấm điểm là read-only, chỉ GHI khi user chốt; tiêu chí 8 chiều cố định để so sánh giữa các kỳ; bám `_geo-rows.json`, KHÔNG bịa số.
