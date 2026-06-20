---
document_type: BRD
template_version: "2.1-lean"
status: Draft            # Draft | In Review | Reviewed | Approved | Rejected | Superseded
project_name: ""
project_code: ""
document_version: "1.0"
classification_ref: ""   # Link Classification doc đã ký
writer_ba: ""            # Author — BA Lead Core Telco
reviewer_pm: ""          # Reviewer — PM Core Telco
approver_po: ""          # Approver — Product Owner / Client
release_date: ""         # YYYY-MM-DD
linked_prd: ""           # Link khi PRD ban hành
---

# BRD — Business Requirement Document — `[TÊN DỰ ÁN]`

> [!NOTE]
> **BRD trả lời 2 câu hỏi: dự án này LÀM CHO AI và VÌ SAO.** Không nói HOW IT WORKS (đó là việc của PRD/SDD).
> Author: Core Telco BA • Approver: Product Owner / Client. Sau khi BRD ký, BA + SA viết tiếp PRD/SDD dựa trên baseline này.

---

## Cách dùng

1. Điền **YAML frontmatter** ở đầu file — đây là source of truth cho metadata.
2. Thay mọi placeholder `[...]` bằng nội dung thật. Mục không áp dụng → ghi `N/A — lý do: ...`, đừng xóa heading.
3. Callout `> [!NOTE]` là hướng dẫn cho người viết — xóa khi finalize.
4. Tăng version → cập nhật `document_version` ở frontmatter **và** thêm dòng vào Mục 0.
5. BRD chỉ có hiệu lực sau khi đủ **3 chữ ký** ở Mục 12.

**Thứ tự đọc gợi ý:**

- Sponsor / PO (đọc nhanh): Mục 1 → Mục 3 → Mục 12
- BA / PM (viết & review): toàn bộ
- SA / Delivery (chuẩn bị PRD/SDD): Mục 4 → Mục 5 → Mục 8

---

## 0. Document history

| Version | Date | Author | Tóm tắt thay đổi | Impact downstream |
|---|---|---|---|---|
| 1.0 | `[YYYY-MM-DD]` | `[BA]` | Initial draft | — |

> [!IMPORTANT]
> Sau khi BRD đã Approved, mọi thay đổi phải qua **Change Request** và re-sign 3 chữ ký mới.

---

## 1. Executive Summary

> Tóm tắt 1 trang cho sponsor/PO đọc nhanh. Không kỹ thuật.

| Mục | Tóm tắt |
|---|---|
| **Business need** | `[1-2 câu — vấn đề/cơ hội business cốt lõi]` |
| **Solution approach (high-level)** | `[1-2 câu — hướng giải quyết ở mức business, không technical]` |
| **Expected outcomes** | `[2-3 outcome đo được — KPI chi tiết ở Mục 3]` |
| **Estimated investment** | `[Budget range + resource chính]` |
| **Timeline** | `[Go-live target + Hypercare end target]` |
| **Key risks** | `[Top 2-3 risk — chi tiết ở Mục 9]` |

---

## 2. Business Context

**Background — tại sao có dự án này?**
`[1-2 đoạn: bối cảnh business hiện tại, vấn đề/cơ hội đang tồn tại, tại sao bây giờ là thời điểm thích hợp.]`

**Pain points hiện tại:**

| # | Pain point | Tần suất / Severity | Tác động business (số liệu) |
|---|---|---|---|
| 1 | `[Mô tả cụ thể]` | `[Ngày/Tuần/Tháng] · [P0/P1/P2]` | `[VD: 30% KH drop ở bước X → mất ~500tr/tháng]` |
| 2 | `[...]` | `[...]` | `[...]` |

**Cost of inaction:** `[Nếu KHÔNG làm: mất doanh thu bao nhiêu, churn bao nhiêu, compliance risk nào?]`

---

## 3. Business Goals, Objectives & KPI

> **Goals** = đích đến (định tính). **Objectives** = mục tiêu SMART đo được. **KPI** track tiến độ tới Objectives.

**Strategic alignment:** `[Dự án hỗ trợ chiến lược/OKR nào của khối Telco — 1-2 câu]`

**Business goals (high-level):**
- `[Goal 1 — VD: Tăng customer satisfaction]`
- `[Goal 2 — VD: Giảm operational cost]`

**SMART objectives & KPI:**

| # | Objective | KPI | Baseline | Target | Timeframe |
|---|---|---|---|---|---|
| 1 | `[VD: Giảm churn]` | Monthly churn rate | 5% | ≤ 3% | 6 tháng sau go-live |
| 2 | `[VD: Tăng conversion]` | Signup → first purchase | 15% | ≥ 25% | 3 tháng sau go-live |

**Anti-metrics (KHÔNG để xấu đi):**
- `[VD: Tỷ lệ giao dịch lỗi không vượt 0.5%]`
- `[VD: Complaint volume không tăng quá 10% so với baseline]`

---

## 4. High-level Business Capabilities

> **Bridge từ BRD → PRD.** Liệt kê "khả năng business" sản phẩm phải có để đạt Goals ở Mục 3. KHÔNG phải user story chi tiết (đó là PRD).
> Ưu tiên MoSCoW: **Must-have** (không có thì không go-live) · **Should-have** (quan trọng nhưng có workaround) · **Could-have** (nice-to-have).

| # | Capability | Persona thụ hưởng | Goal liên kết | Ưu tiên |
|---|---|---|---|---|
| C1 | `[VD: Tự gia hạn gói cước online không cần gọi tổng đài]` | End customer | Goal 1 | Must-have |
| C2 | `[VD: Dashboard real-time số liệu vận hành]` | Ops Lead | Goal 2 | Must-have |
| C3 | `[Capability 3]` | `[Persona]` | `[Goal]` | Should / Could |

---

## 5. Scope, Assumptions & Dependencies

> Scope ở **mức nghiệp vụ**. Technical scope (component, API, module) ở PRD/SDD.

**In-scope (business processes):**
- `[VD: Quy trình mở thuê bao mới]`
- `[VD: Quy trình gia hạn gói cước]`

**Out-of-scope (KHÔNG thuộc dự án này):**
- `[VD: Customer self-service portal — phase 2 Q2/2026]`
- `[VD: B2B billing — không thuộc sản phẩm này]`

**Assumptions (giả định business):**

| # | Assumption | Owner validate | Status |
|---|---|---|---|
| A1 | `[VD: User có sẵn account hệ thống KYC]` | `[Team]` | Validated \| Pending |

**Dependencies (phụ thuộc business):**

| # | Dependency | Owner | ETA | Risk if delay |
|---|---|---|---|---|
| D1 | `[VD: Tích hợp CRM mới đang triển khai]` | `[Team Customer]` | `[YYYY-MM-DD]` | High \| Med \| Low |

---

## 6. Stakeholders & RACI

| Stakeholder | Vai trò chính | Quan tâm chính |
|---|---|---|
| **PO (Product Owner)** | Quyết định business cuối | Goal + KPI + budget + timeline |
| **BA Lead (Core)** | Author BRD + PRD | Chất lượng requirement |
| **SA Lead (Core)** | Author SDD | Feasibility + architecture |
| **PM Core** | Review BRD + quản scope handover | Scope + timeline |
| **PM / Tech Lead (Delivery)** | Implement & deploy | On-time, on-budget, code quality |
| **Compliance / Legal** | Duyệt pháp lý | Compliance 100% |
| **QA Trung tâm** | Audit quy trình | Chất lượng artifact |

> [!IMPORTANT]
> **Quy tắc RACI:** mỗi activity chỉ có **MỘT** Accountable (A). Không ghi "A/R" cùng ô — tách rõ ai là A, ai là R.
> R = Responsible (làm) · A = Accountable (chịu trách nhiệm cuối, chỉ 1) · C = Consulted · I = Informed.

| Activity | PO | BA | SA | PM Core | Delivery | QA TT |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Author BRD | **A** | R | C | C | I | I |
| Review BRD | C | R | C | **A** | I | C |
| Approve BRD | **A** | I | I | I | I | C |
| Author PRD / SDD | C | R | **A** | C | C | I |
| Implementation | I | C | C | C | **A**/R | I |
| UAT decision | **A** | C | I | C | R | I |

---

## 7. Business Process (As-is → To-be)

> Mức **business process**, không phải user flow chi tiết (đó là PRD). Có thể link BPMN/flowchart. Nếu không có thay đổi quy trình → ghi `N/A`.

| Aspect | As-is (hiện tại) | To-be (sau khi có sản phẩm) |
|---|---|---|
| **Diagram** | `[URL]` | `[URL]` |
| **Mô tả ngắn** | `[Ai làm, mất bao lâu]` | `[Thay đổi gì, automate phần nào]` |
| **Thời gian end-to-end** | `[VD: 3 ngày]` | `[VD: 30 phút]` |

---

## 8. Constraints & Compliance

**Business / Organizational constraints:**
- `[VD: Budget tối đa X tỷ VND]`
- `[VD: Timeline cứng — deadline YYYY-MM-DD vì regulatory]`
- `[VD: Phải tích hợp legacy A — không được thay thế]`

**Regulatory / Compliance:**

| Regulation | Phạm vi | Yêu cầu | Owner | Status |
|---|---|---|---|---|
| Luật ANM (24/2018/QH14) | `[Phạm vi]` | `[Yêu cầu]` | Compliance | Compliant \| Pending |
| NĐ 13/2023/NĐ-CP (PDPA) | `[Phạm vi]` | `[Yêu cầu]` | Legal | `[Status]` |
| PCI-DSS (nếu có thẻ) | `[Phạm vi]` | `[Yêu cầu]` | Security | `[Status]` |

---

## 9. Business Risks & Mitigations

> Risk ở **mức business** — technical risk thuộc SDD.
> Risk score: H×H = Critical · H×M/M×H = High · M×M/H×L/L×H = Medium · còn lại = Low.

| # | Risk | Likelihood | Impact | Score | Mitigation | Owner |
|---|---|:-:|:-:|:-:|---|---|
| R1 | `[VD: User không adopt sản phẩm mới]` | H | H | **Critical** | `[Training + change mgmt]` | `[Owner]` |
| R2 | `[VD: Competitor launch trước]` | M | H | High | `[Mitigation]` | `[Owner]` |

---

## 10. Timeline & Milestones

> Mức business — milestone lớn, không phải sprint plan.

| Milestone | Mục tiêu business | Owner | Deadline |
|---|---|---|---|
| **M1 — BRD approved** | PO confirm goal + scope, BRD ký xong | BA Lead | `[YYYY-MM-DD]` |
| **M2 — PRD + SDD ready** | Detail spec sẵn sàng review | BA + SA | `[YYYY-MM-DD]` |
| **M3 — Handover** | Biên bản chuyển giao Core → Delivery ký | Core + Delivery + QA | `[YYYY-MM-DD]` |
| **M4 — Dev complete + UAT** | Đạt AC, UAT PASS | Delivery + PO | `[YYYY-MM-DD]` |
| **M5 — Go-live** | Sản phẩm production | Delivery + Core Ops | `[YYYY-MM-DD]` |
| **M6 — Hypercare end** | Stable, chuyển sang Warranty | Delivery + Core Ops | `[YYYY-MM-DD]` |

---

## 11. Glossary & Open Questions

**Glossary (thuật ngữ business):** thuật ngữ technical thuộc Glossary của PRD/SDD.

| Thuật ngữ | Định nghĩa business | Note |
|---|---|---|
| `[VD: Active subscriber]` | `[Thuê bao có ≥1 giao dịch trong 30 ngày]` | `[Loại trừ test account]` |

**Open questions** — phải resolve **trước khi PRD bắt đầu**:

| # | Question | Owner resolve | Deadline | Status |
|---|---|---|---|---|
| Q1 | `[VD: Có cần support multi-currency?]` | `[PO]` | `[YYYY-MM-DD]` | Open \| Resolved |

---

## 12. Acceptance Checklist & Sign-off

**Checklist** (BA tự kiểm trước Review; PM Reviewer dùng để quyết approve hay trả về):

- [ ] Mọi placeholder `[...]` đã điền hoặc đánh dấu `N/A — lý do`
- [ ] Mục 1 gọn 1 trang, không kỹ thuật
- [ ] Mọi Objective (Mục 3) đều SMART — có Baseline, Target, Timeframe
- [ ] Capabilities (Mục 4) có ưu tiên MoSCoW rõ ràng
- [ ] In-scope / out-of-scope (Mục 5) không overlap, không gap
- [ ] Mọi Assumption có Owner validate + Status
- [ ] RACI (Mục 6) không có "A/R" cùng ô
- [ ] Risk Critical/High (Mục 9) đều có Mitigation + Owner
- [ ] Open questions (Mục 11) đều Resolved trước khi sign-off
- [ ] Glossary cover hết thuật ngữ business trong văn bản

**Sign-off** — BRD chỉ có hiệu lực khi đủ **3 chữ ký**:

| Vai trò | Họ tên | Vị trí | Chữ ký | Ngày |
|---|---|---|---|---|
| **Writer (BA Lead)** | `[Họ tên]` | BA Lead Core Telco | ________ | `[Date]` |
| **Reviewer (PM Core)** | `[Họ tên]` | PM Core Telco | ________ | `[Date]` |
| **Approver (Client / PO)** | `[Họ tên]` | Product Owner | ________ | `[Date]` |

> [!NOTE]
> **Đủ 3 chữ ký:** BA + SA bắt đầu viết PRD/SDD dựa trên BRD này.
> **Nếu PRD/SDD phát hiện cần đổi BRD:** raise Change Request → cập nhật Mục 0 → re-sign 3 chữ ký mới.

---

<!-- ==========================================================
     END OF BRD (LEAN)
     Template version: 2.1-lean
     Maintained by: ISC AI-SDLC Governance Team
     Aligned with: IIBA BABOK v3, IEEE 29148
========================================================== -->
