# Workflow 20 — Chiến lược GEO (Generative Engine Optimization)

> Phân tích nội dung marketing/SEO → **việc cần làm để TĂNG GEO** (được ChatGPT·Perplexity·Google AI
> Overviews·Gemini·Claude·Copilot trích dẫn) → **bức tranh + roadmap 1 năm / 5 năm** → (tùy chọn) **lên
> chiến dịch tự động** theo roadmap. Tiêu chí GEO: `tools/geo-strategy/README.md` (8 chiều, có trích nguồn).

Resolve path tool (bản cài ở CORE): `T=tools; [ -e "$T/geo-strategy/geo_strategy.py" ] || T="$HOME/.claude/kora-framework/tools"`.

## Bước 0 — Confirm + CỔNG MẬT KHẨU vận hành
- Guard gói USER (file `.claude-knowledge-user`) → máy NGƯỜI DÙNG không chạy phân tích/gửi; báo nhẹ rồi DỪNG.
- 🔒 **Cổng `KORA_OPS_PW`** (kéo nội dung live từ SharePoint + có thể tạo campaign outward):
  `python3 "$T/archive-gate/verify_ops_password.py"` — exit ≠ 0 → **DỪNG**.

## Bước 1 — Chọn NGUỒN nội dung (BẮT BUỘC HỎI, KHÔNG tự quét)
**AskUserQuestion** (header "Nguồn ND"): **[SharePoint] · [Local folder] · [Đã có trong vault]**.
- **[SharePoint] — BẮT BUỘC HỎI 2 BƯỚC (như WF14), TUYỆT ĐỐI không tự lấy "file mới nhất":**
  **① HỎI FOLDER** `sharepoint_folder_search` → AskUserQuestion liệt kê → user chọn **(các) FOLDER** (ô "Other" = keyword → `sharepoint_search query=`); **② HỎI FILE** `sharepoint_search folderName=<folder>` → chọn (các) file → `read_resource` đọc text. >4 → phân trang.
- **[Local folder]** → AskUserQuestion hỏi đường dẫn (ô "Other"); đọc các file nội dung (md/html/docx/txt/csv).
- **[Đã có trong vault]** → dùng note `source: content` đã import.

## Bước 2 — Import nội dung vào vault (`source: content`)
Mỗi nội dung → 1 note `type: content`, `source: content`, `source_id: content__<batch>` (tiêu đề · url nếu có · body trích xuất).
Dùng `import_files`/workflow 02 cho file, hoặc ghi thẳng note. Reindex `build_index.py --root .` sau import.

## Bước 3 — 🤖 SPAWN Agent GEO Analyst (BẮT BUỘC, fallback: không có Agent tool → Claude tự chấm)
`Agent(subagent — chuyên gia GEO/AI-SEO)`, prompt:
> *"Đóng vai **chuyên gia Generative Engine Optimization (GEO)**. Đọc TỪNG nội dung đã chọn (note `source: content`
> hoặc file). Với MỖI nội dung, CHẤM 0–100 cho **8 chiều** (theo `tools/geo-strategy/README.md`) — chỉ chấm theo
> những gì THỰC SỰ có trong nội dung, KHÔNG bịa:
> 1. **extractability** — quick-answer 40–80 từ đầu trang? câu định-nghĩa-dẫn? TL;DR/bullet/bảng? FAQ/Q&A?
> 2. **statistics** — có thống kê gốc / dữ liệu first-party?
> 3. **citations** — 3–5 trích dẫn nguồn uy tín + quotation?
> 4. **authority** — author bio/E-E-A-T? liên kết thực thể (Wikipedia/Wikidata)? outbound uy tín?
> 5. **schema** — JSON-LD (Article/FAQPage/ItemList/Organization)?
> 6. **offsite** — dấu hiệu hiện diện Reddit/LinkedIn/Wikipedia/YouTube/Quora?
> 7. **technical** — HTTPS? tốc độ? llms.txt? robots cho GPTBot/PerplexityBot/ClaudeBot/Google-Extended?
> 8. **freshness** — cập nhật gần đây? version history?
> Mỗi nội dung liệt kê **gaps** (3–6 thiếu sót lớn nhất). Ghi ra `reports/_geo-rows.json` ĐÚNG schema:
> `{"brand":"<thương hiệu>","period":"<vd 2026-Q2>","competitors":["..."],"overall_notes":"...",
>   "pieces":[{"id":"<url|title>","title":"...","url":"...","scores":{"extractability":N,...8 chiều...},"gaps":["..."]}]}`.
> KHÔNG render HTML — chỉ ghi JSON. Thiếu dữ liệu chiều nào → chấm thấp + ghi vào gaps."*

## Bước 4 — Sinh scorecard + action-list + roadmap
`python3 "$T/geo-strategy/geo_strategy.py" --rows reports/_geo-rows.json --brand "<thương hiệu>" --period "<kỳ>"`
→ ra `reports/geo-strategy-latest.html` (dashboard: điểm GEO tổng · 8 chiều · **việc cần làm ưu tiên** · roadmap
1 năm/5 năm · nội dung yếu nhất · metrics) + `geo-strategy-latest.json` + `_subject-latest.txt` (tiêu đề mail động).
- **Hiển thị inline Cowork** qua `show_widget` (đọc HTML) + báo: điểm tổng, 3 chiều yếu nhất, top việc quick-win.
- Mọi con số/đề xuất bám `_geo-rows.json` — KHÔNG bịa.

## Bước 5 — Bước kế (AskUserQuestion, kèm khuyến nghị)
- **[Lên chiến dịch theo roadmap]** → workflow 18 / `claude-knowledge-campaign`: map mỗi giai đoạn roadmap (Q1→Q4 hoặc năm)
  thành chuỗi **đo GEO định kỳ → Agent GEO phân tích → report tiến triển → mail/post** + đặt lịch (xem WF20 §Campaign).
- **[Gửi mail báo cáo GEO]** → `send_report.py --html-file reports/geo-strategy-latest.html --attach …` (tiêu đề tự đọc `_subject-latest.txt`; qua cổng).
- **[Xuất tài liệu]** → workflow 06 (docx/pdf cho lãnh đạo). · **[Quét thêm nội dung]** · **[Dừng]**.

## §Campaign — sinh chiến dịch từ roadmap (Pha 3)
Mỗi giai đoạn roadmap = 1 campaign step-set chạy theo lịch (đo GEO → phân tích → report → mail/post). Tạo qua
`tools/kora-campaign/campaign.py` (create/list/run/dry-run) + `schedule.py` đặt lịch. Bước outward (mail/post) gated
`KORA_OPS_PW`; bước model (Agent GEO) chạy interactive. ✋ Chốt trước khi tạo/đặt lịch.

## Guardrails
- KHÔNG in token; phân tích read-only (chấm điểm) — chỉ GHI khi user chốt (import note · tạo campaign · gửi mail).
- BẮT BUỘC hỏi nguồn + (SharePoint) hỏi folder trước khi quét. Thiếu `_geo-rows.json` → geo_strategy.py DỪNG (báo cần Agent sinh trước).
- Đầu ra CHUẨN: tiêu chí 8 chiều cố định (README.md) → so sánh được giữa các kỳ.
