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
> ⚠️ **Chống nhầm lệnh 2 — LUÔN CONFIRM Ý ĐỊNH:** Keyword có thể xuất hiện trong câu
> hỏi thường (vd: "quét jira là gì?", "khởi tạo dự án mất bao lâu?"). Trước khi chạy
> bất kỳ workflow nào, nếu tin nhắn KHÔNG phải lệnh rõ ràng, phải hỏi lại 1 câu:
> *"Bạn muốn tôi chạy [tên luồng] ngay, hay chỉ đang hỏi thông tin?"* — user xác nhận
> mới chạy. User chỉ hỏi → trả lời bình thường, không chạy gì cả.

| User nhắn | Claude làm gì |
|---|---|
| `@khởi tạo dự án` (hoặc "setup factory", "cài đặt hệ thống") | Confirm → chạy `workflows/00-setup.md` từng bước |
| "quét jira" (toàn bộ project) | Confirm → chạy `workflows/01-import-jira.md` |
| "quét task <KEY>" / "quét epic <KEY>" (vd `quét task FPT-102`) | Confirm → chạy `workflows/01b-import-jira-single.md` |
| "đặt lịch quét jira", "tự động đồng bộ jira" | Confirm → chạy `workflows/08-schedule-sync.md` |
| "tiến hóa KB", "dọn dẹp KB", "kiểm tra sức khỏe KB" | Confirm → chạy `workflows/09-evolve.md` |
| Gửi file PDF/DOCX/zip Obsidian | Confirm → chạy `workflows/02-import-files.md` |
| Nêu một vấn đề / yêu cầu tính năng mới | Chạy `workflows/03-request.md` |
| "thiết kế", "prototype", "mở Claude Design" | Confirm → chạy `workflows/04-claude-design.md` |
| "sync design", dán kết quả từ Claude Design | Confirm → chạy `workflows/05-sync-back.md` |
| "xuất tài liệu", "export docx/pdf" | Confirm → chạy `workflows/06-export-docs.md` |
| "đổi domain", "sửa rule" | Confirm → chạy `workflows/00-setup.md` mục B (chỉ phần domain/rules) |

**Nếu chưa setup** (`config/factory-config.yaml` còn giá trị `TODO`): với MỌI yêu cầu,
đề nghị user chạy `@khởi tạo dự án` trước, giải thích ngắn gọn vì sao.

---

## 1. Nguyên tắc bất biến (không phụ thuộc domain)

1. **Đọc KB trước, viết KB sau.** Mọi phân tích phải dựa trên tri thức trong `docs/`
   và vault (`vault_path` trong config), trích nguồn theo đường dẫn file. Không có nguồn → nói rõ là suy luận.
2. **Approval Gate.** Không ghi tri thức vào KB chính (`docs/`), không cập nhật
   `.kb/relation-graph.json`, không chạy Claude Design, không sửa code khi user chưa confirm.
3. **Trình bày bằng ngôn ngữ tự nhiên trước.** Khi phân tích xong, trả lời user bằng
   tiếng Việt dễ hiểu (không dán file thô), rồi mới hỏi confirm để ghi vào `.md`.
4. **Không bịa tri thức.** Thiếu thông tin → đánh dấu `[CẦN XÁC NHẬN]`.
   Tri thức chuyên môn (ngưỡng y tế, quy định pháp lý...) chưa có nguồn → `[CẦN XÁC NHẬN CHUYÊN MÔN]`.
5. **Trace được nguồn.** Mọi tri thức phải có mặt trong `.kb/source-registry.json`.
6. **Không lưu secret.** Token/password chỉ nằm trong `tools/jira-to-obsidian/.env.local`
   (đã gitignore). Không in token ra log/chat.
7. **Mọi thay đổi ghi changelog** vào `.kb/changelog.md` (ngày, source, file, lý do, người duyệt).
8. **Hỏi bằng lựa chọn.** Khi cần input của user, luôn đưa ra các phương án gợi ý
   (dùng AskUserQuestion nếu có) kèm mô tả rõ, cho phép user chọn hoặc tự điền.
9. **Thao tác file phải có fallback.** Sandbox có thể bị chặn quyền xóa/đổi tên
   thư mục trong folder của user. Mọi `mv`/`rm`/rename phải: thử → lỗi thì dùng cách
   thay thế (tạo mới + copy, hoặc giữ nguyên tên và chỉ cập nhật config) → tệ nhất
   hướng dẫn user làm tay 1 thao tác. TUYỆT ĐỐI không để workflow fail giữa chừng
   vì một thao tác file.
10. **Tự tiến hóa, không chỉ tích lũy.** SAU MỖI lần ghi tri thức đã duyệt vào `docs/`
   (workflow 02/03/05), LUÔN chạy `python3 tools/kb-indexer/build_index.py --root .`
   để dựng lại `.kb/index.json` + `relation-graph.json` + `health-report.md` (rẻ, bằng
   máy). Đọc `.kb/lessons.md` trước khi phân tích để không lặp lỗi cũ. Định kỳ chạy
   `workflows/09-evolve.md` để dọn dead-link, hợp nhất trùng lặp, phát hiện mâu thuẫn,
   bù lỗ hổng coverage.
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
  ↓ Claude đọc .kb/index.json + relation-graph → load đúng file liên quan; index trống mà vault có dữ liệu Jira → grep thẳng vault, KHÔNG trả lời chay
  ↓ Phân tích: feature mới hay sửa feature cũ? ảnh hưởng gì? thiếu gì?
  ↓ Trình bày kết quả bằng tiếng Việt tự nhiên + câu hỏi mở [CẦN XÁC NHẬN]
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
- **Khi present file cho user** (vd `.env.local`, `quet-jira.command`): card file KHÔNG
  có nút mở thư mục chứa nó → luôn kèm theo (1) đường dẫn folder tuyệt đối trong khối
  code để copy, (2) hướng dẫn mở nhanh: macOS = Finder → `Cmd+Shift+G` → dán đường dẫn;
  Windows = Explorer → dán vào thanh địa chỉ. File ẩn (bắt đầu bằng `.`) nhắc thêm:
  macOS nhấn `Cmd+Shift+.` để hiện file ẩn.
