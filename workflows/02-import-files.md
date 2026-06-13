# Workflow 02 — Nạp tri thức từ file (PDF / DOCX / MD / zip Obsidian)

> Trigger: user gửi file hoặc nhắn "nạp tài liệu" (confirm ý định trước). Mỗi file đi qua:
> raw → normalized → classified → pending-approval → (approve) → KB chính.

## Bước 1 — Tiếp nhận

| Loại file | Hành động |
|---|---|
| PDF | Copy vào `inbox/raw/pdf/`, trích text (dùng skill pdf) |
| DOCX | Copy vào `inbox/raw/docx/`, trích text (dùng skill docx) |
| MD / TXT | Copy vào `inbox/raw/text/` |
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

## Bước 3 — Phân loại (Auto Classifier)

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

1. Ghi vào `docs/` đúng vị trí (feature → `docs/03-features/F-xxx/source/`,
   domain → `docs/01-domain/`, thuật ngữ → `docs/08-glossary/`...).
2. Tạo/cập nhật notes trong Obsidian vault + backlink.
3. Cập nhật `.kb/index.json`, `relation-graph.json`, `source-registry.json`, `changelog.md`.
4. Chuyển batch sang `inbox/approved/` (hoặc `rejected/`).
