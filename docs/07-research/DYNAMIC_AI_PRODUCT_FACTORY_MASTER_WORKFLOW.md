# Dynamic AI Product Factory — Master Workflow Specification

## 1. Mục tiêu hệ thống

Xây dựng một hệ thống Dynamic AI Product Factory giúp user non-technical có thể đưa vào:

* Link Jira project / board / epic / user story
* File DOCX
* File PDF
* File Excel / CSV
* Tài liệu thô copy-paste
* Yêu cầu mới từ CEO / PO / BA / PM

Sau đó hệ thống tự động:

1. Import dữ liệu nguồn.
2. Phân loại tài liệu.
3. Trích xuất tri thức.
4. Tạo Obsidian Knowledge Base.
5. Xây dựng quan hệ Project → Epic → User Story → Feature → Business Rule → Acceptance Criteria.
6. Tạo tài liệu `.md` cho Claude hiểu.
7. Tạo tài liệu chuẩn cho người đọc dạng DOCX/PDF.
8. Chờ user approve.
9. Sau khi approve thì cập nhật KB chính.
10. Sinh prompt cho Claude Design.
11. Sinh workflow / wireframe / prototype.
12. Sinh implementation plan cho Claude Code.
13. Đồng bộ thay đổi ngược lại vào KB, changelog và relation graph.

Hệ thống phải hoạt động theo nguyên tắc:

> Không đưa dữ liệu thô trực tiếp vào Knowledge Base chính.
> Không để AI tự ghi tri thức chính thức nếu user chưa approve.
> Không chạy Claude Design hoặc Claude Code trước khi requirement được chốt.

---

## 2. Ý tưởng kiến trúc tổng thể

```text
User / CEO / BA / PM
        ↓
Claude Cowork Orchestrator
        ↓
Import Layer
Jira / DOCX / PDF / CSV / Raw Text
        ↓
Raw Inbox
        ↓
Auto Classifier
        ↓
Knowledge Extractor
        ↓
Conflict & Duplicate Checker
        ↓
Approval Gate
        ↓
Knowledge Base Writer
        ↓
Obsidian Vault + Markdown KB + Git
        ↓
Document Generator
MD → DOCX → PDF
        ↓
Claude Design Prompt Generator
        ↓
Claude Design / Prototype / Wireframe
        ↓
Claude Code Plan / Sourcebase Execution
        ↓
Sync Back
Changelog + ADR + Relation Graph + Source Registry
```

---

## 3. Các layer chính

## 3.1 Import Layer

Nhiệm vụ:

* Nhận dữ liệu đầu vào từ Jira, DOCX, PDF, CSV hoặc text thô.
* Không phân tích sâu ngay.
* Chỉ đưa dữ liệu vào vùng `inbox/raw`.

Nguồn hỗ trợ:

```text
Jira:
- Project
- Board
- Epic
- User Story
- Task
- Bug
- Sub-task
- Comment
- Attachment metadata
- Linked issue

File:
- DOCX
- PDF
- CSV
- XLSX
- Markdown
- Raw text
```

Output:

```text
inbox/raw/
  jira/
  docx/
  pdf/
  csv/
  text/
```

---

## 3.2 Normalization Layer

Nhiệm vụ:

* Chuẩn hóa dữ liệu từ nhiều nguồn về một schema chung.
* Không thay đổi nghĩa.
* Không tự suy diễn business rule chính thức.

Schema chuẩn:

```json
{
  "source_id": "SRC-JIRA-PROJ-102",
  "source_type": "jira_issue",
  "title": "Xin quyền Apple HealthKit",
  "raw_content": "...",
  "project": "PROJ",
  "issue_key": "PROJ-102",
  "issue_type": "Story",
  "status": "To Do",
  "parent": "PROJ-101",
  "links": [],
  "attachments": [],
  "comments": [],
  "imported_at": "ISO_DATETIME"
}
```

Output:

```text
inbox/normalized/
```

---

## 3.3 Auto Classifier

Nhiệm vụ:

Tự phân loại tài liệu hoặc issue thành:

```text
- Project
- Epic
- User Story
- Requirement
- Business Rule Candidate
- Acceptance Criteria Candidate
- Design Note
- API Spec
- Test Case
- Bug Report
- Technical Task
- Decision Candidate
- Domain Knowledge
- Unknown
```

Luật:

* Nếu dữ liệu có dạng “As a user...” → user_story.
* Nếu dữ liệu có Given/When/Then → acceptance_criteria_candidate.
* Nếu dữ liệu mô tả điều kiện bắt buộc của hệ thống → business_rule_candidate.
* Nếu dữ liệu mô tả màn hình, UI, layout → design_note.
* Nếu dữ liệu mô tả lỗi → bug_report.
* Nếu không chắc chắn → unknown, không ghi vào KB chính.

Output:

```text
inbox/classified/
```

---

## 3.4 Knowledge Extractor

Nhiệm vụ:

Trích xuất tri thức từ tài liệu đã phân loại:

```text
- Feature candidate
- Functional requirement
- Non-functional requirement
- Business rule
- Acceptance criteria
- User flow
- Screen
- API
- Data field
- Permission
- Error state
- Empty state
- Dependency
- Risk
- Open question
```

Luật:

* Không tự bịa tri thức.
* Nếu thiếu thông tin, đánh dấu `[CẦN XÁC NHẬN]`.
* Nếu liên quan y tế, đánh dấu `[CẦN XÁC NHẬN CHUYÊN MÔN]` khi chưa có nguồn rõ.
* Mọi tri thức phải trace được về source.

---

## 3.5 Conflict & Duplicate Checker

Nhiệm vụ:

Trước khi ghi KB, kiểm tra:

```text
- Requirement mới có trùng requirement cũ không?
- Business rule mới có mâu thuẫn rule cũ không?
- Acceptance criteria có lệch với user story không?
- Feature mới có phụ thuộc feature cũ không?
- Có cùng màn hình / cùng source file bị ảnh hưởng không?
```

Output phải có:

```text
- New knowledge
- Duplicate candidate
- Conflict candidate
- Missing information
- Suggested update
```

---

## 3.6 Approval Gate

Trước khi cập nhật KB chính, user phải duyệt.

Các trạng thái:

```text
Approve all
Approve selected
Reject
Need revision
Need more information
```

Nếu user chưa approve:

* Không ghi vào `docs/features`.
* Không cập nhật `relation-graph.json` chính thức.
* Không sinh DOCX/PDF chính thức.
* Không chạy Claude Design.
* Không chạy Claude Code.

---

## 3.7 Knowledge Base Writer

Sau khi user approve, hệ thống mới ghi vào KB chính.

Cấu trúc KB:

```text
ai-product-factory/
  CLAUDE.md

  inbox/
    raw/
    normalized/
    classified/
    pending-approval/
    approved/
    rejected/

  docs/
    00-index.md
    01-domain/
    02-product/
    03-features/
    04-design/
    05-architecture/
    06-decisions/
    07-research/
    08-glossary/

  obsidian-vault/
    00_Index/
    01_Projects/
    02_Epics/
    03_UserStories/
    04_BusinessRules/
    05_AcceptanceCriteria/
    06_Features/
    07_Decisions/
    _system/

  .kb/
    index.json
    relation-graph.json
    source-registry.json
    changelog.md
    rules.md
```

---

## 4. Cấu trúc mỗi feature

Mỗi feature phải có folder riêng:

```text
docs/03-features/F-001-healthkit/
  README.md

  source/
    01-user-document.md
    02-claude-context.md
    03-business-rules.md
    04-acceptance-criteria.md
    05-design-brief.md
    06-implementation-plan.md
    07-test-plan.md
    changelog.md

  export/
    F-001-healthkit-URD-v1.0.docx
    F-001-healthkit-URD-v1.0.pdf
    F-001-healthkit-SRS-v1.0.docx
    F-001-healthkit-SRS-v1.0.pdf
```

Ý nghĩa:

```text
source/  → Claude đọc và thực thi
export/  → người đọc / CEO / PM / BA dùng
```

---

## 5. Hai loại tài liệu bắt buộc cho mỗi feature

## 5.1 `01-user-document.md`

Dành cho người đọc.

Yêu cầu:

* Tiếng Việt chuẩn.
* Dễ hiểu.
* Dành cho CEO, PO, BA, PM, Design, Dev, Tester.
* Có mục tiêu, phạm vi, luồng, rule, tiêu chí nghiệm thu.
* Có thể export sang DOCX/PDF.

Cấu trúc:

```markdown
# Tài liệu yêu cầu tính năng

## 1. Mục tiêu

## 2. Phạm vi

## 3. Đối tượng sử dụng

## 4. Luồng sử dụng chính

## 5. Quy tắc nghiệp vụ

## 6. Tiêu chí nghiệm thu

## 7. Tác động đến màn hình

## 8. Tác động đến dữ liệu

## 9. Rủi ro và ghi chú

## 10. Câu hỏi cần xác nhận
```

---

## 5.2 `02-claude-context.md`

Dành cho Claude Cowork, Claude Design, Claude Code.

Yêu cầu:

* Có metadata.
* Có ID rõ ràng.
* Có related documents.
* Có related features.
* Có related screens.
* Có business rules.
* Có acceptance criteria.
* Có design rules.
* Có code rules.
* Có guardrails.
* Có instruction cho Claude Design và Claude Code.

Cấu trúc:

```markdown
# CLAUDE CONTEXT — F-001 Feature Name

## Metadata

- Feature ID:
- Feature Name:
- Domain:
- Status:
- Version:
- Source of Truth:

## Purpose

## Related Documents

## Related Features

## Related Screens

## Business Rules

## Acceptance Criteria

## Design Rules

## Code Rules

## Claude Design Instruction

## Claude Code Instruction

## Guardrails

## Sync Rules
```

---

## 6. Obsidian Knowledge Graph

Obsidian phải hiểu quan hệ bằng:

```text
- Backlink [[...]]
- YAML frontmatter
- Tags
- Folder structure
- relation-graph.json
- source-registry.json
```

Ví dụ Project note:

```markdown
---
type: project
source: jira
jira_project_key: PROJ
---

# MyApp

## Epics

- [[PROJ-101_Apple-HealthKit]]

## Related Features

- [[F-001_Apple-HealthKit]]
```

Ví dụ User Story note:

```markdown
---
type: user_story
source: jira
jira_key: PROJ-102
parent_epic: PROJ-101
---

# PROJ-102 — Xin quyền Apple HealthKit

## Parent Epic

- [[PROJ-101_Apple-HealthKit]]

## Related Feature

- [[F-001_Apple-HealthKit]]

## Business Rules

- [[BR-HK-001]]

## Acceptance Criteria

- [[AC-HK-001]]
```

---

## 7. Relation Graph

File:

```text
.kb/relation-graph.json
```

Schema:

```json
{
  "generated_at": "ISO_DATETIME",
  "nodes": [
    {
      "id": "PROJ-102",
      "type": "user_story",
      "title": "Xin quyền Apple HealthKit",
      "status": "To Do",
      "project": "PROJ"
    }
  ],
  "edges": [
    {
      "from": "PROJ",
      "to": "PROJ-101",
      "relation": "has_epic"
    },
    {
      "from": "PROJ-101",
      "to": "PROJ-102",
      "relation": "has_story"
    },
    {
      "from": "PROJ-102",
      "to": "BR-HK-001",
      "relation": "extracts_rule"
    },
    {
      "from": "PROJ-102",
      "to": "AC-HK-001",
      "relation": "defines_acceptance_criteria"
    }
  ]
}
```

Claude phải dùng file này để hiểu:

```text
- Project nào có Epic nào
- Epic nào có Story nào
- Story nào sinh ra BR/AC nào
- Feature nào phụ thuộc feature nào
- Rule nào ảnh hưởng màn hình/code/test nào
```

---

## 8. Source Registry

File:

```text
.kb/source-registry.json
```

Mục tiêu:

* Trace mọi tri thức về nguồn gốc.
* Biết rule nào lấy từ Jira issue nào.
* Biết tài liệu nào sinh ra feature nào.
* Biết lần import nào đã được approve.

Schema:

```json
{
  "source_id": "SRC-JIRA-PROJ-102",
  "source_type": "jira_issue",
  "origin": "Jira",
  "jira_key": "PROJ-102",
  "title": "Xin quyền Apple HealthKit",
  "status": "approved",
  "mapped_features": ["F-001-healthkit"],
  "generated_documents": [
    "01-user-document.md",
    "02-claude-context.md",
    "03-business-rules.md",
    "04-acceptance-criteria.md"
  ],
  "approved_at": "ISO_DATETIME"
}
```

---

## 9. Dynamic Workflow Commands

Hệ thống cần hỗ trợ các command:

```text
/init-project
/import-jira
/import-source
/classify-source
/analyze-impact
/propose-kb-update
/approve-update
/generate-docs
/export-docs
/generate-design-brief
/sync-claude-design
/generate-code-plan
/sync-code-result
/update-changelog
```

---

## 10. Workflow 1 — Init Project

Command:

```text
/init-project name="MyApp"
```

Luồng:

```text
1. Tạo base folder.
2. Tạo CLAUDE.md.
3. Tạo .kb.
4. Tạo docs.
5. Tạo obsidian-vault.
6. Tạo inbox.
7. Tạo workflow templates.
8. Tạo initial changelog.
```

---

## 11. Workflow 2 — Import Jira

Command:

```text
/import-jira mode=full
```

Luồng:

```text
1. Đọc Jira config từ .env.local.
2. Kết nối Jira API.
3. Lấy project.
4. Lấy board nếu có.
5. Lấy Epic / Story / Task / Bug / Sub-task.
6. Lấy parent, linked issue, comments, attachment metadata.
7. Normalize.
8. Ghi vào inbox/raw và inbox/normalized.
9. Tạo raw Obsidian notes.
10. Tạo raw relation graph.
11. Tạo import review report.
12. Chờ user approve.
```

---

## 12. Workflow 3 — Classify Source

Command:

```text
/classify-source source="jira-import-batch-001"
```

Luồng:

```text
1. Đọc raw source.
2. Phân loại issue/document.
3. Group theo feature candidate.
4. Trích xuất requirement candidate.
5. Trích xuất business rule candidate.
6. Trích xuất acceptance criteria candidate.
7. Phát hiện thiếu thông tin.
8. Phát hiện mâu thuẫn.
9. Tạo pending approval report.
```

---

## 13. Workflow 4 — Approve Update

Command:

```text
/approve-update batch="jira-import-batch-001"
```

Luồng:

```text
1. Kiểm tra pending report.
2. Nếu user approve all:
   - ghi KB chính;
   - tạo feature folder;
   - tạo Obsidian backlink;
   - update relation graph;
   - update source registry;
   - update changelog.
3. Nếu user approve selected:
   - chỉ ghi phần được duyệt.
4. Nếu reject:
   - đưa vào inbox/rejected.
```

---

## 14. Workflow 5 — Generate Docs

Command:

```text
/generate-docs feature="F-001-healthkit"
```

Luồng:

```text
1. Đọc feature source.
2. Tạo 01-user-document.md.
3. Tạo 02-claude-context.md.
4. Tạo 03-business-rules.md.
5. Tạo 04-acceptance-criteria.md.
6. Tạo 05-design-brief.md.
7. Tạo 06-implementation-plan.md.
8. Tạo 07-test-plan.md.
9. Export DOCX/PDF nếu cần.
10. Ghi changelog.
```

---

## 15. Workflow 6 — Claude Design

Command:

```text
/generate-design-brief feature="F-001-healthkit"
```

Luồng:

```text
1. Đọc user document.
2. Đọc claude context.
3. Đọc business rules.
4. Đọc acceptance criteria.
5. Đọc design system hiện tại.
6. Đọc prototype map hiện tại.
7. Tạo prompt cho Claude Design.
8. Nếu có Design Adapter:
   - gửi prompt sang Claude Design;
   - tạo workflow/wireframe/prototype;
   - lấy output;
   - sync lại design decision vào KB.
9. Nếu chưa có adapter:
   - xuất prompt để user copy thủ công.
```

---

## 16. Workflow 7 — Claude Code

Command:

```text
/generate-code-plan feature="F-001-healthkit"
```

Luồng:

```text
1. Đọc claude context.
2. Đọc business rules.
3. Đọc acceptance criteria.
4. Đọc source map.
5. Tìm file code liên quan.
6. Đề xuất implementation plan.
7. User approve.
8. Mới được sửa sourcebase.
9. Sau khi sửa, update changelog và test plan.
```

---

## 17. Approval Gates

Hệ thống phải có 4 cổng duyệt:

```text
Gate 1 — Approve extracted knowledge
Gate 2 — Approve generated documentation
Gate 3 — Approve design changes
Gate 4 — Approve code changes
```

Không được vượt gate nếu user chưa duyệt.

---

## 18. Changelog Rule

Mọi thay đổi phải ghi:

```text
- ngày giờ
- source
- feature bị ảnh hưởng
- file đã thay đổi
- lý do thay đổi
- người duyệt
- version trước / version sau
```

Format:

```markdown
## 2026-06-13 — F-001 HealthKit

### Changed

- Cập nhật business rule BR-HK-001 từ Jira issue PROJ-102.
- Tạo acceptance criteria AC-HK-001.
- Cập nhật relation graph.

### Source

- SRC-JIRA-PROJ-102

### Approved By

- User
```

---

## 19. Guardrails

Claude phải tuân thủ:

1. Không tự bịa requirement.
2. Không ghi KB chính nếu chưa approve.
3. Không sửa prototype trước khi cập nhật tài liệu.
4. Không sửa code trước khi có BR/AC.
5. Không tự tạo ngưỡng y tế nếu không có nguồn chuyên môn.
6. Không dùng password Jira.
7. Không in token ra log.
8. Không lưu secret trong Markdown.
9. Không đưa dữ liệu raw vào tài liệu chính thức khi chưa được phân loại.
10. Mọi output phải trace được về source.

---

## 20. Definition of Done

Hệ thống được xem là hoàn thành khi:

```text
[ ] User có thể đưa Jira link/file DOCX/PDF
[ ] Hệ thống import được vào inbox/raw
[ ] Hệ thống normalize được dữ liệu
[ ] Hệ thống phân loại được source
[ ] Hệ thống tạo Obsidian notes
[ ] Hệ thống tạo backlink
[ ] Hệ thống tạo relation-graph.json
[ ] Hệ thống tạo source-registry.json
[ ] Hệ thống tạo pending approval report
[ ] User approve được
[ ] Hệ thống ghi vào KB chính
[ ] Hệ thống sinh .md cho Claude
[ ] Hệ thống sinh DOCX/PDF cho người đọc
[ ] Hệ thống sinh prompt Claude Design
[ ] Hệ thống sinh implementation plan cho Claude Code
[ ] Hệ thống ghi changelog
```
