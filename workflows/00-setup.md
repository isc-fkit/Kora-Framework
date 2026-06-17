# Workflow 00 — Setup (trigger: "@khởi tạo dự án", đã confirm ý định)

> Claude thực thi **tuần tự từng bước**, mỗi bước hỏi user bằng lựa chọn gợi ý + mô tả rõ,
> user confirm hoặc tự điền rồi mới sang bước kế. Kết quả cuối: `config/factory-config.yaml`
> được điền đầy đủ, KB sẵn sàng nhận yêu cầu.
>
> ⛔ **BẮT BUỘC — MỖI BƯỚC LÀ MỘT LẦN HỎI:** setup đi TỪNG BƯỚC, mỗi bước **DỪNG LẠI hỏi user
> bằng AskUserQuestion** (lựa chọn hữu hạn LẪN nhập liệu — input tự do thì dùng **gợi ý + ô
> "Other"** để user gõ, KHÔNG bắt gõ vào chat) rồi **CHỜ user trả lời** mới sang bước kế.
> **TUYỆT ĐỐI KHÔNG**: tự chọn mặc định thay user, gộp nhiều bước vào một lượt, hay chạy thẳng tới
> cuối. Rule "tự chạy không hỏi" (CLAUDE.md §0.1 Tầng A) **CHỈ** dành cho phân tích read-only —
> **KHÔNG áp cho setup**. Thà hỏi thừa còn hơn tự quyết thay user.
> 📋 **Task tracker:** dùng danh sách bước thì **tick từng bước khi xong** và **đóng Bước 6
> (cả danh sách) khi setup hoàn tất** — không để bước nào treo (xem Bước 6 mục 0).
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
- Ghi `domain:` vào `config/factory-config.yaml`.
→ Sang **Bước 2 — Domain rule** (việc chỉnh rule TÁCH thành một bước riêng).

## Bước 2 — Domain rule (bước RIÊNG)

Sau khi Bước 1 đã copy preset → `config/domain-rules.md`:

- **→ dùng AskUserQuestion** (ca LAI; **KHÔNG mở đầu bằng câu nhập tự do**):
  *"Bạn muốn chỉnh rule domain không?"* → **[Giữ nguyên preset (khuyến nghị)]** / **[Thêm/bớt rule]**.
  - Chọn **Giữ nguyên preset** → sang Bước 3.
  - Chọn **Thêm/bớt rule** → (lượt kế) hỏi bằng **câu thường** "rule muốn thêm/bớt là gì?" →
    cập nhật `config/domain-rules.md`, đọc lại cho user xác nhận.
  (Đổi sau bất cứ lúc nào bằng cách nhắn "đổi domain" / "sửa rule".)

## Bước 3 — Tên project & ngôn ngữ

- **Tên project** → **dùng AskUserQuestion** (KHÔNG bắt gõ vào chat): câu hỏi *"Tên sản phẩm/project
  của bạn là gì?"* + đưa **vài GỢI Ý tên ví dụ theo domain** làm option (vd Healthcare:
  `HealthTrack` / `MedCare` / `CarePlus`; domain khác tự chỉnh cho hợp) — user bấm ô **"Other"**
  gõ **tên thật** vào ô trống. (Đa số sẽ dùng "Other"; gợi ý chỉ để tham khảo.)
  *Fallback:* nếu môi trường không nhập được ô "Other" → mới hỏi câu thường.
- **Ngôn ngữ tài liệu**: mặc định **Tiếng Việt**; nếu cần hỏi → **dùng AskUserQuestion**
  (2 lựa chọn: Tiếng Việt / English), KHÔNG hỏi trong chat.
- Ghi vào `factory-config.yaml` (`project_name`, `language`).

## Bước 4 — Nơi lưu tri thức (vault)

> 💡 **Obsidian là TÙY CHỌN — KHÔNG bắt buộc.** Vault chỉ là một **thư mục các file `.md`**.
> Claude và MỌI tính năng (quét Jira, phân tích, xuất tài liệu, cập nhật…) chạy bình thường
> mà **không cần Obsidian**. Obsidian chỉ giúp **xem backlink trực quan**; không có nó thì vẫn
> mở folder bằng VS Code / editor markdown bất kỳ (backlink `[[...]]` hiện dạng text, không click được).

**Trước tiên → dùng AskUserQuestion:** *"Bạn đã cài Obsidian chưa?"* → **[Đã cài]** / **[Chưa cài /
không dùng Obsidian]**.
- **Chưa cài + muốn dùng** → gợi ý tải tại **https://obsidian.md** (có cho macOS / Windows / Linux),
  cài xong → "Open folder as vault". (Vẫn tiếp tục setup ngay, không bắt chờ cài.)
- **Chưa cài / không dùng** → **vẫn tiếp tục bình thường**; cuối Bước 3 chỉ cần mở folder vault bằng
  editor markdown bất kỳ. KHÔNG để việc thiếu Obsidian chặn setup.

Hỏi nơi lưu:

> "Tri thức sẽ được lưu thành vault (thư mục các file .md có backlink).
> Bạn muốn đặt vault ở đâu?"

**→ Dùng AskUserQuestion** (3 nhánh). Nhánh 2 & 3 là **ca LAI**: sau khi user chọn, hỏi đường dẫn
folder bằng **AskUserQuestion khác** — gợi ý vài đường dẫn thường gặp làm option (vd thư mục
project hiện tại, `~/Documents/<TênProject>_Brain`, `~/Obsidian/<TênProject>`) + ô **"Other"** để
user dán **đường dẫn thật**. KHÔNG bắt gõ vào chat (fallback câu thường nếu ô Other lỗi):

1. **Tạo mới trong project này, tên `<TênProject>_Brain`** (mặc định, khuyến nghị) —
   Claude đổi tên thư mục `Project_Name_Brain/` theo tên project đã chọn ở Bước 2
   (vd project "MyApp" → `MyApp_Brain/`), đồng bộ `vault_path` trong config và
   `OBSIDIAN_VAULT` trong `.env.local`.

   ⚠️ **Thao tác đổi tên/xóa thư mục trong sandbox CÓ THỂ bị chặn quyền** — phải làm
   theo thứ tự fallback, TUYỆT ĐỐI KHÔNG để setup fail giữa chừng:
   - (a) Thử đổi tên **theo OS:** macOS/Linux `mv Project_Name_Brain <TênProject>_Brain`;
     **Windows (PowerShell)** `Rename-Item Project_Name_Brain <TênProject>_Brain` (hoặc `Move-Item`).
   - (b) Lỗi → tạo thư mục mới `<TênProject>_Brain` + copy nội dung sang;
     báo user tự xóa thư mục cũ (Finder trên macOS / Explorer trên Windows — sandbox không có quyền xóa).
   - (c) Cả hai lỗi → GIỮ NGUYÊN tên `Project_Name_Brain`, chỉ ghi đúng `vault_path`
     vào config (tên thư mục chỉ là nhãn — mọi workflow đọc `vault_path`, không đọc
     tên cứng). Nhắc user: muốn đổi tên thì đổi trong Finder (macOS) / Explorer (Windows) rồi nhắn để cập nhật config.
2. **Dùng vault có sẵn** — user dán đường dẫn folder vault; Claude kiểm tra
   folder tồn tại, hỏi có muốn tạo sub-folder riêng cho project không.
3. **Đường dẫn khác** — chọn xong, hỏi đường dẫn bằng AskUserQuestion + ô **"Other"** (như trên).

Hỏi tiếp — **→ dùng AskUserQuestion** (2 lựa chọn: **Dùng tên mặc định** / **Đặt tên khác**).
Chọn "Đặt tên khác" = **ca LAI** → hỏi tên thư mục tùy biến bằng **AskUserQuestion**: gợi ý bộ
tên mặc định (`00_Index`, `02_Epics`…) làm tham khảo + ô **"Other"** để nhập tên tùy biến (KHÔNG
bắt gõ vào chat; fallback câu thường nếu lỗi):

> "Cấu trúc thư mục trong vault dùng tên mặc định (00_Index, 02_Epics, 03_UserStories...)
> hay bạn muốn đặt tên khác?" — đa số chọn mặc định; nếu đổi → ghi vào
> `factory-config.yaml > knowledge_base.vault_structure` VÀ `VAULT_DIRS` trong
> `tools/jira-to-obsidian/.env.local` (JSON) để script dùng đúng tên.

Hành động:
- Ghi `vault_path:` vào `factory-config.yaml`.
- Tạo cấu trúc vault theo `factory-config.yaml > knowledge_base.vault_structure`
  (KHÔNG hardcode tên thư mục):
- Tạo `00_Index/Knowledge-Base.md` (mục lục) nếu chưa có.
- Hướng dẫn user mở vault **theo lựa chọn ở đầu Bước 3**:
  - **Dùng Obsidian** → mở Obsidian → "Open folder as vault" → chọn đường dẫn trên.
  - **Không dùng Obsidian** → mở folder `<vault_path>` bằng VS Code / editor markdown bất kỳ
    (Finder/Explorer cũng xem được các file `.md`). Mọi tính năng vẫn chạy bình thường.

> ℹ️ **Init GỌN NHẸ — KHÔNG nạp nguồn / token / lịch ở đây.** Việc nạp tri thức và kết nối
> nguồn đã chuyển sang các skill riêng, chạy SAU init khi cần (không ép lúc khởi tạo):
> - `/kora-scan`, `/kora-scan-jira-task` — nạp Jira (chọn kết nối **MCP** hoặc **API** ngay trong skill đó).
> - `/kora-import-files` — nạp PDF / DOCX / ảnh.
> - `/kora-schedule` — đặt lịch + cấu hình kết nối nguồn (token API ghi vào `~/.zshrc` / `~/.bashrc`).
> - `/kora-daily-report` — báo cáo (chọn project, lọc thành viên, kéo dữ liệu theo khoảng thời gian).

## Bước 5 — Kết nối Claude Design

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

## Bước 6 — Tổng kết & kích hoạt

0. ✅ **ĐÓNG TASK TRACKER:** ngay khi làm xong Bước 6 và đã đặt `setup_completed: true`, **đánh
   dấu Bước 6 + TOÀN BỘ danh sách bước = HOÀN THÀNH** trong trình theo dõi tiến độ (TaskUpdate →
   `completed`). TUYỆT ĐỐI không để Bước 6 treo "chưa hoàn thành", **kể cả khi user yêu cầu chạy
   thẳng một mạch tới cuối** — chạy tới đâu tick tới đó, xong Bước 6 thì đóng cả danh sách.
1. Điền nốt `factory-config.yaml`, đặt `setup_completed: true` + ngày giờ.
2. Chạy lập chỉ mục: `python3 tools/kb-indexer/build_index.py --root .` (Windows: `py`) → tự dựng
   `.kb/index.json`, `.kb/relation-graph.json`, `.kb/health-report.md`. Báo nhanh
   sức khỏe KB ban đầu cho user.
3. Ghi dòng đầu vào `.kb/changelog.md`.
4. In tổng kết cho user (ngôn ngữ tự nhiên):
   - Domain + số rule đang áp dụng
   - Vault ở đâu, bao nhiêu note
   - Project Design nào được đăng ký
   - Nhắc: nạp tri thức bằng skill SAU init (`/kora-scan`, `/kora-import-files`).
5. Kết bằng hướng dẫn dùng:

> "Setup xong! Từ giờ bạn chỉ cần **nhắn vấn đề hoặc yêu cầu** bằng lời thường,
> tôi sẽ tự phân tích dựa trên tri thức hiện có và chỉ hỏi bạn khi cần xác nhận.
> Lệnh tắt: `/kora-scan`, `/kora-import-files`, `/kora-daily-report`, `/kora-schedule`,
> `/kora-design`, `/kora-export-docs`, `/kora-evolve`. Gõ `/` để xem đủ 12 lệnh."

6. **Đề xuất bước kế (§0.4) — → dùng AskUserQuestion** (1–3 lựa chọn hợp lý theo những gì vừa
   setup) để user chỉ việc bấm, KHÔNG phải tự nhớ lệnh. Ví dụ: `[A] /kora-scan nạp tri thức ·
   [B] /kora-import-files nạp tài liệu · [C] Nêu một yêu cầu để phân tích · [D] Dừng ở đây`.

---

## Mục B — Đổi domain / rule (trigger: "đổi domain", "sửa rule")

1. Đọc `config/domain-rules.md` hiện tại, tóm tắt cho user.
2. Hỏi: đổi sang preset khác hay sửa từng rule?
3. Mọi thay đổi: hiển thị diff dạng dễ hiểu → user confirm → ghi file.
4. Cập nhật `factory-config.yaml` + changelog.
5. Nhắc user: rule mới chỉ áp dụng cho phân tích từ giờ; tài liệu cũ không tự sửa lại
   (có thể yêu cầu "rà soát lại KB theo rule mới").
