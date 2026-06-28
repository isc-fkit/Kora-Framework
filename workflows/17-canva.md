# Workflow 17 — Canva: tạo Sản phẩm / Thuyết trình

> Tương đương skill `/claude-knowledge-canva`. Chạy được kể cả khi skill chưa upload (đọc thẳng workflow này).
> Canva = **MCP app-level** → gọi MCP tool TRỰC TIẾP (không qua run_command). Cần connector Canva đã bật.

## Bước 0 — Verify (read-only)
`list-brand-kits` → connected? lấy `brand_kit_id`. Lỗi "Missing scopes" → disconnect/reconnect connector Canva.

## Bước 1 — Chọn loại (AskUserQuestion "Canva")
**[Sản phẩm từ brand template]** / **[Thuyết trình từ mô tả]** / **[← Huỷ]**.

## A. Sản phẩm từ brand template
1. `search-brand-templates dataset="non_empty"` → chọn template (phân trang >4). Không có → fallback `generate-design` + `brand_kit_id`, hoặc mở `create_url` để user tạo template autofill.
2. `get-brand-template-dataset` → field cần điền → AI map dữ liệu từ KB/mô tả → **✋ user CHỐT**.
3. `autofill-design` / `create-design-from-brand-template` → `design_id` → `export-design` (PDF/PNG/PPTX).

## B. Thuyết trình từ mô tả (phân tích → hỏi rõ → chốt → generate)
1. User mô tả → **AI phân tích** + AskUserQuestion làm rõ: đối tượng · số slide · tông/brand · nội dung từ KB nào.
2. Claude dựng **outline** (kéo nội dung từ vault/`.kb/index.json` nếu user chỉ định) → **trình outline → ✋ CHỐT** (CHƯA chốt → KHÔNG generate).
3. `generate-design-structured` (outline + `brand_kit_id`) → `design_id` → `get-design-pages` (kiểm) → `export-design` (PPTX/PDF).

## Bước cuối — Lưu KB + bước kế
- `docs/04-Designs/D-<slug>/source/design-meta.md` (type: design, source: canva, design_id) + `export/<file>` + backlink `[[…]]` → reindex `build_index.py --root .`.
- **LUÔN hỏi bước kế** (AskUserQuestion "Bước kế"): **[Tạo lịch tự động] · [Tạo design khác] · [Xuất định dạng khác] · [Dừng]**.

> ⛔ Approval Gate: TẠO/EXPORT design = ghi ra Canva user (outward) → CHỐT trước. Read-only (search/list/get) tự chạy.
