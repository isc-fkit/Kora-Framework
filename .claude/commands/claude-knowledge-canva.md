---
description: Create a Canva product/asset OR an auto-generated presentation. Choose [Product from brand template] or [Presentation from a description]; for presentations the AI analyzes the request, asks clarifying questions, and only generates after you confirm. Output is exported and saved under docs/04-Designs. Uses the Canva MCP connector (app-level). Triggers (vi): «tạo thiết kế canva», «tạo thuyết trình», «tạo slide», «tạo ấn phẩm/sản phẩm», «thiết kế từ template», «xuất bài thuyết trình» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-canva` — tạo sản phẩm/thuyết trình bằng **Canva MCP** (connector app-level, gọi MCP tool TRỰC TIẾP — KHÔNG qua run_command). Resolve tool path: `T=tools; [ -e "$T/connections/check_connection.py" ] || T="$HOME/.claude/kora-framework/tools"`.

> 🎨 **Canva là MCP app-level.** Cần connector Canva đã bật (Claude Desktop `/mcp` hoặc Cowork Settings → Connectors).
> Verify nhanh: `list-brand-kits` (read-only) chạy được = connected. Chưa có → hướng dẫn bật connector rồi quay lại.
> ⛔ **TẠO/EXPORT design = GHI ra Canva của user (outward) → PHẢI để user CHỐT trước khi tạo.** Read-only (search/list/get) tự chạy.

### Bước 0 — Verify Canva (read-only)
`list-brand-kits` → lấy `brand_kit_id` (ghi nhớ, dùng cho generate). Lỗi "Missing scopes" → nhắc disconnect/reconnect connector.

### Bước 1 — Chọn loại (AskUserQuestion, header "Canva", single-select)
**[Sản phẩm từ brand template] · [Thuyết trình từ mô tả] · [← Huỷ]**.

### Nhánh A — SẢN PHẨM từ brand template
1. `search-brand-templates` `dataset="non_empty"` (template autofill được) → AskUserQuestion liệt kê (id+name, >4 phân trang). Ô "Other" = từ khoá → `query=<keyword>`.
   - **KHÔNG có template non_empty** → fallback: dùng **[Thuyết trình/Generate]** với `brand_kit_id` (generate-design), HOẶC mời user tạo template autofill trong Canva (mở `create_url`).
2. `get-brand-template-dataset <template_id>` → xem các field cần điền.
3. **Lấy dữ liệu điền field** từ KB/Jira/mô tả user (AI map) → trình bày bản map cho user → **✋ CHỐT**.
4. Sau khi chốt → `autofill-design` (hoặc `create-design-from-brand-template`) với dataset đã map → nhận `design_id`.
5. **AskUserQuestion chọn ĐỊNH DẠNG** (PDF / PNG / PPTX) → `export-design <design_id> --format <…>` → tải file.

### Nhánh B — THUYẾT TRÌNH từ mô tả (AI phân tích → hỏi rõ → chốt → generate)
1. User MÔ TẢ (chủ đề, mục tiêu). **AI phân tích** + **AskUserQuestion làm rõ** (tối đa vài thẻ): **đối tượng nghe** · **số slide** · **tông/brand** (dùng `brand_kit_id`?) · **nội dung lấy từ KB nào** (feature/report/meeting trong vault?).
2. Claude DỰNG **outline** (tiêu đề + bullet từng slide), kéo nội dung từ KB nếu user chỉ định (tra `.kb/index.json` + vault). **Trình outline cho user → ✋ CHỐT** (sửa tới khi ưng). **CHƯA chốt → KHÔNG generate.**
3. Sau chốt → `generate-design-structured` (truyền outline + `brand_kit_id`) → `design_id`. (Mô tả tự do ngắn → `generate-design`.)
4. `get-design-pages <design_id>` (kiểm số trang/nội dung) → nếu cần chỉnh, lặp lại bước 2–3.
5. **AskUserQuestion chọn ĐỊNH DẠNG** (PPTX / PDF / PNG) → `export-design <design_id> --format <…>` → tải file.

### Bước cuối — Lưu vào KB + bước kế
- Lưu output: `docs/04-Designs/D-<slug>/` — `source/design-meta.md` (frontmatter: type: design, source: canva, design_id, template_id?, created) + `export/<file>` (PDF/PPTX/PNG). Backlink `[[…]]` tới feature/report liên quan. Reindex `python3 "$T/kb-indexer/build_index.py" --root .`.
- **LUÔN đề xuất bước kế** (AskUserQuestion, header ≤12 ký tự "Bước kế"): **[Tạo lịch tự động] · [Tạo design khác] · [Xuất định dạng khác] · [Dừng]**.
  - **[Tạo lịch tự động]** → `/claude-knowledge-schedule` (vd tự sinh ấn phẩm/báo cáo định kỳ — trong campaign Pha 6).
