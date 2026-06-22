# Workflow 03 — User nêu vấn đề → phân tích → confirm → ghi tri thức

> Đây là luồng CHÍNH sau setup. User chỉ cần nhắn vấn đề bằng lời thường,
> mọi bước còn lại tự chạy, user chỉ confirm tại các Gate.
>
> **Tầng A (Bước 1–3) TỰ CHẠY — không cần lệnh** (xem CLAUDE.md §0.1): hễ user bàn về
> tính năng / yêu cầu / thay đổi nghiệp vụ là phân tích luôn (đọc KB → xung đột/tác động/
> lỗ hổng → trình bày). Chỉ Bước 4 (ghi) mới cần confirm. Đừng hỏi "có muốn phân tích không".

## Bước 0 — Vai trò + Domain + Template (HỎI khi có YÊU CẦU MỚI về một tính năng)

Mỗi khi user nêu một **YÊU CẦU / TÍNH NĂNG MỚI** (feature mới, hoặc chuyển sang phân tích một tính năng khác —
KHÔNG phải tin nhắn follow-up của tính năng đang phân tích), HỎI nhanh bằng AskUserQuestion (rồi **NHỚ cho các
follow-up CÙNG tính năng đó**; sang tính năng/yêu cầu mới → **hỏi lại**; Tầng A tự chạy theo vai trò đã chọn):

1. **Vai trò?** → **[BA] / [PO] / [SA] / [QA] / [Khác]**. Nạp prompt mẫu theo vai trò từ
   `templates/prompts/role-<x>.md` (đã cài: `~/.claude/kora-framework/templates/prompts/...`) — bản đồ
   `templates/prompts/_index.md`. Vai trò = "lăng kính" phân tích + loại output mong đợi.
2. **Domain?** → nếu `config/factory-config.yaml > domain.preset` đã có thì DÙNG luôn (báo 1 dòng);
   chưa có/không rõ → hỏi chọn preset. Áp THÊM `config/domain-rules.md`. Placeholder `[domain]` trong
   prompt mẫu ← domain này.
3. **Dùng template prompt mẫu + doc template?** → **[Có — role-<x> + doc BRD/PRD] / [Không — tự do]**.
   Nếu **Có**: chèn yêu cầu vào `[<<YÊU CẦU>>]` của prompt mẫu, phân tích đúng theo các mục của prompt;
   **nạp `templates/prompts/ba-prompt-library.md`** (thư viện 20 artifact + định dạng chuẩn) → từ đó mọi
   artifact (US / AC / BR / FR / NFR / validation / test…) ghi ra theo **ĐỊNH DẠNG CHUẨN TỰ ĐỘNG** (mục
   cuối file này), KHÔNG cần user yêu cầu format; đề xuất doc template (`templates/docs/BRD-template.md` /
   `PRD-template.md`) khi user muốn xuất tài liệu (qua `/claude-knowledge-export-docs`). Mẫu output đã điền: `templates/examples/`.

> Cổng NHẸ (1 thẻ/tính năng) — KHÔNG biến mỗi tin nhắn thành 1 lần hỏi; chỉ hỏi khi BẮT ĐẦU một yêu cầu/tính
> năng mới. Sau khi chốt vai trò/domain cho tính năng đó, Tầng A (Bước 1–3) tự chạy như thường (giữ "lăng kính"
> vai trò + prompt mẫu đã chọn) cho các follow-up cùng tính năng.

## Bước 1 — Hiểu yêu cầu, load đúng tri thức (BẮT BUỘC trước khi trả lời)

1. Đọc `.kb/index.json` + `.kb/relation-graph.json`.
2. Tìm các node liên quan đến yêu cầu (feature, BR, AC, màn hình, epic/story Jira).
2b. **Liên kết chéo PROJECT (TỰ ĐỘNG).** Nếu yêu cầu đụng tới thực thể/feature/màn hình/thuật ngữ
   xuất hiện ở **nhiều project** — nhận biết qua relation-graph (issuelink/backlink bắc cầu giữa
   các project) hoặc trùng tên thực thể/thuật ngữ — thì **tự xác định các project liên quan** và
   **kéo cả tri thức của chúng** vào ngữ cảnh (grep across mọi thư mục project trong vault), KHÔNG
   chỉ nhìn 1 project. Mục tiêu: yêu cầu có quan hệ chéo → tự liên kết các project liên quan.
3. **Vault là tri thức — phải dùng kể cả khi `.kb` chưa lập chỉ mục.** Nếu index
   trống/mỏng nhưng vault (`vault_path` trong config) có dữ liệu Jira đã quét:
   - Grep trực tiếp trong vault theo từ khóa của yêu cầu (tên tính năng, màn hình,
     mã hạng mục...) trên cả các thư mục project (`PROJ_MyApp/...`).
   - Đọc các note khớp (epic/story/task liên quan) làm ngữ cảnh trả lời,
     trích nguồn dạng `vault/PROJ_MyApp/03_UserStories/PROJ-123_....md (nguồn raw Jira,
     chưa duyệt)`.
   - TUYỆT ĐỐI KHÔNG trả lời "chưa có tri thức" khi vault có dữ liệu liên quan.
   - Sau khi trả lời, đề nghị: "Chạy lập chỉ mục để các lần sau tra nhanh hơn?"
     → dựng `.kb/index.json` từ vault.
4. **Chỉ load những file thật sự liên quan** — không load cả KB.
5. Đọc `config/domain-rules.md` để áp rule domain hiện hành.
6. Đọc `.kb/lessons.md` — các bài học từ phiên trước để KHÔNG lặp lại lỗi cũ.

## Bước 2 — Phân tích

> 🔢 **THEO ĐÚNG THỨ TỰ PROMPT của `templates/prompts/_index.md` + `ba-prompt-library.md` (§0).** Khi đã chọn
> "Có template" (Bước 0), phân tích bám **chuỗi prompt theo số** (lọc theo vai trò): **01** Phân tích tổng quát →
> **02** Câu hỏi làm rõ → **03** Feature Tree (MoSCoW) → **04** User Story → **05** AC → **06/07** FR/NFR →
> **08/09** Validation/Error → **10/11** Flow → **12/13/14** URD/PRD/SRS → **15/16** Screen/UX → **17/18** API/DB →
> **19/20** Test/Edge. KHÔNG nhảy cóc bỏ bước trước (vd chưa rõ yêu cầu thì dừng ở 02 hỏi `[CẦN XÁC NHẬN]`).

Xác định (chạy theo chuỗi prompt trên):

- Đây là **feature mới** hay **thay đổi feature đã có**? (nếu đã có → chỉ đụng đến
  đúng feature đó và các feature phụ thuộc theo relation graph)
- Ảnh hưởng: màn hình nào, rule nào, AC nào, feature nào phụ thuộc.
- **Project liên quan (liên kết chéo):** yêu cầu này nối những project nào (liệt kê) + phụ thuộc/
  ảnh hưởng CHÉO giữa chúng (vd đổi ở project A kéo theo project B). Nêu rõ để không sửa lệch một phía.
- Mâu thuẫn với tri thức hiện có? (nêu rõ, không tự chọn bên đúng)
- Thiếu thông tin gì → câu hỏi `[CẦN XÁC NHẬN]` (đúng theo prompt **02**, nhóm Business Rules/Data/UI/Technical).

## Bước 3 — Trình bày bằng ngôn ngữ tự nhiên

Trả lời user theo cấu trúc (văn xuôi, không thuật ngữ kỹ thuật thừa):

1. Tôi hiểu yêu cầu của bạn là...
2. Theo tri thức hiện có (trích nguồn file)... liên quan đến các tính năng...
3. Đề xuất của tôi: mục tiêu, luồng chính, rule nghiệp vụ, tiêu chí nghiệm thu.
4. Các điểm cần bạn xác nhận: ...

✋ **GATE 1** — chờ user confirm / chỉnh sửa. Lặp lại bước này đến khi chốt.

## Bước 3.5 — Rà soát chốt phiên (khi user nói "xong / chốt")

Khi user phát tín hiệu kết thúc trao đổi ("xong", "chốt", "ok ghi đi", "vậy là đủ"…),
TRƯỚC khi sang Bước 4, tự tổng rà **toàn bộ** những gì đã bàn trong phiên:

- **Xung đột chéo** giữa các điểm vừa thảo luận (BR mới vs BR vừa nêu, AC chồng nhau,
  luồng mâu thuẫn nhau…).
- **Mâu thuẫn với KB hiện có** + `config/domain-rules.md`.
- **Lỗ hổng còn lại:** feature thiếu Business Rule / Acceptance Criteria; câu
  `[CẦN XÁC NHẬN]` chưa được trả lời.

Trình bày bản tổng kết ngắn (checklist) → nếu còn `[CẦN XÁC NHẬN]` thì hỏi nốt → rồi mới ghi.

## Bước 4 — Ghi tri thức (chỉ sau confirm)

> **Mỗi artifact ghi theo ĐỊNH DẠNG CHUẨN** của `templates/prompts/ba-prompt-library.md`
> (US / AC / BR / FR / NFR / validation / test…) — **TỰ ĐỘNG**, không cần user yêu cầu định dạng.
> Vai trò đã chọn ở Bước 0 lọc *tập artifact* nào được ghi (xem mục "ĐẦU RA CHUẨN TỰ ĐỘNG" cuối file).

Với feature mới `F-xxx-<slug>` (xem `templates/`):

```
docs/03-features/F-xxx-<slug>/
  README.md
  source/
    01-user-document.md        ← tài liệu cho người đọc (template user-document)
    02-claude-context.md       ← context cho Claude Code (template claude-context)
    03-business-rules.md
    04-acceptance-criteria.md
    06-implementation-plan.md  ← tạo ở workflow 07 (nếu có code)
    07-test-plan.md
    changelog.md
  export/                      ← DOCX/PDF, tạo ở workflow 06
```

Với feature đã có: chỉ cập nhật các file bị ảnh hưởng, bump version trong frontmatter.

Sau đó:
- Tạo/cập nhật note vault: `06_Features/F-xxx.md`, `04_BusinessRules/BR-*.md`,
  `05_AcceptanceCriteria/AC-*.md` + backlink về epic/story nguồn.
- **Liên kết chéo project (TỰ ĐỘNG):** nếu tri thức vừa ghi liên quan project khác, thêm backlink
  `[[...]]` **HAI CHIỀU** giữa note/feature của các project liên quan (vd `[[PROJ-A/F-012-...]]` ↔
  `[[PROJ-B/F-034-...]]`) để `relation-graph.json` nối các project với nhau; reindex sẽ ghi nhận cạnh chéo.
- Chạy `python3 tools/kb-indexer/build_index.py --root .` (Windows: `py`) để tự dựng lại
  `.kb/index.json` + `relation-graph.json` + `health-report.md` (khớp docs/ vừa ghi).
- Cập nhật `source-registry.json`, `changelog.md`. Nếu trong phiên vừa có đề xuất bị
  reject/sửa lớn → ghi `.kb/lessons.md` **NGAY** (CLAUDE.md §0.3, format ở workflow 09
  mục E), không chờ tới phiên tiến hóa.

## Bước 5 — Đề xuất bước tiếp

Hỏi user (1 câu, dùng AskUserQuestion):

> "Tri thức đã ghi xong. Bạn muốn: [A] ☁️ Đẩy lên Confluence chung
> [B] 📄 Xuất DOCX/PDF [C] Dừng ở đây?"

[A] → `tools/confluence-sync/sync_confluence.py --push` (hoặc MCP Atlassian khi tương tác);
chỉ hiện khi `confluence.enabled: true`. [B] → `workflows/06-export-docs.md`.

---

## Quy trình BA CHUẨN — để có ĐẦU RA CHUẨN (8 bước)

Khi đi sâu phân tích một feature, bám **quy trình BA 8 bước** (đầu ra mỗi bước là artifact chuẩn). Bước 0–4
ở trên là lõi; dưới là bản đồ đầy đủ + KORA tự thực thi phần nào:

| Bước | Trigger | Mô tả | Đầu ra | KORA thực thi |
|---|---|---|---|---|
| **B0 · Tiếp nhận yêu cầu** | Meeting / Email yêu cầu | Thu thập yêu cầu thô; **ẩn danh dữ liệu nhạy cảm** trước khi đưa vào AI | Yêu cầu thô đã ẩn danh | `/claude-knowledge-connect` + `/claude-knowledge-scan` gom nguồn → vault |
| **B1 · Clarify** | Yêu cầu còn mơ hồ | Sinh câu hỏi làm rõ (group Business Rules/Data/UI/Technical); BA bổ sung theo domain | Danh sách câu hỏi clarification | Bước 0 (vai trò+domain) + `[CẦN XÁC NHẬN]` ở Bước 2/3 |
| **B2 · User Story + AC** | Yêu cầu đã rõ | "As a… I want… So that…" + Given/When/Then | User Story + AC | prompt `role-ba.md` → `docs/03-features/.../04-acceptance-criteria.md` |
| **B3 · Process Flow** | US được duyệt | Mermaid flow; đối chiếu nghiệp vụ thật | Flowchart Mermaid | sinh Mermaid trong feature doc |
| **B4 · FRS/BRD/PRD** | Flow đã duyệt | Bullet → tài liệu chuyên nghiệp; soát theo glossary | BRD/PRD draft | `templates/docs/BRD-template.md` / `PRD-template.md` → `/claude-knowledge-export-docs` |
| **B5 · Quality Gate** | Tài liệu draft xong | Soát 3 mức: chính xác · đầy đủ · peer-review | Tài liệu đã review | **Approval Gate (Bước 4)** + rà soát chốt phiên (Bước 3.5) + `.kb/health-report.md` |
| **B6 · Test Cases** | Tài liệu được duyệt | Happy / edge / negative | Test Cases + UAT script | prompt `role-qa.md` |
| **B7 · UAT** | Test Cases được duyệt | Soạn UAT checklist + kịch bản | UAT checklist + kịch bản | `/claude-knowledge-export-docs` (UAT) |

**TỰ TRƯỞNG THÀNH & HỌC TỪ SAI LẦM (không phải bước 1 lần):** mỗi khi một đề xuất bị user **bác/sửa lớn**,
ghi NGAY 1 bài học vào `.kb/lessons.md` (ngày · bối cảnh · sai gì · rút ra · áp dụng từ nay — §0.3); **đọc lại
`.kb/lessons.md` trước mỗi lần phân tích** để không lặp lỗi. Sau mỗi lần ghi tri thức → **tự reindex**
(`build_index.py`) để index/graph/health luôn khớp. Định kỳ `/claude-knowledge-evolve` (workflow 09) dọn dead-link, hợp
nhất trùng lặp, bù lỗ hổng coverage. ⇒ KB + chất lượng phân tích **lớn dần theo thời gian**.

---

## ĐẦU RA CHUẨN TỰ ĐỘNG (auto-standard output) — TÍCH HỢP thư viện 20 prompt

**Trả lời thẳng câu hỏi "luồng phân tích đã cho output chuẩn tự động chưa?": CÓ.** Luồng phân tích (Bước
1–4) đã **tích hợp** quy trình BA 8 bước **+** thư viện `templates/prompts/ba-prompt-library.md`. Khi chọn
"Có template" (Bước 0), KORA nạp thư viện và **tự động** xuất mỗi artifact theo đúng định dạng chuẩn — user
**KHÔNG** phải yêu cầu "viết theo format X". Bản đồ artifact → định dạng → file ghi:

| Artifact | Định dạng chuẩn (auto) | Prompt | File ghi (`source/`) |
|---|---|---|---|
| **User Story** | `US-[ID]` · `As a… I want… So that…` · Priority · Story Points · OUT OF SCOPE | 04 | `01-user-document.md` |
| **Acceptance Criteria** | `Given-When-Then`, đủ **happy + edge + negative**; negative có **thông báo lỗi** | 05 | `04-acceptance-criteria.md` |
| **Business Rules** | `BR-[ID]` mô tả rule + nguồn/điều kiện | 01/03 | `03-business-rules.md` |
| **Validation + Error msg** | bảng `Tên trường·Kiểu·Bắt buộc·Min·Max·Định dạng·Business Rule` + cross-field | 08/09 | `04-acceptance-criteria.md` (mục Validation) |
| **FR / NFR** | `FR-[ID]` (Actor/Pre/Post) · `NFR-[ID]` (nhóm + số đo + cách kiểm tra) | 06/07 | `02-claude-context.md` |
| **Flow** | Mermaid `flowchart TD` / swimlane (happy + error path) | 10/11 | trong feature doc |
| **Test Cases / Edge** | `TC-[ID]` 3 loại (≥3 happy·2 edge·2 negative) + edge theo 6 nhóm | 19/20 | `07-test-plan.md` |
| **BRD / PRD / SRS** | theo `templates/docs/` (cấu trúc mục cố định) | 12/13/14 | `export/` qua `/claude-knowledge-export-docs` |

**🔢 THỨ TỰ XUẤT (theo `_index` / library §0 — KHÔNG tùy tiện):** sinh & ghi artifact đúng chuỗi prompt
**01→20** (lọc theo vai trò), khớp 8 bước BA: `01 tổng quát → 02 clarify → 03 feature tree → 04 US → 05 AC →
06/07 FR/NFR → 08/09 validation → 10/11 flow → 12/13/14 docs → 15/16 UX → 17/18 API/DB → 19/20 test`. Bước
sau dựa trên bước trước (AC bám US; test bám AC) — thiếu đầu vào thì dừng hỏi `[CẦN XÁC NHẬN]`, không bịa để nhảy bước.

**Vai trò lọc tập artifact** (lăng kính chọn ở Bước 0, theo `_index.md`): **BA** → 01–05,12,15 · **PO** →
01,03,13 + KPI(SMART)/MoSCoW · **SA** → 06,07,14,17,18 · **QA** → 05,08,09,19,20. Chi tiết định dạng từng
artifact: `templates/prompts/ba-prompt-library.md`.

**Nguyên tắc khi auto-xuất:** vẫn bám tri thức KB + trích nguồn (§1), thiếu thông tin → `[CẦN XÁC NHẬN]`
(không bịa để "đủ format"); áp `config/domain-rules.md`; chờ **Approval Gate (Bước 4)** trước khi ghi.
