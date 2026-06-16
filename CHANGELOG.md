# CHANGELOG — Lịch sử BẢN APP (AI Product Factory)

> File này ghi lịch sử **phiên bản của ứng dụng** (CORE: CLAUDE.md, workflows, templates,
> tools, scripts…) — tức là phần đi theo repo khi bạn tải/cập nhật.
>
> ⚠️ **Khác với `.kb/changelog.md`**: file đó ghi lịch sử **tri thức của user** (DATA:
> mỗi lần ghi/sửa tài liệu trong `docs/`, vault, ai duyệt, vì sao). Khi bạn cập nhật app
> (`scripts/update.command`), `CHANGELOG.md` này có thể đổi, còn `.kb/changelog.md` của
> bạn được GIỮ NGUYÊN.

---

## v1.0.9 "Genesis-1" — 2026-06-15

- **Render đẹp field tiến độ khi quét Jira:** `import_jira.py` thêm xử lý riêng cho **Sprint**
  (Cloud object + parse được chuỗi serialize của Jira Server → `Sprint 3 (active, ngày-bắt-đầu →
  ngày-kết-thúc)`), **time tracking** (Ước tính gốc / Còn lại / Đã log), và field thời-gian-giây
  (`timespent`, `timeoriginalestimate`, `timeestimate` → đổi sang `8h`, `2d`). Sprint + time +
  start/end/due đưa cả lên frontmatter cho dễ tra. Story points (số thường) không bị nhầm thành thời gian.

## v1.0.8 "Genesis-1" — 2026-06-15

- **Quét Jira CÀO HẾT mọi field:** `tools/jira-to-obsidian/import_jira.py` mặc định dùng
  `fields=*all` — mỗi note lấy TẤT CẢ field của issue (priority, labels, components, assignee,
  reporter, created/updated, resolution, sprint, story points và MỌI custom field) ở mục
  `## Tất cả field (đầy đủ)`, tên custom field hiển thị người-đọc (map từ `/rest/api/2/field`).
  Thêm flatten ADF (rich-text Cloud), enrich frontmatter, attachment kèm link. Tắt bằng
  `JIRA_FETCH_ALL_FIELDS=false` cho chế độ gọn.
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn. Quét lại để lấy đầy đủ field mới.)

## v1.0.7 "Genesis-1" — 2026-06-14

- **Obsidian là TÙY CHỌN:** setup (`workflows/00-setup.md` Bước 3) giờ HỎI "đã cài Obsidian chưa?"
  trước, gợi ý cài nếu cần, và nói rõ hệ thống chạy bình thường KHÔNG cần Obsidian (vault chỉ là
  thư mục `.md`; mở bằng editor markdown bất kỳ). Ghi rõ ở README + landing.
- **OS-dynamic toàn repo:** thêm nguyên tắc 12 trong `CLAUDE.md` (python3↔`py`, `mv`↔`Move-Item`,
  path `/`↔`\`, mở folder/file ẩn theo OS). Mọi lệnh `python3 build_index.py` nêu biến thể Windows
  `py`; Bước 3 đổi tên thư mục có lệnh PowerShell; `scripts/update.bat` sửa `python3`→`py`.
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.6 "Genesis-1" — 2026-06-14

- **Sau khi quét Jira → gợi ý nạp thêm nguồn:** `workflows/01-import-jira.md` Bước 5 giờ hỏi 4
  lựa chọn — Phân loại · **Quét thêm nguồn Jira khác** (domain nội bộ/Cloud) · **Nạp thêm tài liệu
  (PDF/DOCX/ảnh)** · Để raw. Thêm nguyên tắc §0.4: nạp xong một nguồn thì LUÔN mời nạp thêm nguồn khác.
- **Nhận ẢNH RỜI làm tri thức:** `workflows/02-import-files.md` thêm loại file PNG/JPG/JPEG/WEBP —
  Claude đọc bằng vision (sơ đồ/flow → flow/BR/AC; ảnh UI → design_note). Trigger ở CLAUDE.md nhận "ảnh".
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.5 "Genesis-1" — 2026-06-14

- **Setup nhập liệu bằng THẺ (gợi ý + ô trống), không bắt gõ chat:** Bước 2 (tên project) & Bước 3
  (đường dẫn vault, tên thư mục) giờ hiện AskUserQuestion với gợi ý + ô **"Other"** để bạn tự gõ.
  Sửa rule `CLAUDE.md` §1.8: AskUserQuestion CÓ nhận free text qua ô "Other" — "Failed" trước kia
  do thiếu option cố định, không phải bản chất. Token/secret vẫn chỉ nhập qua `.env.local`.
- **Bước 7 luôn được đánh dấu hoàn thành:** thêm bước đóng task tracker khi `setup_completed:true`
  — không còn để Bước 7 treo "chưa hoàn thành", kể cả khi chạy một mạch tới cuối.
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.4 "Genesis-1" — 2026-06-14

- **Setup luôn hiện THẺ CHỌN ở mọi bước:** vá nốt các sub-step còn bắt gõ tay — "thêm/bớt rule"
  và "đặt lịch sync" giờ mở bằng AskUserQuestion (Có/Không) trước, chỉ hỏi nhập tự do SAU khi user
  chọn nhánh cần nhập. Thêm nguyên tắc 🔑 "mở đầu MỌI quyết định bằng thẻ chọn" vào `workflows/00-setup.md`
  + `CLAUDE.md` §1.8 (bản v1.0.3 mới ép "mỗi bước dừng hỏi" nhưng chưa đổi sub-step free-text thành thẻ).
- **Đồng bộ nhãn version landing:** thêm bước BẮT BUỘC trong `workflows/12-release.md` + `RELEASING.md`
  để mỗi lần phát hành tự cập nhật nhãn version hiển thị trên `index.html` (model card + footer).
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.3 "Genesis-1" — 2026-06-14

- **Đổi tên lệnh → "cập nhật phiên bản":** bỏ hẳn tên cũ "cập nhật model" (chữ "model" gây nhiễu)
  ở mọi nơi. Tên chính giờ là **"cập nhật phiên bản"** + alias "cập nhật ứng dụng / app",
  "lên bản mới nhất", "có bản mới không", "kiểm tra phiên bản".
- **Setup BẮT BUỘC hỏi từng bước:** `workflows/00-setup.md` thêm rule cứng — mỗi bước DỪNG LẠI
  hỏi user (AskUserQuestion / câu thường) rồi mới sang bước kế; KHÔNG tự chọn mặc định, KHÔNG
  gộp bước, KHÔNG chạy lướt. Rule "tự chạy không hỏi" chỉ áp cho phân tích read-only.
- **Luôn hỏi trước khi THỰC THI:** `CLAUDE.md` Approval Gate viết lại rộng hơn — phân tích
  read-only vẫn tự chạy, nhưng mọi thao tác ghi/chạy/sửa/export đều phải hỏi xác nhận mới làm.
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

## v1.0.2 "Genesis-1" — 2026-06-14

- **Hiểu đúng lệnh "cập nhật phiên bản":** lệnh này = **nâng ỨNG DỤNG lên bản phát hành mới**.
  AI chạy thẳng `workflows/10-update.md`, KHÔNG còn hỏi nhầm "bạn muốn cập
  nhật cái gì". Thêm alias: "cập nhật ứng dụng / app", "có bản mới không".
- **Force update + nội dung giới thiệu:** `version.json` thêm 2 field `force` (bool) + `intro`
  (string). Khi phát hành, `workflows/12-release.md` hỏi force? + nội dung giới thiệu; user bản cũ
  lúc **kiểm tra cập nhật** sẽ thấy `intro` nổi bật + cách nâng cấp (force → đánh dấu "bản quan trọng").
- **Video hướng dẫn xem tốt hơn trên điện thoại:** thêm quyền `fullscreen`, link "⛶ Xem toàn màn
  hình" (mở trình phát Drive native — xoay ngang/dọc được), và tinh chỉnh khung video cho mobile.
- **Setup hiện thẻ chọn bấm được:** `workflows/00-setup.md` ghi rõ từng bước hữu hạn dùng
  AskUserQuestion (domain, ngôn ngữ, vault, có/không Jira/file, design); input tự do vẫn hỏi câu thường.
- **Quét Jira bằng lệnh Terminal (bỏ file double-click):** xóa `quet-jira.command`/`.bat` (hay bị
  macOS chặn "không đáng tin cậy"); chỉ dùng lệnh Terminal copy-paste, **điền sẵn đường dẫn tuyệt
  đối thật theo máy/OS, không cần `cd`, không hardcode**. Sửa tài liệu setup (bỏ `pip install` thừa).
- (Không có migration DATA → cập nhật giữ nguyên tri thức của bạn.)

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
