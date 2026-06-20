# Workflow 02 — Nạp tri thức từ file (PDF / DOCX / ẢNH / MD / zip Obsidian)

> Trigger: user gửi file (PDF, DOCX, **ảnh PNG/JPG**, .md, zip Obsidian) hoặc nhắn "nạp tài liệu"
> (confirm ý định trước). Mỗi file đi qua: raw → normalized → classified → pending-approval →
> (approve) → KB chính.

## Bước 1 — Tiếp nhận

| Loại file | Hành động |
|---|---|
| PDF | Copy vào `inbox/raw/pdf/`, trích text (skill pdf); PDF scan/ảnh → OCR. **Trích ảnh sơ đồ (CÁCH CỤ THỂ):** PyMuPDF `fitz` — `page.get_images()` lấy ảnh nhúng; trang không có ảnh-object thì `page.get_pixmap()` (hoặc `pdftoppm`) render cả trang ra PNG → lưu `inbox/raw/pdf/<batch>-img/` |
| DOCX | Copy vào `inbox/raw/docx/`, trích text (skill docx) + **trích ảnh sơ đồ (CÁCH CỤ THỂ):** .docx là file zip → `unzip -o file.docx 'word/media/*'` lấy mọi ảnh nhúng → lưu `inbox/raw/docx/<batch>-img/` |
| MD / TXT | Copy vào `inbox/raw/text/` |
| **Ảnh rời (PNG / JPG / JPEG / WEBP)** | Copy vào `inbox/raw/img/`, Claude **đọc ảnh bằng Read (nhìn trực tiếp = vision)** → mô tả thành text có cấu trúc (tái dùng cách Bước 2.5) → đưa vào `raw_content`. Ảnh sơ đồ/flow → trích flow/BR/AC; ảnh chụp màn hình UI → `design_note`; ảnh mờ/không đọc được → `[CẦN XÁC NHẬN: ảnh <tên> chưa đọc được]`, KHÔNG bịa |
| ZIP (folder Obsidian) | Giải nén vào `inbox/raw/obsidian/<tên-zip>/`, giữ nguyên backlink |

Đặt batch id: `import-YYYYMMDD-HHMM-<nguồn>`.

## Bước 2 — Normalize

Mỗi tài liệu → 1 file JSON trong `inbox/normalized/` theo schema:

```json
{
  "source_id": "SRC-FILE-<batch>-<n>",
  "source_type": "pdf|docx|md|obsidian_note",
  "title": "...",
  "raw_content": "...",
  "origin_file": "inbox/raw/pdf/abc.pdf",
  "imported_at": "ISO_DATETIME"
}
```

Không thay đổi nghĩa, không suy diễn.

## Bước 2.5 — Hiểu SƠ ĐỒ / ẢNH bằng vision

Áp dụng cho **cả ảnh nhúng** (trong PDF/DOCX) **lẫn ảnh RỜI** user gửi thẳng (PNG/JPG…).
Tài liệu kỹ thuật hay có sequence diagram / flowchart là **ẢNH** — bước trích text bỏ qua,
nên phải đọc riêng. **Nếu Bước 1 không ra ảnh nào** (file không có ảnh nhúng) → render từng
trang PDF ra PNG (`pdftoppm`/`fitz`) rồi đọc trang có sơ đồ; DOCX không có `word/media` → coi
như không có sơ đồ ảnh (không bịa). Với mỗi ảnh sơ đồ đã trích:

1. Claude **mở ảnh bằng Read (nhìn trực tiếp)** — đây là cách "hiểu" được sơ đồ ảnh.
2. Mô tả lại thành text có cấu trúc: các actor/thành phần, thứ tự bước (1→n), thông điệp
   giữa các bên, nhánh điều kiện (alt/else), vòng lặp (loop), điều kiện bắt đầu/kết thúc.
3. Ghi mô tả vào `raw_content` của tài liệu (kèm `[sơ đồ: <tên ảnh>]` để trace), **giữ link
   ảnh gốc**. Sơ đồ dạng code (Mermaid/PlantUML/ASCII) → đọc thẳng text, không cần vision.
4. Ảnh mờ/không đọc được → đánh dấu `[CẦN XÁC NHẬN: sơ đồ <tên> chưa đọc được]`, KHÔNG bịa.

> Nhờ bước này, luồng nghiệp vụ trong sơ đồ trở thành tri thức (flow/BR/AC), không mất chỉ vì là ảnh.

## Bước 3 — Phân loại (Auto Classifier)

> 📐 **Đọc `config/domain-rules.md` TRƯỚC khi phân loại** (như mọi phiên phân tích — CLAUDE.md §0.1/§2):
> phân loại + nhận diện thuật ngữ/rule thận trọng theo domain hiện hành (vd Healthcare: tách "hiển thị
> thông tin" vs "tư vấn y tế"). Nếu vai trò/domain CHƯA chốt trong phiên → áp cổng vai trò/domain/template
> (`workflows/03-request.md` Bước 0) 1 lần rồi nhớ cho cả phiên.

Phân mỗi tài liệu/đoạn thành: project, epic, user_story, requirement,
business_rule_candidate, acceptance_criteria_candidate, design_note, api_spec,
test_case, bug_report, decision_candidate, domain_knowledge, unknown.

Luật: "As a user..." → user_story; Given/When/Then → AC candidate; điều kiện bắt buộc
hệ thống → BR candidate; mô tả màn hình/UI → design_note; không chắc → unknown
(không bao giờ vào KB chính). Kết quả ghi `inbox/classified/<batch>.md`.

## Bước 4 — Trích xuất tri thức + đối chiếu KB hiện có

1. Trích: feature candidate, requirement, BR, AC, user flow, màn hình, API, data field,
   permission, error/empty state, dependency, risk, open question.
2. Đối chiếu `.kb/index.json` + `relation-graph.json`:
   trùng lặp? mâu thuẫn với rule cũ? bổ sung cho feature nào đã có?
3. Tạo báo cáo `inbox/pending-approval/<batch>-report.md` gồm 5 nhóm:
   **Mới / Trùng / Mâu thuẫn / Thiếu thông tin / Đề xuất cập nhật**.

## Bước 5 — ✋ Approval Gate (tóm tắt cho user xác nhận TRƯỚC khi nạp)

Với MỖI file/tài liệu, trình bày bằng tiếng Việt tự nhiên (không dán JSON):
- **Phân loại**: tài liệu này là gì (đặc tả tính năng / business rule / domain / design...).
- **Tóm tắt nội dung**: 3-5 ý chính rút ra được.
- **Tri thức sẽ nạp**: feature/BR/AC nào sẽ tạo hoặc cập nhật, vào file KB nào.
- **Liên quan & cảnh báo**: trùng/mâu thuẫn với tri thức hiện có (nếu có).

Rồi hỏi:

- [A] Duyệt tất cả  [B] Duyệt mục chọn  [C] Từ chối  [D] Cần sửa / bổ sung thông tin

KHÔNG ghi bất cứ gì vào `docs/` hay vault khi user chưa chọn [A]/[B].

## Bước 6 — Ghi KB (chỉ sau approve)

> 📋 **ÁP TEMPLATE + ĐẦU RA CHUẨN (giống workflow 03):** mọi artifact ghi ra theo **ĐỊNH DẠNG CHUẨN TỰ
> ĐỘNG** của `templates/prompts/ba-prompt-library.md` (US-[ID] As a/I want/So that · AC Given-When-Then đủ
> happy+edge+negative · BR-[ID] · validation · FR/NFR · test TC-[ID]) và **cấu trúc template** trong
> `templates/` (feature `F-xxx/source/` theo `templates/feature-readme-template.md` + `*-template.md`; doc
> BRD/PRD theo `templates/docs/` khi xuất). Vai trò đã chốt (Bước 3) lọc tập artifact. Thiếu thông tin →
> `[CẦN XÁC NHẬN]`, KHÔNG bịa để "đủ format". Đây là cùng chuẩn đầu ra với workflow 03 (mục "ĐẦU RA CHUẨN TỰ ĐỘNG").

1. Ghi vào `docs/` đúng vị trí (feature → `docs/03-features/F-xxx/source/`,
   domain → `docs/01-domain/`, thuật ngữ → `docs/08-glossary/`...).
2. Tạo/cập nhật notes trong Obsidian vault + backlink.
3. Chạy `python3 tools/kb-indexer/build_index.py --root .` (Windows: `py`) (tự dựng lại `index.json` +
   `relation-graph.json` + `health-report.md` khớp `docs/` vừa ghi) → cập nhật
   `source-registry.json`, `changelog.md`. Nếu trong phiên có tài liệu bị từ chối/sửa
   lớn → ghi `.kb/lessons.md` (§0.3).
4. Chuyển batch sang `inbox/approved/` (hoặc `rejected/`).

## Bước 7 — Đề xuất bước kế (§0.4)

Hỏi **AskUserQuestion** (đừng chỉ dừng): `[A] Phân tích sâu tính năng vừa nạp ·
[B] Nạp thêm tài liệu (PDF/DOCX/ảnh) · [C] Quét thêm nguồn Jira khác (→ workflow 01) · [D] Dừng`.
