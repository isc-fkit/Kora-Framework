---
title: BA Prompt Library — 20 artifact chuẩn (9 nhóm)
description: Nguồn CHUẨN của định dạng đầu ra. Workflow 03 + role prompts nạp file này để khi phân tích & ghi tài liệu, mọi artifact TỰ ĐỘNG đúng định dạng chuẩn — user KHÔNG cần yêu cầu "viết theo format X".
applies_to: workflows/03-request.md (Bước 0/2/4), templates/prompts/role-*.md
---

# Thư viện Prompt BA — 20 artifact chuẩn

> **Đây là NGUỒN CHUẨN của các định dạng đầu ra.** Khi `workflows/03-request.md` phân tích
> (Bước 2–3) và **ghi tài liệu (Bước 4)**, KORA **tự động** xuất mỗi artifact theo đúng định
> dạng dưới đây — KHÔNG cần user yêu cầu định dạng. **Vai trò** (BA/PO/SA/QA, xem `_index.md`)
> quyết định *tập artifact* nào được sinh; **`config/domain-rules.md`** áp thêm rule domain.

## 0. Bản đồ: Bước BA → artifact → định dạng → file ghi

| Bước BA | Artifact | Prompt | File ghi `docs/03-features/F-xxx/source/` |
|---|---|---|---|
| B1 · Clarify | Câu hỏi làm rõ | 02 | hỏi trong phiên (`[CẦN XÁC NHẬN]`) |
| B2 · US + AC | User Story | 04 | `01-user-document.md` |
| B2 · US + AC | Acceptance Criteria | 05 | `04-acceptance-criteria.md` |
| (BR) | Business Rules | 01 / 03 | `03-business-rules.md` |
| (Validation) | Validation + Error msg | 08 / 09 | `04-acceptance-criteria.md` (mục Validation) |
| (FR/NFR) | Functional / Non-functional | 06 / 07 | `02-claude-context.md` |
| B3 · Flow | User / Process Flow | 10 / 11 | Mermaid trong feature doc |
| B4 · Docs | URD / PRD / SRS | 12 / 13 / 14 | `export/` qua `/claude-knowledge-export-docs` |
| (UX) | Screen Spec / UX | 15 / 16 | `01-user-document.md` |
| (Dev) | API / Database | 17 / 18 | `02-claude-context.md` |
| B6 · Test | Test Cases / Edge | 19 / 20 | `07-test-plan.md` |

## I. Phân tích yêu cầu
- **Prompt 01 — Phân tích tổng quát.** *Output chuẩn:* danh sách đánh số — 1) Actors · 2) Tính năng chính · 3) Business goals · 4) Assumptions · 5) Thông tin còn thiếu.
- **Prompt 02 — Câu hỏi làm rõ.** *Output chuẩn:* câu hỏi nhóm theo **Business Rules / Data / UI / Technical**; đánh dấu ★ top 5 ưu tiên.
- **Prompt 03 — Feature Tree.** *Output chuẩn:* `Feature [F01]` → `Sub-feature [F01.1]…` + cột **MoSCoW** (Must/Should/Could/Won't).

## II. User Stories
- **Prompt 04 — User Story.** *Output chuẩn:* mỗi US gồm `US-[ID]: tiêu đề` / `As a [vai trò], I want to [hành động], so that [lợi ích].` / `Priority: High|Medium|Low` / `Story Points`. Tối thiểu 3 US, bao phủ nhiều vai trò; ghi rõ **OUT OF SCOPE**.
- **Prompt 05 — Acceptance Criteria.** *Output chuẩn:* mỗi AC theo `Given… When… Then…`; **BẮT BUỘC** ≥1 happy + ≥1 edge + ≥1 negative; negative ghi rõ **thông báo lỗi cụ thể** hiển thị cho user.

## III. Functional Requirements
- **Prompt 06 — FR.** *Output chuẩn:* `FR-[ID]: tiêu đề` + Mô tả ("Hệ thống phải…/Cho phép…") + Actor + Pre-condition + Post-condition.
- **Prompt 07 — NFR.** *Output chuẩn:* `NFR-[ID]: [Nhóm] – yêu cầu có con số đo lường` + Cách kiểm tra. Nhóm: Performance / Security / Scalability / Availability / Usability / Maintainability.

## IV. Validation Rules & Error Messages
- **Prompt 08 — Validation Rules.** *Output chuẩn:* bảng `| Tên trường | Kiểu | Bắt buộc | Min | Max | Định dạng | Business Rule |` + **cross-field validation** (vd Ngày kết thúc > Ngày bắt đầu).
- **Prompt 09 — Error Messages.** *Output chuẩn:* thông báo lỗi **cụ thể** (tránh "Dữ liệu không hợp lệ"), hướng dẫn cách sửa, giọng tích cực, ≤2 câu.

## V. User / Process Flow
- **Prompt 10 — User Flow.** *Output chuẩn:* Mermaid `flowchart TD` (start → bước → điểm quyết định → end, đủ happy path + error path) + giải thích ngắn từng bước.
- **Prompt 11 — Process Flow (swimlane).** *Output chuẩn:* Mermaid swimlane theo vai trò + điểm handoff + bước phê duyệt (hình thoi) + danh sách rủi ro quy trình.

## VI. Tài liệu BA
- **Prompt 12 — URD · Prompt 13 — PRD · Prompt 14 — SRS.** *Output chuẩn:* theo `templates/docs/BRD-template.md` / `PRD-template.md` (cấu trúc mục cố định). Xuất qua `/claude-knowledge-export-docs` → `export/`.

## VII. Hỗ trợ UX / UI
- **Prompt 15 — Screen Spec.** *Output chuẩn:* bảng `| Element | Loại | Label | Placeholder | Validation | Hành động |` + Mục đích màn hình + Navigation + Ghi chú responsive.
- **Prompt 16 — UX Improvement.** *Output chuẩn:* đề xuất theo Cognitive load / Error prevention / Feedback / Consistency / Accessibility; mỗi đề xuất kèm **Priority** + **Effort**.

## VIII. Hỗ trợ Dev
- **Prompt 17 — API Requirements.** *Output chuẩn:* mỗi endpoint `[METHOD] /api/v1/[path]` + Request (headers / params / body schema) + Response (200/201 + mã lỗi) + business rules + auth (Có/Không).
- **Prompt 18 — Database.** *Output chuẩn:* mỗi bảng `| Cột | Kiểu dữ liệu | Nullable | Mặc định | Mô tả nghiệp vụ |` + Indexes + Quan hệ (FK) + sơ đồ ER tóm tắt.

## IX. Hỗ trợ QA
- **Prompt 19 — Test Cases.** *Output chuẩn:* `TC-[ID] | tên` + Loại (Happy/Edge/Negative) + Precondition + Bước + Kết quả mong đợi + Priority. Tối thiểu **3 happy · 2 edge · 2 negative**.
- **Prompt 20 — Edge Cases & rủi ro.** *Output chuẩn:* nhóm Boundary values / Concurrent / Network-timeout / Xung đột phân quyền / Data integrity / Third-party; mỗi kịch bản kèm Mức rủi ro (High/Med/Low) + cách xử lý.

## Vai trò → tập artifact (lăng kính lọc)
- **BA** → 01–05, 12, 15 (US, AC, BR, URD, Screen Spec).
- **PO** → 01, 03, 13 + Business value / KPI (SMART) / MoSCoW / PRD.
- **SA** → 06, 07, 14, 17, 18 (FR, NFR, SRS, API, DB, kiến trúc).
- **QA** → 05, 08, 09, 19, 20 (AC, Validation, Error msg, Test Cases, Edge).

## Quy ước (bất biến)
- Instruction tiếng Việt; **technical term giữ EN**: User Story, Given-When-Then, FR/NFR, Mermaid, MoSCoW, endpoint…
- `[domain]` ← `config/factory-config.yaml`; áp THÊM `config/domain-rules.md`. Thiếu nguồn → `[CẦN XÁC NHẬN]`; tri thức chuyên môn chưa có nguồn → `[CẦN XÁC NHẬN CHUYÊN MÔN]`.
- Mọi artifact phải **trace nguồn** (file/issue) — bám tri thức KB, không bịa (CLAUDE.md §1).
