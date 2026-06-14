# Workflow 00 — Setup (trigger: "@khởi tạo dự án", đã confirm ý định)

> Claude thực thi **tuần tự từng bước**, mỗi bước hỏi user bằng lựa chọn gợi ý + mô tả rõ,
> user confirm hoặc tự điền rồi mới sang bước kế. Kết quả cuối: `config/factory-config.yaml`
> được điền đầy đủ, KB sẵn sàng nhận yêu cầu.
>
> ⛔ **BẮT BUỘC — MỖI BƯỚC LÀ MỘT LẦN HỎI:** setup đi TỪNG BƯỚC, mỗi bước **DỪNG LẠI hỏi user**
> (AskUserQuestion cho lựa chọn hữu hạn / câu thường cho input tự do) rồi **CHỜ user trả lời**
> mới sang bước kế. **TUYỆT ĐỐI KHÔNG**: tự chọn mặc định thay user, gộp nhiều bước vào một lượt,
> hay chạy thẳng tới cuối. Rule "tự chạy không hỏi" (CLAUDE.md §0.1 Tầng A) **CHỈ** dành cho
> phân tích read-only — **KHÔNG áp cho setup**. Thà hỏi thừa còn hơn tự quyết thay user.
>
> 🟦 **Cách HỎI (rule §1.8) — áp cho mọi bước:** mỗi khi có **lựa chọn hữu hạn (2–4 phương án)**
> → **BẮT BUỘC dùng AskUserQuestion** (thẻ bấm được), KHÔNG bắt user gõ trả lời trong chat.
> **Input TỰ DO** (tên project, URL, đường dẫn, mô tả, mã, tên thư mục tùy biến) → hỏi bằng
> **câu thường** (AskUserQuestion sẽ báo "Failed"). **Ca LAI** (chọn 1 nhánh rồi mới phải nhập
> giá trị tự do — vd "Dùng vault có sẵn", "Đường dẫn khác", "Tạo project Design mới"):
> AskUserQuestion CHỈ để **chọn nhánh**; SAU KHI user chọn mới hỏi giá trị tự do bằng câu thường
> ở **lượt kế** — KHÔNG nhồi giá trị tự do vào AskUserQuestion.
>
> 🔑 **QUAN TRỌNG — MỞ ĐẦU MỌI QUYẾT ĐỊNH BẰNG AskUserQuestion, kể cả khi sẽ dẫn tới nhập tự do.**
> TUYỆT ĐỐI KHÔNG mở một bước bằng câu hỏi nhập-tự-do trống (vd "Bạn muốn thêm/bớt rule nào?",
> "Đặt lịch không?"). Phải khung thành thẻ bấm trước (tối thiểu **Có / Không** — vd
> "[Giữ nguyên preset] / [Thêm/bớt rule]"); user chọn **[Có / nhánh cần nhập]** thì MỚI hỏi giá
> trị tự do ở lượt kế. Mọi sub-step nhỏ trong setup đều phải hiện thẻ chọn, không bắt user gõ tay khi chưa cần.

---

## Bước 1 — Chào + chọn Domain

Hỏi user:

> "Sản phẩm của bạn thuộc lĩnh vực nào? Domain quyết định các rule phân tích
> (thuật ngữ, ràng buộc pháp lý, mức độ thận trọng)."

**→ Dùng AskUserQuestion** (4 lựa chọn, đọc danh sách từ `config/domain-presets/`):

1. **Healthcare / Y tế** — app y tế, thiết bị IoT, dữ liệu sức khỏe (preset `healthcare.md`)
2. **Fintech** — thanh toán, ngân hàng, ví điện tử (preset `fintech.md`)
3. **E-commerce** — bán hàng, giỏ hàng, đơn hàng (preset `ecommerce.md`)
4. **Generic / Khác** — user tự mô tả domain (preset `generic.md`)

Hành động sau khi chọn:
- Copy preset đã chọn → `config/domain-rules.md`.
- Hỏi tiếp — **→ dùng AskUserQuestion** (ca LAI; **KHÔNG mở đầu bằng câu nhập tự do**):
  *"Bạn muốn chỉnh rule domain không?"* → **[Giữ nguyên preset (khuyến nghị)]** / **[Thêm/bớt rule]**.
  - Chọn **Giữ nguyên preset** → bỏ qua, sang Bước 2.
  - Chọn **Thêm/bớt rule** → (lượt kế) hỏi bằng **câu thường** "rule muốn thêm/bớt là gì?" →
    cập nhật `config/domain-rules.md`, đọc lại cho user xác nhận.
  (Đổi sau bất cứ lúc nào bằng cách nhắn "đổi domain".)
- Ghi `domain:` vào `config/factory-config.yaml`.

## Bước 2 — Tên project & ngôn ngữ

- **Tên project** là input TỰ DO → hỏi bằng **câu thường** (TUYỆT ĐỐI KHÔNG dùng AskUserQuestion,
  sẽ báo "Failed"): *"Tên sản phẩm/project của bạn là gì? (tên ngắn gọn — vd: MyApp, ShopX, TaskFlow…)"*
  → chờ user gõ tên.
- **Ngôn ngữ tài liệu**: mặc định **Tiếng Việt**; nếu cần hỏi → **dùng AskUserQuestion**
  (2 lựa chọn: Tiếng Việt / English), KHÔNG hỏi trong chat.
- Ghi vào `factory-config.yaml` (`project_name`, `language`).

## Bước 3 — Nơi lưu tri thức (Obsidian vault)

Hỏi:

> "Tri thức sẽ được lưu thành Obsidian vault (các file .md có backlink).
> Bạn muốn đặt vault ở đâu?"

**→ Dùng AskUserQuestion** (3 nhánh). Nhánh 2 & 3 là **ca LAI**: sau khi user chọn mới hỏi
đường dẫn folder bằng **câu thường** ở lượt kế (KHÔNG nhồi đường dẫn vào AskUserQuestion):

1. **Tạo mới trong project này, tên `<TênProject>_Brain`** (mặc định, khuyến nghị) —
   Claude đổi tên thư mục `Project_Name_Brain/` theo tên project đã chọn ở Bước 2
   (vd project "MyApp" → `MyApp_Brain/`), đồng bộ `vault_path` trong config và
   `OBSIDIAN_VAULT` trong `.env.local`.

   ⚠️ **Thao tác đổi tên/xóa thư mục trong sandbox CÓ THỂ bị chặn quyền** — phải làm
   theo thứ tự fallback, TUYỆT ĐỐI KHÔNG để setup fail giữa chừng:
   - (a) Thử `mv Project_Name_Brain <TênProject>_Brain`.
   - (b) `mv` lỗi → tạo thư mục mới `<TênProject>_Brain` + copy nội dung sang;
     báo user tự xóa thư mục cũ trong Finder (sandbox không có quyền xóa).
   - (c) Cả hai lỗi → GIỮ NGUYÊN tên `Project_Name_Brain`, chỉ ghi đúng `vault_path`
     vào config (tên thư mục chỉ là nhãn — mọi workflow đọc `vault_path`, không đọc
     tên cứng). Nhắc user: muốn đổi tên thì đổi trong Finder rồi nhắn để cập nhật config.
2. **Dùng vault Obsidian có sẵn** — user dán đường dẫn folder vault; Claude kiểm tra
   folder tồn tại, hỏi có muốn tạo sub-folder riêng cho project không.
3. **Đường dẫn khác** — user tự điền.

Hỏi tiếp — **→ dùng AskUserQuestion** (2 lựa chọn: **Dùng tên mặc định** / **Đặt tên khác**).
Chọn "Đặt tên khác" = **ca LAI** → hỏi tên thư mục tùy biến bằng **câu thường** ở lượt kế:

> "Cấu trúc thư mục trong vault dùng tên mặc định (00_Index, 02_Epics, 03_UserStories...)
> hay bạn muốn đặt tên khác?" — đa số chọn mặc định; nếu đổi → ghi vào
> `factory-config.yaml > knowledge_base.vault_structure` VÀ `VAULT_DIRS` trong
> `tools/jira-to-obsidian/.env.local` (JSON) để script dùng đúng tên.

Hành động:
- Ghi `vault_path:` vào `factory-config.yaml`.
- Tạo cấu trúc vault theo `factory-config.yaml > knowledge_base.vault_structure`
  (KHÔNG hardcode tên thư mục):
- Tạo `00_Index/Knowledge-Base.md` (mục lục) nếu chưa có.
- Hướng dẫn user: mở Obsidian → "Open folder as vault" → chọn đường dẫn trên.

## Bước 4 — Quét tài liệu Jira?

Hỏi:

> "Bạn có muốn quét tài liệu từ Jira về làm tri thức ban đầu không?
> (Cần URL Jira và Personal Access Token — KHÔNG dùng password.)"

**→ Dùng AskUserQuestion** (2 lựa chọn: **Có, quét Jira** / **Không, bỏ qua**). Các input của
Jira (URL, token, project keys) là TỰ DO → vẫn hỏi bằng câu thường theo `workflows/01-import-jira.md`.

**Nếu KHÔNG** → sang Bước 5.

**Nếu CÓ** → chạy `workflows/01-import-jira.md` (tự động hoàn toàn theo
`tools/jira-to-obsidian/CLAUDE_CODE_JIRA_TO_OBSIDIAN_SETUP.md`). Tóm tắt các input cần hỏi:

| Input | Mô tả cho user | Bắt buộc |
|---|---|---|
| `JIRA_BASE_URL` | Địa chỉ Jira, ví dụ `https://jira.company.vn` | ✔ |
| `JIRA_PAT` | Personal Access Token (tạo trong Jira: Profile → Personal Access Tokens). Claude tự tạo `.env.local` và mở file cho user dán token vào rồi lưu — KHÔNG dán token vào chat. Có hỏi "đã có token chưa?" trước, chưa có thì hướng dẫn tạo | ✔ |
| `PROJECT_KEYS` | Mã project muốn quét, cách nhau dấu phẩy (vd `PROJ,SHOP`). Để trống = quét tất cả | ✘ |
| `GROUP_BY_PROJECT` | Nhiều project → hỏi user có muốn mỗi project 1 thư mục con trong vault không (khuyến nghị: có). Ghi cả vào `factory-config.yaml > jira.group_by_project` | ✘ |
| `JIRA_AC_FIELD` / `JIRA_BR_FIELD` | ID custom field Acceptance Criteria / Business Rule nếu Jira có | ✘ |

Sau khi import xong → **→ dùng AskUserQuestion** (2 lựa chọn): "Đặt lịch tự động lấy issue
mới từ Jira (vd mỗi sáng)?" → **[Có, đặt lịch]** / **[Không, để sau]**.
→ CÓ thì chạy `workflows/08-schedule-sync.md` ngay; KHÔNG thì bỏ qua (đặt sau bằng
lệnh "đặt lịch quét jira"). Rồi tiếp Bước 5.

## Bước 5 — Nạp tri thức từ file?

Hỏi:

> "Bạn có file tài liệu sẵn muốn nạp không? Hỗ trợ: PDF, DOCX, file .md,
> hoặc zip cả folder Obsidian."

**→ Dùng AskUserQuestion** (2 lựa chọn: **Có, tôi sẽ gửi file** / **Không, bỏ qua**).

- Nếu CÓ → user kéo file vào chat → chạy `workflows/02-import-files.md` cho từng file.
- Nếu KHÔNG → bỏ qua.

## Bước 6 — Kết nối Claude Design

Hỏi:

> "Khi tính năng được chốt, hệ thống sẽ tạo design brief để dựng prototype trong
> Claude Design (artifact/preview). Bạn muốn quản lý prototype theo project nào?"

**→ Dùng AskUserQuestion** (3 nhánh). Nhánh 1 & 2 là **ca LAI**: sau khi chọn mới hỏi tên/mô tả
bằng **câu thường** ở lượt kế (KHÔNG nhồi tên/mô tả vào AskUserQuestion):

1. **Tạo project Design mới** — (lượt kế) hỏi tên → Claude tạo entry trong `projects/_registry.md`
   theo `templates/design-project-template.md`.
2. **Đăng ký project đã có** — (lượt kế) user mô tả project Design hiện hữu (tên, link nếu có,
   các màn hình đã dựng) → Claude ghi vào registry để các lần sau chỉ tương tác đúng
   feature liên quan.
3. **Để sau** — sẽ hỏi lại khi có feature đầu tiên cần design.

## Bước 7 — Tổng kết & kích hoạt

1. Điền nốt `factory-config.yaml`, đặt `setup_completed: true` + ngày giờ.
2. Chạy lập chỉ mục: `python3 tools/kb-indexer/build_index.py --root .` → tự dựng
   `.kb/index.json`, `.kb/relation-graph.json`, `.kb/health-report.md`. Báo nhanh
   sức khỏe KB ban đầu cho user.
3. Ghi dòng đầu vào `.kb/changelog.md`.
4. In tổng kết cho user (ngôn ngữ tự nhiên):
   - Domain + số rule đang áp dụng
   - Vault ở đâu, bao nhiêu note
   - Đã import gì (Jira/file)
   - Project Design nào được đăng ký
5. Kết bằng hướng dẫn dùng:

> "Setup xong! Từ giờ bạn chỉ cần **nhắn vấn đề hoặc yêu cầu** bằng lời thường,
> tôi sẽ tự phân tích dựa trên tri thức hiện có và chỉ hỏi bạn khi cần xác nhận.
> Các lệnh khác: 'đổi domain', 'quét jira', 'quét task <KEY>', 'xuất tài liệu',
> 'thiết kế <tính năng>'. Xem đầy đủ trong README.md."

6. **Đề xuất bước kế (§0.4) — → dùng AskUserQuestion** (1–3 lựa chọn hợp lý theo những gì vừa
   setup) để user chỉ việc bấm, KHÔNG phải tự nhớ lệnh. Ví dụ: `[A] Quét Jira lấy tri thức ·
   [B] Nạp file tài liệu · [C] Nêu một yêu cầu để phân tích · [D] Dừng ở đây`.

---

## Mục B — Đổi domain / rule (trigger: "đổi domain", "sửa rule")

1. Đọc `config/domain-rules.md` hiện tại, tóm tắt cho user.
2. Hỏi: đổi sang preset khác hay sửa từng rule?
3. Mọi thay đổi: hiển thị diff dạng dễ hiểu → user confirm → ghi file.
4. Cập nhật `factory-config.yaml` + changelog.
5. Nhắc user: rule mới chỉ áp dụng cho phân tích từ giờ; tài liệu cũ không tự sửa lại
   (có thể yêu cầu "rà soát lại KB theo rule mới").
