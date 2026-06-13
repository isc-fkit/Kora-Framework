# Luật bảo trì Knowledge Base

1. **Đặt tên**: feature `F-xxx-<slug-khong-dau>`, business rule `BR-<feature>-NNN`, AC `AC-<feature>-NNN`, ADR `ADR-NNN`, source `SRC-<LOAI>-<id>`.
2. **Vị trí**: tri thức domain → docs/01-domain; tính năng → docs/03-features/F-xxx/source; quyết định → docs/06-decisions; thuật ngữ → docs/08-glossary.
3. **Frontmatter bắt buộc** cho mọi file KB: feature_id/type, version, status, updated.
4. **Không sửa file approved** mà không bump version + ghi changelog.
5. **Mọi node mới** phải vào relation-graph.json; mọi tri thức mới phải có source trong source-registry.json.
6. **Inbox không phải KB**: nội dung inbox chưa approve không được trích dẫn làm nguồn chính thức.
7. **Obsidian vault** sync 1 chiều từ docs/ + import; sửa tay trong vault phải báo Claude để sync ngược.
