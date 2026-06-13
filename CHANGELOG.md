# CHANGELOG — Lịch sử BẢN APP (AI Product Factory)

> File này ghi lịch sử **phiên bản của ứng dụng** (CORE: CLAUDE.md, workflows, templates,
> tools, scripts…) — tức là phần đi theo repo khi bạn tải/cập nhật.
>
> ⚠️ **Khác với `.kb/changelog.md`**: file đó ghi lịch sử **tri thức của user** (DATA:
> mỗi lần ghi/sửa tài liệu trong `docs/`, vault, ai duyệt, vì sao). Khi bạn cập nhật app
> (`scripts/update.command`), `CHANGELOG.md` này có thể đổi, còn `.kb/changelog.md` của
> bạn được GIỮ NGUYÊN.

---

## v1.0.1 "Genesis-1" — 2026-06-14

- **Base trung lập:** dọn mọi ví dụ dính dự án gốc (tên project, URL Jira, mã issue…) → placeholder
  chung (`MyApp`, `jira.company.vn`, `PROJ-102`…) để user mới setup không nhầm.
- **Tự tiến hóa hệ thống (meta):** thêm `workflows/13-evolve-system.md` — review đối kháng + cải tiến
  chính workflow/rule (maintainer-only), kèm `.kb/system-lessons.md` (bài học tầng quy trình, CORE).
- **Vá setup & quét Jira:** không dùng AskUserQuestion cho input tự do (hết lỗi "Failed"); "quét jira"
  thêm bước chọn nguồn/domain (Server nội bộ / Cloud Atlassian) qua `JIRA_ENV_FILE`.
- **Video hướng dẫn** chuyển sang link Google Drive (bỏ file mp4 nặng trong repo).
- **Kênh phát hành** chuyển sang branch `release` (download + update + Pages từ `release`).
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.0 "Genesis-1" — 2026-06-13

- Bản nền đầu tiên: AI Product Factory điều phối qua CLAUDE.md + workflows.
- Quét Jira đa nguồn (Server tự host + Cloud Atlassian), mỗi nguồn sync riêng, merge an toàn.
- Import Word/PDF, hiểu sơ đồ sequence bằng vision.
- Tự phân tích/đối chiếu xung đột, tự học (lessons), tự reindex.
- Lịch tự đồng bộ chạy-bù khi mở app, chỉ lấy issue mới (--since).
- Cơ chế update giữ tri thức + export/import dời máy.
