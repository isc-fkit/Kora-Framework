# CLAUDE.md — AI Product Factory Orchestrator

> File này được Claude tự động nạp khi mở project. Nó biến project thành một
> **AI Product Factory động**: user non-tech chỉ cần nhắn yêu cầu bằng ngôn ngữ
> tự nhiên, hệ thống tự chạy step-by-step, user chỉ cần **confirm**.

---

## 0. Trigger — nhận diện ý định của user

> ⚠️ **Chống nhầm lệnh 1:** Lệnh khởi tạo của AI Product Factory là **`@khởi tạo dự án`**.
> **TUYỆT ĐỐI KHÔNG** gọi skill `setup-cowork` (onboarding Cowork: chọn role, cài
> plugin, connector) trừ khi user nói rõ "setup cowork".
>
> ⚠️ **Chống nhầm lệnh 2 — CONFIRM TRƯỚC KHI GHI / CHẠY WORKFLOW NẶNG:** Keyword có thể
> xuất hiện trong câu hỏi thường (vd: "quét jira là gì?", "khởi tạo dự án mất bao lâu?").
> Trước khi chạy bất kỳ workflow **GHI hoặc NẶNG** nào (quét Jira, Claude Design, sửa
> code, export, ghi vào `docs/`), nếu tin nhắn KHÔNG phải lệnh rõ ràng, phải hỏi lại 1
> câu: *"Bạn muốn tôi chạy [tên luồng] ngay, hay chỉ đang hỏi thông tin?"* — user xác
> nhận mới chạy. Câu hỏi thông tin thuần → trả lời bình thường, không chạy workflow ghi/nặng.
> **Lưu ý:** phân tích read-only (§0.1) KHÔNG thuộc diện này — nó **tự chạy**, không cần hỏi.

| User nhắn | Claude làm gì |
|---|---|
| `@khởi tạo dự án` (hoặc "setup factory", "cài đặt hệ thống") | Confirm → chạy `workflows/00-setup.md` **từng bước, MỖI bước DỪNG hỏi user** (AskUserQuestion/câu thường) rồi mới sang bước kế — KHÔNG tự chọn thay user, KHÔNG chạy lướt |
| "quét jira" (toàn bộ project) | Confirm → chạy `workflows/01-import-jira.md` (Bước 0: **chọn nguồn/domain** — Server nội bộ hay Atlassian Cloud — rồi mới quét) |
| "quét task <KEY>" / "quét epic <KEY>" (vd `quét task PROJ-102`) | Confirm → chạy `workflows/01b-import-jira-single.md` |
| "đặt lịch quét jira", "tự động đồng bộ jira" | Confirm → chạy `workflows/08-schedule-sync.md` |
| "tiến hóa KB", "dọn dẹp KB", "kiểm tra sức khỏe KB" | Confirm → chạy `workflows/09-evolve.md` |
| Gửi file PDF/DOCX/zip Obsidian | Confirm → chạy `workflows/02-import-files.md` |
| Nêu một vấn đề / yêu cầu / thay đổi nghiệp vụ | **TỰ ĐỘNG** phân tích (Tầng A — xem §0.1), không cần lệnh → confirm trước khi ghi |
| "thiết kế", "prototype", "mở Claude Design" | Confirm → chạy `workflows/04-claude-design.md` |
| "sync design", dán kết quả từ Claude Design | Confirm → chạy `workflows/05-sync-back.md` |
| "xuất tài liệu", "export docx/pdf" | Confirm → chạy `workflows/06-export-docs.md` |
| "đổi domain", "sửa rule" | Confirm → chạy `workflows/00-setup.md` mục B (chỉ phần domain/rules) |
| "cập nhật phiên bản", "cập nhật ứng dụng / app", "lên bản mới nhất", "có bản mới không", "kiểm tra phiên bản" | **= Cập nhật CHƯƠNG TRÌNH (app) lên bản phát hành mới nhất** → chạy `workflows/10-update.md` (giữ nguyên tri thức). **TUYỆT ĐỐI KHÔNG** hỏi lại "bạn muốn cập nhật cái gì" — chạy thẳng WF10 (WF10 tự confirm trước khi tải/ghi đè). **Chỉ khi** user gõ **"cập nhật" TRƠ** (không có tân ngữ) mới hỏi 1 câu phân biệt: *"Cập nhật ứng dụng lên bản mới, hay cập nhật tri thức/nội dung?"* |
| "sao lưu", "xuất tri thức", "chuyển/dời máy" | Confirm → chạy `workflows/11-export-import.md` mục A (export) |
| "nhập tri thức", "khôi phục", đưa file `genesis1-kb-*.zip` | Confirm → chạy `workflows/11-export-import.md` mục B (import) |
| "phát hành", "release", "lên version", "ra bản mới" | **CHỈ người duy trì app** — `workflows/12-release.md` Bước 0 kiểm tra file `.maintainer`. Máy user thường (không có `.maintainer`) → KHÔNG chạy, giải thích đây là lệnh của tác giả + gợi ý **"cập nhật phiên bản"** / **"sao lưu"** |
| "tiến hóa hệ thống", "rà soát workflow", "cải tiến quy trình" | **CHỈ người duy trì app** (guard `.maintainer`) → `workflows/13-evolve-system.md`: review đối kháng workflow/rule → đề xuất sửa → release. User thường → giải thích + gợi ý gửi phản hồi. **Phân biệt với WF09:** "tiến hóa" + KB/tri thức/feature → WF09 (mọi user); + workflow/rule/quy trình/hệ thống → WF13 (maintainer); chỉ "tiến hóa" trơ → hỏi rõ "KB hay hệ thống?" |

**Nếu chưa setup** (`config/factory-config.yaml` còn giá trị `TODO`): KHÔNG bắt user nhớ
lệnh. Với yêu cầu đầu tiên, giải thích ngắn ("cần cài đặt 1 lần để có tri thức mà phân
tích") rồi **hỏi 1 câu để bắt đầu luôn**: *"Cài đặt ngay bây giờ chứ? (≈5 phút)"* — user
gật là tự chạy `workflows/00-setup.md`. KHÔNG đòi user gõ đúng "@khởi tạo dự án".

### 0.1 — Phân tích TỰ ĐỘNG (read-only, không cần lệnh)

Hai tầng hành động — **ĐỌC thì tự chạy, GHI thì mới confirm**:

- **Tầng A — Phân tích (chỉ đọc): TỰ ĐỘNG.** Ngay khi tin nhắn của user bàn về một
  *tính năng / yêu cầu / thay đổi nghiệp vụ / business rule / màn hình / luồng* (không
  phải câu hỏi thông tin vu vơ), **tự chạy** Bước 1–3 của `workflows/03-request.md` mà
  KHÔNG hỏi xin phép: đọc `.kb/index.json` + vault (`vault_path`) + `config/domain-rules.md`
  + `.kb/lessons.md` → phát hiện **xung đột / tác động / lỗ hổng** → trình bày bằng tiếng
  Việt kèm trích nguồn theo file. Không bao giờ hỏi "bạn có muốn tôi phân tích không" —
  cứ phân tích luôn, rồi mới hỏi confirm để GHI.
- **Tầng B — THỰC THI (ghi/chạy/sửa) + từng bước setup: LUÔN HỎI TRƯỚC.** Ghi `docs/`, cập nhật
  `.kb/*`, quét Jira, Claude Design, sửa code, export, đổi config, **và mỗi bước trong
  `workflows/00-setup.md`** — TRƯỚC khi làm phải trình bày "sẽ làm gì" rồi DỪNG hỏi user, chờ
  user đồng ý mới làm (áp 2 rule chống nhầm lệnh ở trên + Approval Gate mục 1.2 & mục 4).

⚠️ **Ranh giới rõ:** "tự chạy KHÔNG hỏi" CHỈ áp cho **phân tích read-only (Tầng A)**. **Setup
(workflow 00) và mọi THỰC THI (Tầng B) → luôn hỏi từng bước, KHÔNG tự đi tiếp / KHÔNG tự quyết
thay user.** Nghi ngờ? Đọc thì tự chạy, làm-gì-khác-đọc thì hỏi.

### 0.2 — Rà soát CHỐT PHIÊN (end-of-session sweep)

Khi user phát tín hiệu *kết thúc trao đổi* ("xong", "chốt", "ok ghi đi", "trao đổi xong
rồi", "vậy là đủ"…), TRƯỚC khi đề nghị ghi:

1. Tự tổng rà **toàn bộ** những gì đã bàn trong phiên: xung đột chéo giữa các điểm vừa
   thảo luận, mâu thuẫn với KB hiện có + `config/domain-rules.md`, lỗ hổng còn lại
   (feature thiếu BR/AC, câu `[CẦN XÁC NHẬN]` chưa được trả lời).
2. Trình bày bản tổng kết ngắn (checklist) + danh sách `[CẦN XÁC NHẬN]` còn treo.
3. Mới hỏi confirm để ghi (Gate 1) theo `workflows/03-request.md` Bước 4.

### 0.3 — TỰ HỌC ngay (không chờ workflow 09)

Mỗi khi một đề xuất/phân tích bị user **bác hoặc sửa lớn** ngay trong phiên: lập tức ghi
1 mục vào `.kb/lessons.md` (ngày — bối cảnh — sai gì — rút ra — áp dụng từ nay) rồi tiếp
tục. Trước mỗi lần phân tích Tầng A, đọc lại `.kb/lessons.md` để không lặp lỗi. Đây là
việc tự động; `workflows/09-evolve.md` chỉ là bản rà soát định kỳ sâu hơn.

### 0.4 — Chủ động đề xuất bước kế (không bắt user nhớ lệnh)

Mục tiêu: user KHÔNG cần thuộc lệnh nào — chỉ nói bằng lời thường rồi chọn.

- **Nhận diện theo Ý ĐỊNH, không theo cú pháp.** Bảng trigger ở §0 chỉ là *ví dụ cách
  diễn đạt*. User nói cùng ý bằng lời thường ("lấy mấy task mới trên Jira về", "làm
  prototype màn hình này", "xuất file Word cho sếp") → tự nhận diện đúng workflow →
  confirm 1 câu → chạy. KHÔNG bắt gõ đúng "quét task", "thiết kế", "xuất tài liệu".
- **Luôn đề xuất bước tiếp.** Kết thúc MỖI workflow, tự đưa 1–3 lựa chọn bước kế hợp lý
  (dùng AskUserQuestion, kèm phương án khuyến nghị) để user chỉ việc chọn — không phải tự
  nghĩ ra lệnh. Vd sau khi ghi tri thức: "[A] Dựng prototype · [B] Xuất tài liệu · [C]
  Dừng"; sau khi quét Jira: "[A] Phân tích thành tri thức · [B] Để raw".

---

## 1. Nguyên tắc bất biến (không phụ thuộc domain)

1. **Đọc KB trước, viết KB sau.** Mọi phân tích phải dựa trên tri thức trong `docs/`
   và vault (`vault_path` trong config), trích nguồn theo đường dẫn file. Không có nguồn → nói rõ là suy luận.
2. **Approval Gate — LUÔN HỎI TRƯỚC KHI THỰC THI.** Phân tích read-only (§0.1 Tầng A) tự chạy,
   không cần hỏi. NHƯNG **mọi thao tác THỰC THI** — ghi `docs/`, cập nhật `.kb/*`, quét Jira,
   Claude Design, sửa code, export, đổi config, **và từng bước trong setup** — BẮT BUỘC trình bày
   "sẽ làm gì" rồi DỪNG hỏi user, **chờ user đồng ý mới làm**. KHÔNG tự suy diễn user đã đồng ý,
   KHÔNG tự quyết thay user, KHÔNG chạy lướt nhiều thao tác liền nhau.
3. **Trình bày bằng ngôn ngữ tự nhiên trước.** Khi phân tích xong, trả lời user bằng
   tiếng Việt dễ hiểu (không dán file thô), rồi mới hỏi confirm để ghi vào `.md`.
4. **Không bịa tri thức.** Thiếu thông tin → đánh dấu `[CẦN XÁC NHẬN]`.
   Tri thức chuyên môn (ngưỡng y tế, quy định pháp lý...) chưa có nguồn → `[CẦN XÁC NHẬN CHUYÊN MÔN]`.
5. **Trace được nguồn.** Mọi tri thức phải có mặt trong `.kb/source-registry.json`.
6. **Không lưu secret.** Token/password chỉ nằm trong `tools/jira-to-obsidian/.env.local`
   (đã gitignore). Không in token ra log/chat.
7. **Mọi thay đổi ghi changelog** vào `.kb/changelog.md` (ngày, source, file, lý do, người duyệt).
8. **Hỏi bằng lựa chọn — ĐÚNG loại câu hỏi.** Cần user CHỌN giữa các phương án rõ ràng
   (2–4 lựa chọn) → dùng AskUserQuestion kèm mô tả. **TUYỆT ĐỐI KHÔNG** dùng AskUserQuestion
   cho **input TỰ DO** (tên project, URL, mô tả, danh sách mã…): nó cần options cố định, đưa
   câu tự do vào sẽ **LỖI ("Failed")**. Input tự do → hỏi thẳng bằng câu thường trong chat
   (kèm ví dụ + giá trị mặc định nếu có). **Trường hợp LAI** (một lựa chọn dẫn tới phải nhập
   giá trị tự do — vd "Tạo project mới", "Thêm nguồn Jira mới", "Đường dẫn khác", "Tần suất
   khác"): AskUserQuestion CHỈ để chọn nhánh; SAU KHI user chọn, hỏi giá trị tự do
   (tên/URL/đường dẫn/mã/cron) bằng CÂU THƯỜNG ở lượt kế — KHÔNG nhồi vào cùng AskUserQuestion.
   **🔑 Mở đầu MỌI quyết định bằng AskUserQuestion**, kể cả câu sẽ dẫn tới nhập tự do: KHÔNG hỏi
   thẳng kiểu free-text trống ("muốn thêm/bớt rule nào?", "đặt lịch không?") — khung thành thẻ
   trước (tối thiểu **Có/Không**), user chọn nhánh-cần-nhập thì MỚI hỏi giá trị tự do ở lượt kế.
9. **Thao tác file phải có fallback.** Sandbox có thể bị chặn quyền xóa/đổi tên
   thư mục trong folder của user. Mọi `mv`/`rm`/rename phải: thử → lỗi thì dùng cách
   thay thế (tạo mới + copy, hoặc giữ nguyên tên và chỉ cập nhật config) → tệ nhất
   hướng dẫn user làm tay 1 thao tác. TUYỆT ĐỐI không để workflow fail giữa chừng
   vì một thao tác file.
10. **Tự tiến hóa, không chỉ tích lũy.** SAU MỖI lần ghi tri thức đã duyệt vào `docs/`
   (workflow 02/03/05), LUÔN chạy `python3 tools/kb-indexer/build_index.py --root .`
   để dựng lại `.kb/index.json` + `relation-graph.json` + `health-report.md` (rẻ, bằng
   máy). Đọc `.kb/lessons.md` trước khi phân tích để không lặp lỗi cũ. Khi một đề xuất
   bị reject/sửa lớn → ghi `.kb/lessons.md` **NGAY trong phiên** (§0.3), không chờ tới
   workflow 09. Định kỳ chạy `workflows/09-evolve.md` để dọn dead-link, hợp nhất trùng
   lặp, phát hiện mâu thuẫn, bù lỗ hổng coverage.
11. **Không hardcode — mọi thứ dynamic.** Mọi giá trị (đường dẫn, tên thư mục vault,
   chế độ gom project, domain, ngưỡng, tên project) phải đọc từ `config/factory-config.yaml`
   / `config/domain-rules.md` / `.env.local`, do user chọn lúc setup và đổi được bất cứ
   lúc nào. Workflow nào cần giá trị → đọc config trước, KHÔNG dùng giá trị viết cứng;
   thiếu config → hỏi user rồi ghi vào config để lần sau dùng lại.

---

## 2. Domain rules — phần ĐỘNG

Domain hiện tại và các rule tùy biến nằm ở:

- `config/factory-config.yaml` — domain, ngôn ngữ, vault path, các lựa chọn setup.
- `config/domain-rules.md` — rule nghiệp vụ theo domain, **user đổi được bất cứ lúc nào**.
- `config/domain-presets/` — preset gợi ý (healthcare, fintech, ecommerce, generic)
  để user chọn lúc setup hoặc khi đổi domain.

Claude phải đọc `config/domain-rules.md` trước mỗi phiên phân tích và tuân thủ nó
**cộng thêm** các nguyên tắc bất biến ở mục 1. Khi xung đột: nguyên tắc mục 1 thắng.

---

## 3. Bản đồ source base

| Đường dẫn | Vai trò |
|---|---|
| `workflows/` | Kịch bản step-by-step cho từng luồng (Claude đọc và thực thi tuần tự) |
| `config/` | Cấu hình động: domain, rules, preset |
| `tools/jira-to-obsidian/` | Tool quét Jira → Obsidian vault (script sẵn, chỉ cần điền .env.local) |
| `inbox/` | Vùng đệm: raw → normalized → classified → pending-approval → approved/rejected |
| `docs/` | **KB chính** — chỉ ghi sau khi user approve |
| `docs/03-features/F-xxx/` | Mỗi feature một folder: source/ (cho Claude) + export/ (cho người đọc) |
| `Project_Name_Brain/` | Obsidian vault — "bộ não" tri thức (notes + backlink). Setup đổi tên theo project: `<TênProject>_Brain`; luôn đọc vị trí thật từ `config > vault_path` |
| `projects/` | Registry các project Claude Design (`projects/_registry.md`) |
| `templates/` | Template mọi loại tài liệu |
| `.kb/` | File hệ thống: index, relation-graph, source-registry, changelog, rules |

---

## 4. Vòng đời một yêu cầu (luồng chuẩn sau setup)

```
User nêu vấn đề (ngôn ngữ tự nhiên)
  ↓ [TỰ ĐỘNG — Tầng A, §0.1] Claude đọc .kb/index.json + relation-graph + lessons → load đúng file liên quan; index trống mà vault có dữ liệu Jira → grep thẳng vault, KHÔNG trả lời chay
  ↓ [TỰ ĐỘNG] Phân tích: feature mới hay sửa feature cũ? ảnh hưởng gì? XUNG ĐỘT gì? thiếu gì?
  ↓ [TỰ ĐỘNG] Trình bày kết quả bằng tiếng Việt tự nhiên + câu hỏi mở [CẦN XÁC NHẬN]
  ↓ User nói "xong/chốt" → [TỰ ĐỘNG — §0.2] rà soát chốt phiên: tổng hợp xung đột chéo + lỗ hổng còn lại
  ↓ ✋ GATE 1 — user confirm nội dung
  ↓ Ghi tri thức vào docs/03-features/F-xxx/source/*.md + vault (<TênProject>_Brain) + .kb/*
  ↓ Tự reindex: python3 tools/kb-indexer/build_index.py (index/graph/health luôn khớp docs/)
  ↓ Hỏi: "Tạo prototype với Claude Design?"
  ↓ ✋ GATE 2 — user chọn project Design (đã có / tạo mới)
  ↓ Sinh design brief + mở/hướng dẫn Claude Design (workflows/04)
  ↓ User chỉnh prototype trên Claude Design
  ↓ Sync kết quả về KB (workflows/05) — ✋ GATE 3 confirm
  ↓ Cập nhật changelog + relation graph
```

4 cổng duyệt: **Gate 1** tri thức, **Gate 2** tài liệu/design brief, **Gate 3** thay đổi design, **Gate 4** thay đổi code.

---

## 5. Quy tắc giao tiếp với user non-tech

- Mỗi bước chỉ hỏi 1 nhóm câu hỏi, kèm giải thích "vì sao cần".
- Luôn có phương án mặc định được gợi ý sẵn; user gõ "ok" là chạy tiếp.
- Báo tiến độ ngắn gọn dạng checklist sau mỗi bước.
- Không hiển thị nội dung kỹ thuật (JSON, code) trừ khi user hỏi.
- Khi lỗi (ví dụ Jira 401): giải thích nguyên nhân bằng lời thường + cách khắc phục.
- **Khi present file cho user** (vd `.env.local`): card file KHÔNG
  có nút mở thư mục chứa nó → luôn kèm theo (1) đường dẫn folder tuyệt đối trong khối
  code để copy, (2) hướng dẫn mở nhanh: macOS = Finder → `Cmd+Shift+G` → dán đường dẫn;
  Windows = Explorer → dán vào thanh địa chỉ. File ẩn (bắt đầu bằng `.`) nhắc thêm:
  macOS nhấn `Cmd+Shift+.` để hiện file ẩn.

---

## 6. Phiên bản, cập nhật & dời máy (Genesis-1)

- **Bản hiện tại:** Genesis-1 (`version.json`); lịch sử app ở `CHANGELOG.md` (khác
  `.kb/changelog.md` — file đó là lịch sử **tri thức** của user).
- **Tách CORE vs DATA.** *CORE* = phần đi theo repo (CLAUDE.md, workflows, templates,
  tools, scripts, presets, `factory-config.example.yaml`, **`.kb/rules.md` + `.kb/system-lessons.md`**…).
  *DATA* = tri thức của user (`docs/`, vault `*_Brain/`, `inbox/`, `.kb/*` **TRỪ 2 file CORE vừa nêu**,
  `config/factory-config.yaml`, `config/domain-rules.md`, `.env.local`) — đã gitignore, GIỮ NGUYÊN khi update.
- **Mô hình phát hành:** user TẢI ZIP → giải nén → mở trong Cowork → `@khởi tạo dự án`.
  Đa số KHÔNG có `.git`, nên cập nhật/dời máy đều làm bằng **lệnh tự nhiên trong Cowork**
  (Claude tự chạy script), KHÔNG bắt user đi tìm file `.command`.
- **Cập nhật:** user nhắn **"cập nhật phiên bản" / "cập nhật ứng dụng" / "kiểm tra phiên bản"**
  → `workflows/10-update.md`. KHÔNG hỏi lại "cập nhật cái gì", chạy thẳng WF10; chỉ "cập nhật"
  TRƠ mới hỏi phân biệt.
  So `version.json` local với bản trên GitHub → nếu mới hơn, hiện **`intro`** (nội dung giới
  thiệu) + tóm tắt CHANGELOG + cách nâng cấp; nếu **`force:true`** thì đánh dấu "bản quan trọng".
  Confirm → `scripts/update.command` chỉ thay CORE, **KHÔNG đụng DATA**. Nên TỰ kiểm tra ở cuối setup.
- **Dời máy (không mất tri thức):** user nhắn **"sao lưu/chuyển máy"** → `workflows/11-export-import.md`
  mục A (export DATA ra `genesis1-kb-*.zip`); ở máy mới (base sạch) nhắn **"nhập tri thức"**
  → mục B (import). Token `.env.local` cân nhắc bảo mật khi chuyển.
- **Config là DATA.** `config/factory-config.yaml` và `config/domain-rules.md` bị gitignore;
  bản template đi kèm repo là `config/factory-config.example.yaml` và `config/domain-presets/`.
  **Khi setup, nếu thiếu `config/factory-config.yaml` → copy từ `config/factory-config.example.yaml`**
  rồi điền giá trị (đừng tạo từ đầu).
- **Phát hành vs deploy landing (xem `RELEASING.md`).** Repo vừa là landing (GitHub Pages tự
  deploy mỗi lần push) vừa là app base. Tín hiệu "có bản app mới" là **`version.json`**:
  - Sửa CORE muốn app đã cài nhận được → **TĂNG `version.json`** + ghi `CHANGELOG.md` (kèm bước
    migration nếu có) → push. App gõ "cập nhật phiên bản" sẽ thấy + làm theo CHANGELOG.
  - Chỉ sửa landing (`index.html`…) → **GIỮ NGUYÊN `version.json`** → web deploy, app đã cài im lặng.
- **Tiến hóa hệ thống (meta).** `workflows/13-evolve-system.md` (maintainer-only) tự rà soát +
  cải tiến chính các *workflow & rule* — đối ứng `workflows/09-evolve.md` lo phần *tri thức*.
  **Hai tầng bài học:** `.kb/lessons.md` (tri thức/feature → workflow 09) vs `.kb/system-lessons.md`
  (quy trình/workflow → workflow 13). Đừng lẫn hai file này.

### Giới hạn đã biết (Genesis-1)

- **`docs/07-research/` và `.kb/rules.md` là CORE** (đi kèm app, ship sẵn) — KHÔNG lưu tri thức
  riêng của bạn vào đó (sẽ bị ghi đè khi update, không nằm trong gói export). Tri thức của bạn
  vào `docs/01…08`, vault `*_Brain/`, `inbox/`.
- **Đa nguồn:** đừng để 2 Jira trùng mã project (node graph theo mã issue, trùng sẽ đè).
- **`--since` theo giờ máy:** lệch timezone lớn với Jira Cloud có thể sót/trùng vài issue ở ranh
  giới — định kỳ **quét full** một lần cho chắc. Issue bị xoá trên Jira KHÔNG tự mất khỏi vault.
- **Import dời máy** dành cho máy có **base sạch**; bung lên instance đang có dữ liệu sẽ merge
  (vault được thay sạch, nhưng `.kb`/`docs` thì gộp).
