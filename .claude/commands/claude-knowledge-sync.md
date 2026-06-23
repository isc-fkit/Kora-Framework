---
description: Sync the synthesized knowledge base UP to your connected targets (Confluence and/or a private GitHub repo). Idempotent — no duplicates, only new/changed — with US↔change-request versioning (keeps the old US, marks it superseded, links the new CR). Password-gated (operations password). Triggers (vi): «đồng bộ KB», «sync tri thức», «đẩy KB lên GitHub/Confluence/SharePoint» → tự gọi skill này khi user nhắn các ý đó (tiếng Việt) trong Cowork.
---

The user invoked `/claude-knowledge-sync` — đẩy KB cục bộ → target đã kết nối (Confluence chung và/hoặc repo
GitHub riêng tư). Theo `workflows/16-sync.md`. **CÓ CỔNG MẬT KHẨU vận hành (`KORA_OPS_PW`)** — KHÔNG áp cho `/claude-knowledge-export-*`.

**Luồng (mỗi bước GHI đều confirm — Approval Gate):**
1. **Chọn TARGET** (AskUserQuestion, multi-select): **[Confluence] / [GitHub] / [GitLab] / [SharePoint]** — chỉ hiện
   target đã bật (`confluence.enabled` / `github.enabled` / `gitlab.enabled` / `sharepoint.enabled`). >4 → phân trang. Chưa cấu hình → đi mục "Cấu hình" trong WF16 trước.
2. **Cổng mật khẩu:** hướng dẫn user đặt `KORA_OPS_PW` (biến môi trường — **KHÔNG hỏi qua card,
   KHÔNG in ra**) → chạy `python3 tools/archive-gate/verify_ops_password.py`. Exit ≠ 0 → **DỪNG** ("Sai mật khẩu"), không làm gì.
3. **Đánh dấu phiên bản US↔CR:** `python3 tools/kb-sync/version_mark.py --root . --apply`
   (giữ US cũ + `superseded` + banner + link CR) rồi reindex `python3 tools/kb-indexer/build_index.py --root .`.
4. **Xem trước (Gate 2):** chạy `--push --dry-run` cho target đã chọn → trình bày +tạo/~cập nhật/-xóa → confirm.
5. **Đẩy thật (idempotent, không nhân bản — chỉ mới/đổi):**
   - Confluence: `python3 tools/confluence-sync/sync_confluence.py --push`
   - GitHub: `python3 tools/github-sync/sync_github.py --push`
   - GitLab: `python3 tools/gitlab-sync/sync_gitlab.py --push`
   - SharePoint: `python3 tools/sharepoint-sync/sync_sharepoint.py --push`
6. Báo kết quả + ghi `.kb/changelog.md`. Lần đầu push thành công → ghi
   `confluence.{enabled,base_url,space_key,parent_page_id}` / `github.{enabled,repo,branch}` /
   `sharepoint.{enabled,base_url,site_name,library}` vào config (lần sau khỏi hỏi).

> ⚠️ **SharePoint cần app registration Azure AD:** client-credentials (chạy nền) cần **admin consent
> `Sites.ReadWrite.All`**; device-flow (`--login`) chỉ tương tác. Sandbox Cowork chặn API → đẩy/verify
> SharePoint chạy ở **máy thật** (hoặc lịch HĐH). Token theo rule §1.6 (env `~/.zshrc` / `.env.local` cho lịch nền).

Token CHỈ ở `tools/*/​.env.local` (đã gitignore) — KHÔNG vào chat/log/config. Windows: `python3` → `py`.
Nguồn quét bằng bản cũ (đồ thị thiếu `link_type`) → version_mark nhắc quét lại để nhận diện CR đầy đủ.
