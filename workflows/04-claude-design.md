# Workflow 04 — Claude Design: chọn project, dựng prototype liên kết

> Trigger: user chọn [A] sau workflow 03, hoặc nhắn "thiết kế <tính năng>" (confirm trước).

## Bước 1 — ✋ GATE 2: Chọn project Design

Đọc `projects/_registry.md`, hỏi user:

1. **Dùng project đã có** — liệt kê các project trong registry kèm danh sách màn hình/
   feature đã dựng. Nếu chọn: **chỉ tương tác với các màn hình/feature liên quan đến
   yêu cầu hiện tại** (tra relation graph), không đụng phần khác.
2. **Tạo project mới** — hỏi tên + mô tả → tạo entry mới trong registry theo
   `templates/design-project-template.md` (cấu trúc dynamic: project → screens →
   features → links).

## Bước 2 — Sinh Design Brief

Đọc theo thứ tự: `01-user-document.md` → `02-claude-context.md` → `03-business-rules.md`
→ `04-acceptance-criteria.md` → design system/prototype map của project Design đã chọn
(trong registry) → `config/domain-rules.md` (phần Design Rules).

Tạo `docs/03-features/F-xxx/source/05-design-brief.md` theo
`templates/design-brief-template.md`. Brief PHẢI có:

- Feature ID + liên kết các feature/màn hình liên quan (để prototype mới link đúng
  vào prototype cũ — navigation, state dùng chung).
- Business rules ảnh hưởng UI (validate, ngưỡng, trạng thái lỗi/rỗng).
- AC dạng checklist để design tự kiểm.
- Ràng buộc domain (vd: y tế → không bịa số liệu lâm sàng trong mock data).

## Bước 3 — Sinh Workspace Rules cho project Design (lần đầu tạo project)

Khi tạo project Claude Design MỚI, sinh kèm khối **Workspace Rules** để user dán vào
phần *Project Instructions / Custom Instructions* của project trên web — để mọi chat
trong project Design đó tự tuân cấu trúc factory. Nội dung sinh từ:

- `config/domain-rules.md` mục 4 (Design Rules theo domain)
- Design system hiện có trong `projects/_registry.md`
- Quy tắc liên kết: màn hình mới phải nối điều hướng với màn hình cũ liên quan;
  đủ trạng thái bình thường/rỗng/lỗi/loading; mock data theo rule domain
- Quy tắc sync: kết thúc phiên design phải xuất "tóm tắt thay đổi" để dán lại
  Cowork (`sync design`)

Lưu khối này vào `projects/<tên-project>/workspace-rules.md` + in ra cho user copy.

## Bước 4 — Mở Claude Design

1. In **prompt hoàn chỉnh đã điền sẵn** (khối code, copy được) tổng hợp từ brief —
   không in template trống.
2. **Tự mở web nếu được**: có Claude in Chrome (browser tools) → mở
   `https://claude.ai/projects` (project Design tương ứng), user chỉ việc dán prompt.
   Không có browser tools → in link kèm hướng dẫn: mở project Design trên claude.ai
   → New chat → dán prompt + đính kèm file trong checklist.
3. Nếu môi trường có khả năng tạo artifact/preview trực tiếp: hỏi user
   "Dựng prototype ngay tại đây?" → dựng HTML/React prototype làm artifact,
   các màn hình trong cùng project phải **liên kết điều hướng với nhau**.
4. Checklist file đính kèm khi dán prompt: 01-user-document.md, 02-claude-context.md,
   05-design-brief.md, ảnh tham khảo nếu có.

## Bước 5 — Ghi nhận

- Cập nhật `projects/_registry.md`: thêm màn hình/feature mới vào project,
  link tới brief + prototype.
- Cập nhật relation graph: edges `feature → screen`, `screen → screen (navigates_to)`.
- Ghi changelog.
- Nhắc user: "Sau khi chỉnh prototype xong, nhắn **'sync design'** và dán/mô tả
  những gì đã đổi — tôi sẽ cập nhật ngược về Knowledge Base."
