---
document_type: BRD
template_version: "2.1-lean"
status: Approved
project_name: "Self-service Gia hạn Gói cước Online"
project_code: "TEL-RENEW-2026"
document_version: "1.0"
classification_ref: "CLS-2026-014 (Confidential — Customer data)"
writer_ba: "Nguyễn Thị Hương — BA Lead Core Telco"
reviewer_pm: "Trần Văn Khoa — PM Core Telco"
approver_po: "Lê Minh Tuấn — Product Owner"
release_date: "2026-03-02"
linked_prd: "PRD-TEL-RENEW-2026 (ban hành 2026-03-28)"
---

# BRD — Business Requirement Document — `Self-service Gia hạn Gói cước Online`

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
| 0.1 | 2026-02-12 | N.T.Hương | Initial draft sau workshop với Care & Billing | — |
| 0.5 | 2026-02-23 | N.T.Hương | Bổ sung KPI baseline từ data team, chốt out-of-scope | — |
| 1.0 | 2026-03-02 | N.T.Hương | Approved baseline | Khởi động PRD + SDD |

> [!IMPORTANT]
> Sau khi BRD đã Approved, mọi thay đổi phải qua **Change Request** và re-sign 3 chữ ký mới.

---

## 1. Executive Summary

> Tóm tắt 1 trang cho sponsor/PO đọc nhanh. Không kỹ thuật.

| Mục | Tóm tắt |
|---|---|
| **Business need** | Tổng đài đang quá tải vì cuộc gọi gia hạn gói cước; khách hàng phải chờ lâu và một phần rời mạng ngay tại thời điểm hết hạn. Cần kênh tự gia hạn để giảm tải và giữ chân thuê bao. |
| **Solution approach (high-level)** | Cho thuê bao tự xem gói đang dùng, chọn gia hạn và thanh toán ngay trên app/web, nhận xác nhận tức thì — không cần gọi tổng đài. |
| **Expected outcomes** | (1) Giảm 50% cuộc gọi gia hạn; (2) ≥ 60% lượt gia hạn qua kênh số trong 6 tháng; (3) Giảm churn tại điểm gia hạn từ 8% → ≤ 5%. |
| **Estimated investment** | ~2,4 tỷ VND (1 squad: 4 dev, 1 SA, 1 QA, 1 BA × 4 tháng) + chi phí cổng thanh toán. |
| **Timeline** | Go-live mục tiêu: 2026-06-08. Hypercare end: 2026-06-29. |
| **Key risks** | R1 — Khách hàng quen gọi tổng đài, chậm adopt kênh số. R2 — Cổng thanh toán/billing legacy không ổn định giờ cao điểm. |

---

## 2. Business Context

**Background — tại sao có dự án này?**
Hiện 100% lượt gia hạn gói cước phải thực hiện qua tổng đài hoặc điểm giao dịch. Mỗi tháng có khoảng 120.000 cuộc gọi liên quan gia hạn, chiếm ~40% tổng lưu lượng tổng đài, đẩy thời gian chờ trung bình lên 4–6 phút vào cuối tháng. App tự chăm sóc (self-care) đã có sẵn nhưng chưa hỗ trợ luồng gia hạn. Quý này là thời điểm thích hợp vì app self-care vừa nâng cấp xong nền tảng đăng nhập và đã tích hợp ví điện tử nội bộ.

**Pain points hiện tại:**

| # | Pain point | Tần suất / Severity | Tác động business (số liệu) |
|---|---|---|---|
| 1 | Thuê bao phải gọi tổng đài để gia hạn, chờ lâu giờ cao điểm | Hàng ngày · P1 | ~120.000 cuộc/tháng × 15.000đ xử lý ≈ **1,8 tỷ/tháng** chi phí tổng đài |
| 2 | Hết hạn ngoài giờ làm việc → không gia hạn kịp → mất kết nối | Hàng ngày · P1 | ~8% thuê bao rời mạng ngay tại điểm gia hạn |
| 3 | Nhân viên tổng đài thao tác thủ công, dễ chọn sai gói | Tuần · P2 | ~3% ticket khiếu nại "gia hạn sai gói" |

**Cost of inaction:** Nếu không làm, chi phí tổng đài cho gia hạn giữ ở mức ~21,6 tỷ/năm, churn tại điểm gia hạn tiếp tục ở 8% (ước tính mất ~9 tỷ doanh thu/năm), và áp lực tổng đài tăng theo mùa khuyến mãi.

---

## 3. Business Goals, Objectives & KPI

> **Goals** = đích đến (định tính). **Objectives** = mục tiêu SMART đo được. **KPI** track tiến độ tới Objectives.

**Strategic alignment:** Hỗ trợ OKR khối Telco 2026 "Số hóa 70% tương tác chăm sóc khách hàng" và mục tiêu giảm chi phí vận hành (OpEx) 10%.

**Business goals (high-level):**
- Goal 1 — Tăng sự hài lòng & giữ chân thuê bao tại thời điểm gia hạn.
- Goal 2 — Giảm chi phí vận hành tổng đài.

**SMART objectives & KPI:**

| # | Objective | KPI | Baseline | Target | Timeframe |
|---|---|---|---|---|---|
| 1 | Chuyển lượt gia hạn sang kênh số | Tỷ lệ gia hạn qua app/web | 0% | ≥ 60% | 6 tháng sau go-live |
| 2 | Giảm tải tổng đài | Số cuộc gọi gia hạn/tháng | 120.000 | ≤ 60.000 | 6 tháng sau go-live |
| 3 | Giữ chân thuê bao tại gia hạn | Churn rate tại điểm gia hạn | 8% | ≤ 5% | 6 tháng sau go-live |

**Anti-metrics (KHÔNG để xấu đi):**
- Tỷ lệ giao dịch gia hạn lỗi không vượt 0,5%.
- Complaint volume tổng thể không tăng quá 10% so với baseline.

---

## 4. High-level Business Capabilities

> **Bridge từ BRD → PRD.** Liệt kê "khả năng business" sản phẩm phải có để đạt Goals ở Mục 3. KHÔNG phải user story chi tiết (đó là PRD).
> Ưu tiên MoSCoW: **Must-have** (không có thì không go-live) · **Should-have** (quan trọng nhưng có workaround) · **Could-have** (nice-to-have).

| # | Capability | Persona thụ hưởng | Goal liên kết | Ưu tiên |
|---|---|---|---|---|
| C1 | Tự gia hạn gói cước đang dùng ngay trên app/web, không cần gọi tổng đài | End customer | Goal 1 | Must-have |
| C2 | Xem các gói có thể gia hạn kèm giá & ưu đãi trước khi quyết định | End customer | Goal 1 | Must-have |
| C3 | Thanh toán gia hạn bằng ví điện tử nội bộ hoặc thẻ | End customer | Goal 1, 2 | Must-have |
| C4 | Nhận nhắc hạn và xác nhận gia hạn qua SMS/notification | End customer | Goal 1 | Should-have |
| C5 | Dashboard theo dõi tỷ lệ gia hạn số & tải tổng đài theo thời gian thực | Ops/Care Lead | Goal 2 | Should-have |

---

## 5. Scope, Assumptions & Dependencies

> Scope ở **mức nghiệp vụ**. Technical scope (component, API, module) ở PRD/SDD.

**In-scope (business processes):**
- Quy trình gia hạn gói cước đang dùng (giữ nguyên gói, gia hạn chu kỳ mới).
- Thanh toán gia hạn qua ví nội bộ và thẻ.
- Nhắc hạn + xác nhận kết quả gia hạn qua SMS/notification.

**Out-of-scope (KHÔNG thuộc dự án này):**
- Đổi/nâng/hạ gói (change plan) — phase 2, Q4/2026.
- Đăng ký thuê bao mới — không thuộc sản phẩm này.
- Gia hạn cho thuê bao doanh nghiệp (B2B) — quản lý qua hệ thống riêng.

**Assumptions (giả định business):**

| # | Assumption | Owner validate | Status |
|---|---|---|---|
| A1 | Thuê bao đã có tài khoản app self-care và đã định danh (KYC) | Team Customer | Validated |
| A2 | Ví điện tử nội bộ chịu được 3× lưu lượng giao dịch hiện tại không cần thay đổi | Team Payment | Pending |
| A3 | Hệ thống billing legacy cung cấp API truy vấn gói & ghi nhận gia hạn | Team Billing | Validated |

**Dependencies (phụ thuộc business):**

| # | Dependency | Owner | ETA | Risk if delay |
|---|---|---|---|---|
| D1 | API gói cước & ghi nhận gia hạn từ billing legacy | Team Billing | 2026-04-10 | High |
| D2 | Endpoint trừ tiền ví điện tử nội bộ (idempotent) | Team Payment | 2026-04-15 | High |
| D3 | Template SMS brandname đã đăng ký | Team Marketing | 2026-04-20 | Med |

---

## 6. Stakeholders & RACI

| Stakeholder | Vai trò chính | Quan tâm chính |
|---|---|---|
| **Lê Minh Tuấn (PO)** | Quyết định business cuối | Goal + KPI + budget + timeline |
| **Nguyễn Thị Hương (BA Lead Core)** | Author BRD + PRD | Chất lượng requirement |
| **Phạm Quốc Anh (SA Lead Core)** | Author SDD | Feasibility + architecture |
| **Trần Văn Khoa (PM Core)** | Review BRD + quản scope handover | Scope + timeline |
| **Đỗ Thanh Hà (PM Delivery)** | Implement & deploy | On-time, on-budget |
| **Vũ Đình Nam (Tech Lead Delivery)** | Implement | Technical feasibility + code quality |
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
| Implementation | I | C | C | C | **A** R | I |
| UAT decision | **A** | C | I | C | R | I |

---

## 7. Business Process (As-is → To-be)

> Mức **business process**, không phải user flow chi tiết (đó là PRD).

| Aspect | As-is (hiện tại) | To-be (sau khi có sản phẩm) |
|---|---|---|
| **Diagram** | `miro.com/.../renewal-as-is` | `miro.com/.../renewal-to-be` |
| **Mô tả ngắn** | KH gọi tổng đài → nhân viên xác minh → chọn gói thủ công → thu tiền → xác nhận | KH mở app → chọn gia hạn → thanh toán ví/thẻ → nhận xác nhận tức thì |
| **Thời gian end-to-end** | 4–6 phút (chưa tính thời gian chờ máy) | < 2 phút, 24/7 |

---

## 8. Constraints & Compliance

**Business / Organizational constraints:**
- Budget tối đa 2,5 tỷ VND cho phase 1.
- Timeline cứng: go-live trước mùa khuyến mãi hè (trước 2026-06-15).
- Phải tích hợp billing legacy hiện hữu — không được thay thế.
- Tuân thủ chính sách bảo mật dữ liệu khách hàng của tập đoàn.

**Regulatory / Compliance:**

| Regulation | Phạm vi | Yêu cầu | Owner | Status |
|---|---|---|---|---|
| Luật ANM (24/2018/QH14) | Lưu trữ & xử lý dữ liệu trong nước | Data lưu tại DC Việt Nam | Compliance | Compliant |
| NĐ 13/2023/NĐ-CP (PDPA) | Dữ liệu cá nhân thuê bao | Có cơ chế export/xóa, ghi audit log | Legal | Pending |
| PCI-DSS SAQ-A | Thanh toán thẻ | Không lưu PAN, dùng cổng thanh toán đạt chuẩn | Security | Pending |

---

## 9. Business Risks & Mitigations

> Risk ở **mức business** — technical risk thuộc SDD.
> Risk score: H×H = Critical · H×M/M×H = High · M×M/H×L/L×H = Medium · còn lại = Low.

| # | Risk | Likelihood | Impact | Score | Mitigation | Owner |
|---|---|:-:|:-:|:-:|---|---|
| R1 | KH quen gọi tổng đài, chậm adopt kênh số | M | H | High | In-app tour + SMS hướng dẫn + ưu đãi gia hạn online; đo activation tuần 1 | PO |
| R2 | Cổng thanh toán/billing legacy lỗi giờ cao điểm | M | H | High | Load test theo peak; circuit breaker + retry; fallback thông báo lỗi rõ ràng | SA |
| R3 | Quy định PDPA về thanh toán siết giữa chừng | L | H | Medium | Engage Legal từ giai đoạn design, review trước GA | PO |

---

## 10. Timeline & Milestones

> Mức business — milestone lớn, không phải sprint plan.

| Milestone | Mục tiêu business | Owner | Deadline |
|---|---|---|---|
| **M1 — BRD approved** | PO confirm goal + scope, BRD ký xong | BA Lead | 2026-03-02 |
| **M2 — PRD + SDD ready** | Detail spec sẵn sàng review | BA + SA | 2026-03-30 |
| **M3 — Handover** | Biên bản chuyển giao Core → Delivery ký | Core + Delivery + QA | 2026-04-06 |
| **M4 — Dev complete + UAT** | Đạt AC, UAT PASS | Delivery + PO | 2026-05-25 |
| **M5 — Go-live** | Sản phẩm production | Delivery + Core Ops | 2026-06-08 |
| **M6 — Hypercare end** | Stable, chuyển sang Warranty | Delivery + Core Ops | 2026-06-29 |

---

## 11. Glossary & Open Questions

**Glossary (thuật ngữ business):** thuật ngữ technical thuộc Glossary của PRD/SDD.

| Thuật ngữ | Định nghĩa business | Note |
|---|---|---|
| Active subscriber | Thuê bao có ≥ 1 giao dịch trong 30 ngày gần nhất | Loại trừ test account |
| Điểm gia hạn | Thời điểm gói cước hết chu kỳ và cần gia hạn để duy trì dịch vụ | — |
| Churn tại điểm gia hạn | Thuê bao không gia hạn trong vòng 3 ngày sau khi hết hạn | KPI ở Mục 3 |

**Open questions** — phải resolve **trước khi PRD bắt đầu**:

| # | Question | Owner resolve | Deadline | Status |
|---|---|---|---|---|
| Q1 | Có cho gia hạn khi thuê bao đang nợ cước không? | PO + Billing | 2026-03-10 | Resolved — Không, phải thanh toán nợ trước |
| Q2 | Ví nội bộ và thẻ, kênh nào ưu tiên hiển thị mặc định? | PO | 2026-03-12 | Resolved — Ưu tiên ví nội bộ |

---

## 12. Acceptance Checklist & Sign-off

**Checklist** (BA tự kiểm trước Review; PM Reviewer dùng để quyết approve hay trả về):

- [x] Mọi placeholder `[...]` đã điền hoặc đánh dấu `N/A — lý do`
- [x] Mục 1 gọn 1 trang, không kỹ thuật
- [x] Mọi Objective (Mục 3) đều SMART — có Baseline, Target, Timeframe
- [x] Capabilities (Mục 4) có ưu tiên MoSCoW rõ ràng
- [x] In-scope / out-of-scope (Mục 5) không overlap, không gap
- [x] Mọi Assumption có Owner validate + Status
- [x] RACI (Mục 6) không có "A/R" cùng ô
- [x] Risk Critical/High (Mục 9) đều có Mitigation + Owner
- [x] Open questions (Mục 11) đều Resolved trước khi sign-off
- [x] Glossary cover hết thuật ngữ business trong văn bản

**Sign-off** — BRD chỉ có hiệu lực khi đủ **3 chữ ký**:

| Vai trò | Họ tên | Vị trí | Chữ ký | Ngày |
|---|---|---|---|---|
| **Writer (BA Lead)** | Nguyễn Thị Hương | BA Lead Core Telco | _N.T.Hương_ | 2026-03-02 |
| **Reviewer (PM Core)** | Trần Văn Khoa | PM Core Telco | _T.V.Khoa_ | 2026-03-02 |
| **Approver (Client / PO)** | Lê Minh Tuấn | Product Owner | _L.M.Tuấn_ | 2026-03-02 |

> [!NOTE]
> **Đủ 3 chữ ký:** BA + SA bắt đầu viết PRD/SDD dựa trên BRD này.
> **Nếu PRD/SDD phát hiện cần đổi BRD:** raise Change Request → cập nhật Mục 0 → re-sign 3 chữ ký mới.

---

<!-- ==========================================================
     END OF BRD (LEAN) — SAMPLE (filled)
     Template version: 2.1-lean
     Maintained by: ISC AI-SDLC Governance Team
     Aligned with: IIBA BABOK v3, IEEE 29148
========================================================== -->
