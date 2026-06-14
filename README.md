# AI Product Factory — Dynamic Knowledge Base

Hệ thống giúp bạn (không cần biết kỹ thuật) biến yêu cầu bằng lời thường thành:
tri thức có cấu trúc → tài liệu chuẩn (URD/SRS) → prototype Claude Design → kế hoạch code.
Mọi bước AI tự chạy, **bạn chỉ cần confirm**.

## Phiên bản

**Genesis-1 · v1.0.0** (xem `version.json` và `CHANGELOG.md`).
Đây là bản nền đầu tiên: điều phối qua `CLAUDE.md` + workflows, quét Jira đa nguồn,
import Word/PDF, tự phân tích xung đột, tự học, tự reindex.

## Tải & cài đặt

1. **Tải mã nguồn** — chọn 1 trong 2 cách:
   - Tải file zip: <https://github.com/luugiakhanh689/adaptive_knowledge_base/archive/refs/heads/release.zip>
     → giải nén.
   - Hoặc clone bằng git:
     ```
     git clone https://github.com/luugiakhanh689/adaptive_knowledge_base
     ```
2. **Mở trong Cowork**: tạo project → chọn folder vừa giải nén/clone làm thư mục làm việc.
   (Thấy "Instructions · CLAUDE.md" ở sidebar là đúng.)
3. **Khởi tạo**: nhắn **`@khởi tạo dự án`** → Claude hỏi xác nhận rồi chạy setup từng bước.

## Lần đầu sử dụng (3 bước)

1. **Import folder**: mở Cowork → tạo project → chọn folder này làm thư mục làm việc.
   (Claude sẽ tự nạp `CLAUDE.md` — thấy "Instructions · CLAUDE.md" ở sidebar là đúng.)
2. Nhắn: **`@khởi tạo dự án`** → Claude hỏi xác nhận rồi chạy setup từng bước:
   domain (có preset gợi ý) → tên project → nơi lưu Obsidian vault → quét Jira? →
   nạp file PDF/DOCX? → kết nối Claude Design. Mỗi câu có mô tả rõ + phương án mặc định.
3. Setup xong → chỉ cần nhắn vấn đề bằng lời thường, Claude phân tích dựa trên tri thức
   hiện có và chỉ hỏi khi cần xác nhận.

> Lưu ý: Claude luôn **hỏi confirm trước khi chạy lệnh** — nếu bạn chỉ hỏi thông tin
> có chứa keyword (vd "quét jira là gì?"), Claude sẽ trả lời chứ không tự chạy.

## Bảng lệnh

| Lệnh / bạn nhắn | Hệ thống làm | Workflow |
|---|---|---|
| `@khởi tạo dự án` | Setup toàn bộ hệ thống lần đầu | workflows/00-setup.md |
| `quét jira` | Quét TOÀN BỘ project Jira → vault (tự chạy; Jira nội bộ/VPN thì đưa lệnh Terminal copy-paste điền sẵn đường dẫn) | workflows/01-import-jira.md |
| `quét task PROJ-102` | Quét RIÊNG 1 hoặc vài issue/epic (cách nhau dấu phẩy) | workflows/01b-import-jira-single.md |
| Mô tả một vấn đề / tính năng | Phân tích → trình bày dễ hiểu → bạn duyệt → ghi KB | workflows/03-request.md |
| `thiết kế <tính năng>` | Chọn project Design → sinh brief → dựng prototype liên kết | workflows/04-claude-design.md |
| `sync design` | Cập nhật thay đổi từ prototype ngược về KB (có duyệt) | workflows/05-sync-back.md |
| Gửi file PDF/DOCX/zip Obsidian | Nạp tri thức qua pipeline duyệt | workflows/02-import-files.md |
| `xuất tài liệu` | Tạo DOCX/PDF cho người đọc | workflows/06-export-docs.md |
| `lên kế hoạch code <tính năng>` | Sinh implementation plan (cần BR/AC đã duyệt) | workflows/07-code-plan.md |
| `đặt lịch quét jira` | Tự động đồng bộ issue mới định kỳ (incremental --since) | workflows/08-schedule-sync.md |
| `tiến hóa KB` / `dọn dẹp KB` | Tự dựng lại chỉ mục, báo sức khỏe, dọn dead-link, hợp nhất trùng, học từ lỗi | workflows/09-evolve.md |
| `đổi domain` / `sửa rule` | Đổi rule phân tích bất cứ lúc nào | workflows/00-setup.md mục B |

## Cấu trúc

- `CLAUDE.md` — bộ não điều phối (Claude tự nạp)
- `workflows/` — kịch bản từng luồng, chạy step-by-step
- `config/` — domain + rules **động**, đổi được mọi lúc
- `docs/` — Knowledge Base chính (chỉ ghi sau khi bạn duyệt)
- `Project_Name_Brain/` — vault Obsidian, "bộ não" tri thức (setup tự đổi tên thành `<TênProject>_Brain`; mở bằng "Open folder as vault")
- `inbox/` — vùng đệm dữ liệu chưa duyệt
- `projects/` — danh bạ các project Claude Design
- `tools/jira-to-obsidian/` — tool quét Jira (script sẵn, chỉ điền `.env.local`)
- `.kb/` — chỉ mục, relation graph, source registry, changelog, **health-report**, **lessons** (bài học)
- `tools/kb-indexer/` — bộ tự-dựng-chỉ-mục (chạy bằng máy, không tốn token)

## Quét Jira — những điều nên biết

- Kết quả lưu vào thư mục vault (`vault_path` trong config) — mở bằng Obsidian.
- Mặc định **mỗi project Jira một thư mục riêng** tên `KEY_Tên-project` (vd `PROJ_MyApp/`);
  đổi mẫu tên bằng `PROJECT_FOLDER_PATTERN`, tắt gom bằng `GROUP_BY_PROJECT=false` trong `.env.local`.
- Quét lẻ vài task: `quét task PROJ-102` (merge vào vault, không đụng phần khác).
- Jira đặt tên loại issue không chuẩn (vd tiếng Việt) → khai `JIRA_TYPE_MAP` trong `.env.local`.
- Token chỉ nằm trong `.env.local` — Claude tạo file và mở cho bạn tự dán, không dán vào chat.
- **Hỗ trợ cả Jira Server/DC (Bearer PAT) lẫn Jira Cloud/Atlassian (email + API token)** — script tự nhận diện. Cloud lấy token tại: avatar → Account settings → Security → Create and manage API tokens.
- **Lấy dữ liệu mới định kỳ**: `python3 import_jira.py --since` chỉ kéo issue mới/cập nhật từ lần quét trước (nhanh). Đặt lịch tự động bằng lệnh `đặt lịch quét jira`.

> ⚠️ **Lưu ý lịch tự đồng bộ**: scheduled task chỉ **tự quét được khi Jira là Cloud/Atlassian
> hoặc public** (môi trường Claude ra được mạng). Với **Jira nội bộ/VPN** (vd `jira.company.vn`),
> lịch chỉ có thể **nhắc bạn** chạy lệnh Terminal `python3 "<đường-dẫn>/import_jira.py" --since`
> — vì sandbox không vào được mạng nội bộ, không có cron nào vượt qua rào đó.

## Cập nhật (giữ nguyên tri thức)

Khi có bản app mới, gõ **"cập nhật phiên bản"** trong Cowork (hoặc chạy file
**`scripts/update.command`**). Nó chỉ cập nhật phần **CORE** của app (CLAUDE.md, workflows, templates, tools, scripts…)
và **KHÔNG đụng tới DATA** của bạn — tri thức trong `docs/`, vault `*_Brain/`, `inbox/`,
`.kb/*`, `config/factory-config.yaml`, `config/domain-rules.md`, và token Jira được giữ
nguyên. Sau cập nhật, xem `CHANGELOG.md` để biết bản app có gì mới.

## Dời sang máy khác (export → import)

1. Trên máy cũ: chạy **`scripts/export-kb.command`** → đóng gói toàn bộ DATA (tri thức,
   vault, config, inbox, `.kb/*`) thành 1 file để mang đi.
2. Trên máy mới: tải bản app như mục "Tải & cài đặt", rồi chạy **`scripts/import-kb.command`**
   với gói vừa export → tri thức trở về đúng chỗ.

Riêng `.env.local` (token Jira) **không** đi theo gói export (chủ đích bảo mật) — điền lại
trên máy mới. Quét Jira chỉ cần Python 3 có sẵn (script dùng thư viện chuẩn, không phải
cài thêm gì); các luồng khác không cần gì.

## Phản hồi & báo lỗi

Gặp lỗi hoặc muốn góp ý? Mở issue tại:
<https://github.com/luugiakhanh689/adaptive_knowledge_base/issues>

## Nguyên tắc an toàn

Không gì được ghi vào KB chính khi bạn chưa duyệt. Token Jira chỉ nằm trong
`.env.local` (không commit, không dán vào chat). Mọi tri thức truy được nguồn gốc.
