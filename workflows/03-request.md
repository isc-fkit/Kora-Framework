# Workflow 03 — User nêu vấn đề → phân tích → confirm → ghi tri thức

> Đây là luồng CHÍNH sau setup. User chỉ cần nhắn vấn đề bằng lời thường,
> mọi bước còn lại tự chạy, user chỉ confirm tại các Gate.
>
> **Tầng A (Bước 1–3) TỰ CHẠY — không cần lệnh** (xem CLAUDE.md §0.1): hễ user bàn về
> tính năng / yêu cầu / thay đổi nghiệp vụ là phân tích luôn (đọc KB → xung đột/tác động/
> lỗ hổng → trình bày). Chỉ Bước 4 (ghi) mới cần confirm. Đừng hỏi "có muốn phân tích không".

## Bước 1 — Hiểu yêu cầu, load đúng tri thức (BẮT BUỘC trước khi trả lời)

1. Đọc `.kb/index.json` + `.kb/relation-graph.json`.
2. Tìm các node liên quan đến yêu cầu (feature, BR, AC, màn hình, epic/story Jira).
3. **Vault là tri thức — phải dùng kể cả khi `.kb` chưa lập chỉ mục.** Nếu index
   trống/mỏng nhưng vault (`vault_path` trong config) có dữ liệu Jira đã quét:
   - Grep trực tiếp trong vault theo từ khóa của yêu cầu (tên tính năng, màn hình,
     mã issue...) trên cả các thư mục project (`PROJ_MyApp/...`).
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

Xác định:

- Đây là **feature mới** hay **thay đổi feature đã có**? (nếu đã có → chỉ đụng đến
  đúng feature đó và các feature phụ thuộc theo relation graph)
- Ảnh hưởng: màn hình nào, rule nào, AC nào, feature nào phụ thuộc.
- Mâu thuẫn với tri thức hiện có? (nêu rõ, không tự chọn bên đúng)
- Thiếu thông tin gì → câu hỏi `[CẦN XÁC NHẬN]`.

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

Với feature mới `F-xxx-<slug>` (xem `templates/`):

```
docs/03-features/F-xxx-<slug>/
  README.md
  source/
    01-user-document.md        ← tài liệu cho người đọc (template user-document)
    02-claude-context.md       ← context cho Claude Design/Code (template claude-context)
    03-business-rules.md
    04-acceptance-criteria.md
    05-design-brief.md         ← tạo ở workflow 04
    06-implementation-plan.md  ← tạo ở workflow 07 (nếu có code)
    07-test-plan.md
    changelog.md
  export/                      ← DOCX/PDF, tạo ở workflow 06
```

Với feature đã có: chỉ cập nhật các file bị ảnh hưởng, bump version trong frontmatter.

Sau đó:
- Tạo/cập nhật note vault: `06_Features/F-xxx.md`, `04_BusinessRules/BR-*.md`,
  `05_AcceptanceCriteria/AC-*.md` + backlink về epic/story nguồn.
- Chạy `python3 tools/kb-indexer/build_index.py --root .` để tự dựng lại
  `.kb/index.json` + `relation-graph.json` + `health-report.md` (khớp docs/ vừa ghi).
- Cập nhật `source-registry.json`, `changelog.md`. Nếu trong phiên vừa có đề xuất bị
  reject/sửa lớn → ghi `.kb/lessons.md` **NGAY** (CLAUDE.md §0.3, format ở workflow 09
  mục E), không chờ tới phiên tiến hóa.

## Bước 5 — Đề xuất bước tiếp

Hỏi user (1 câu):

> "Tri thức đã ghi xong. Bạn muốn: [A] 🎨 Dựng prototype với Claude Design
> [B] 📄 Xuất DOCX/PDF [C] Dừng ở đây?"

[A] → `workflows/04-claude-design.md`. [B] → `workflows/06-export-docs.md`.
