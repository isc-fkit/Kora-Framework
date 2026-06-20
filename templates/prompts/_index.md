---
description: Bản đồ ROLE → prompt template + doc template. Luồng phân tích (workflow 03) đọc file này để hỏi role rồi nạp đúng prompt + đề xuất doc template.
---

# Bản đồ Role → Template

> **ĐỘNG (dynamic) theo domain + vai trò.** Cùng 1 yêu cầu, prompt + output đổi theo **vai trò** user
> chọn và **domain** đang cấu hình. Đổi vai trò/domain → kết quả đổi theo, không cần sửa template.

Khi user yêu cầu phân tích, **HỎI role trước** (AskUserQuestion), rồi nạp prompt template tương ứng,
**hỏi/áp domain rule**, và **đề xuất doc template** để xuất tài liệu.

| Role | Prompt template | Doc template (xuất tài liệu) | Output chính |
|---|---|---|---|
| **BA** — Business Analyst | `templates/prompts/role-ba.md` | `templates/docs/BRD-template.md`, `PRD-template.md` | Actors, tính năng, user story, BRD/PRD |
| **PO** — Product Owner | `templates/prompts/role-po.md` | `templates/docs/BRD-template.md` | Business value, KPI, ưu tiên MoSCoW |
| **SA** — Solution Architect | `templates/prompts/role-sa.md` | `templates/docs/PRD-template.md` (Part B) / SDD | Kiến trúc, data model, API, NFR |
| **QA** — Quality Assurance | `templates/prompts/role-qa.md` | (Test plan) | AC, test scenario, edge case |
| **Khác** | mặc định `role-ba.md` | — | hỏi user mô tả role rồi chọn template gần nhất |

**Ví dụ OUTPUT mẫu (đã điền):** `templates/examples/BRD-sample-giahan.md`, `templates/examples/PRD-sample-giahan.md`.

**ĐẦU RA CHUẨN TỰ ĐỘNG → `templates/prompts/ba-prompt-library.md`.** Sau khi chọn role + "Có template",
workflow 03 nạp thư viện 20 artifact này; mọi US / AC / BR / FR / NFR / validation / test ghi ra **theo định
dạng chuẩn TỰ ĐỘNG** (user không cần yêu cầu format). Vai trò lọc *tập artifact*: BA {01–05,12,15} · PO {01,03,13+KPI/MoSCoW} · SA {06,07,14,17,18} · QA {05,08,09,19,20}.

**Quy ước placeholder trong prompt:**
- `[domain]` ← domain hiện tại (`config/factory-config.yaml > domain.preset`).
- `[<<YÊU CẦU>>]` ← yêu cầu user nhập.
- Áp THÊM rule từ `config/domain-rules.md` (ngưỡng, pháp lý, thận trọng theo domain).
