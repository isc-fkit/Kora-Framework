# KEYWORD & VÍ DỤ — nói lời thường, hệ thống tự nhận diện

> Không cần nhớ lệnh. Nói bằng lời tự nhiên → Claude nhận diện ý định → **confirm 1 câu** rồi chạy.
> Phân tích read-only (Tầng A) thì **tự chạy không hỏi**. (Nguồn: bảng trigger CLAUDE.md §0.)

## 🟢 Tự chạy ngầm (không cần keyword)
| Hành vi | Khi nào | Ví dụ |
|---|---|---|
| Phân tích read-only (Tầng A) | bạn bàn 1 tính năng/yêu cầu/rule | "Thêm màn hình đăng nhập OTP" → tự đọc KB, nêu xung đột/tác động |
| Rà chốt phiên | bạn nói "xong/chốt" | "ok chốt ghi đi" |
| Tự học | đề xuất bị bác | (tự ghi `.kb/lessons.md`) |
| Hỏi làm rõ khi mơ hồ | yêu cầu ≥2 cách hiểu | (hỏi 1 câu trước khi làm) |

## 🔵 Trigger có keyword (đều confirm trước khi chạy)
| Việc | Keyword | Ví dụ gõ |
|---|---|---|
| Khởi tạo | `@khởi tạo dự án`, "cài đặt hệ thống" | *@khởi tạo dự án* |
| Quét / cập nhật Jira | "quét jira", "lấy dữ liệu mới từ jira", **"cập nhật dữ liệu mới từ jira"**, "kéo task về", "quét nguồn/dữ liệu", "import jira" | *cập nhật dữ liệu mới từ jira* → hỏi nguồn nếu ≥2 |
| Quét 1 task/epic | "quét task `<KEY>`", "quét epic `<KEY>`" | *quét task PROJ-102* |
| Kết nối nguồn | "kết nối nguồn", "connect", "thêm Jira/GitHub/Gmail…" | *kết nối Gmail* → hỏi SMTP hay MCP (ưu tiên SMTP) |
| Bật run_command 🖥️ | "bật run_command", "setup mcp local-terminal" | *bật run_command* (Claude Desktop) |
| Đẩy Confluence | "đẩy lên Confluence", "post tri thức" | *đẩy tri thức lên Confluence* |
| Đồng bộ KB lên repo 🔒 | "đồng bộ KB", "sync lên GitHub/SharePoint" | *sync KB lên GitHub* |
| Mật khẩu vận hành | "đặt mật khẩu vận hành", "set ops password" | *đặt mật khẩu vận hành* |
| Gửi mail báo cáo 🔒 | "gửi mail báo cáo", "email tiến độ cho team", "mail báo cáo", "gửi báo cáo qua email/mail" | *gửi mail báo cáo cho team* |
| Đặt lịch quét/sync | "đặt lịch quét jira", "tự động đồng bộ" | *đặt lịch quét jira 8h sáng* |
| Báo cáo tiến độ 🔒 | "báo cáo tiến độ", "tiến độ dự án", "cập nhật tiến độ", "sinh/làm/xuất báo cáo", "report" | *cập nhật tiến độ dự án FA* → hỏi LOẠI → nguồn → project |
| Đặt lịch báo cáo | "đặt lịch báo cáo", "lịch báo cáo tiến độ" | *đặt lịch báo cáo 8h hằng ngày* |
| Sửa danh sách mail | "sửa danh sách email báo cáo", "thêm người nhận mail" | *thêm a@x.com vào nhận report* |
| Mail cảnh báo sự cố | "sửa mail cảnh báo sự cố", "cấu hình mail lỗi lịch" | *đổi người nhận mail cảnh báo lịch* |
| Tiến hóa KB | "tiến hóa KB", "dọn dẹp KB", "kiểm tra sức khỏe KB" | *dọn dẹp KB, kiểm tra dead-link* |
| Nạp file | gửi PDF / DOCX / ảnh / zip Obsidian | (kéo `tài-liệu.pdf` vào chat) |
| Phân tích yêu cầu 🔵 | nêu vấn đề / yêu cầu / rule / màn hình | *Sửa rule: bệnh nhân <6 tuổi miễn phí khám* (tự phân tích) |
| Xuất tài liệu | "xuất tài liệu", "export docx/pdf" | *xuất tài liệu F-012 ra Word* |
| Đổi domain/rule | "đổi domain", "sửa rule" | *đổi domain sang fintech* |
| Xem phiên bản | "đang cài bản nào", "phiên bản hiện tại", "version bao nhiêu", "đang dùng bản nào" | *đang cài bản nào?* (chỉ đọc) |
| Cập nhật APP | "cập nhật phiên bản", "cập nhật phiên bản mới nhất", "cập nhật ứng dụng", **"cập nhật framework"**, "update framework", "nâng cấp Kora", "lên bản mới nhất", "có bản mới không" | *cập nhật phiên bản mới nhất framework* → chạy thẳng WF10 |
| Sao lưu / dời máy | "sao lưu", "chuyển/dời máy" | *sao lưu tri thức để chuyển máy* |
| Nhập tri thức | "nhập tri thức", "khôi phục", đưa file `*-kb-*.zip` | (kéo `kora-kb-FMC.zip` vào chat) |
| Đóng gói bàn giao | "đóng gói bàn giao", "archive", "handover" | *đóng gói bàn giao cho team QC* |
| Phát hành 🔒m | "phát hành", "release", "ra bản mới" | *phát hành v2.13* (chỉ maintainer) |
| Tiến hóa hệ thống 🔒m | "tiến hóa hệ thống", "rà soát workflow" | *rà soát + cải tiến workflow* (chỉ maintainer) |
| Report hoá đơn/họp 🔒 | "báo cáo hoá đơn", "tổng hợp hoá đơn", "báo cáo quý", "báo cáo cuộc họp" | *tổng hợp ảnh hoá đơn → báo cáo quý* · *báo cáo họp + roadmap* |
| Tạo Canva | "tạo thuyết trình", "tạo thiết kế canva", "tạo ấn phẩm/slide" | *tạo bài thuyết trình thị trường Q3* (AI hỏi rõ → chốt) |
| Campaign tự động | "tạo campaign", "tự động hoá a-z", "chuỗi tự động như n8n" | *tự động hằng quý: gom hoá đơn → report → gửi sếp* |
| Kiểm tra worklog 🔒 | "kiểm tra logwork", "soát task tạo có đúng không", "kiểm tra thời gian task tháng", "gợi ý lịch tạo task" | *kiểm tra task tháng 6 tạo đúng giờ chưa* → hỏi tháng → quét → biểu đồ timeline + lỗi |
| Chiến lược GEO 🔒 | "phân tích GEO", "tăng GEO", "tối ưu AI search", "được AI trích dẫn", "roadmap GEO", "generative engine optimization" | *phân tích nội dung để được ChatGPT/Perplexity trích dẫn* → chấm 8 chiều GEO → việc cần làm + roadmap 1 năm/5 năm → lên chiến dịch |

⚠️ **Tránh nhầm:** "cập nhật **dữ liệu** jira" = quét ≠ "cập nhật **phiên bản/ứng dụng**" = update app.
🏷️ **Bí danh của CHƯƠNG TRÌNH này:** "framework" · "Kora" · "hệ thống" · "app/ứng dụng" · "chương trình" — user nói
"cập nhật framework / nâng cấp Kora / update hệ thống" đều = **cập nhật APP (WF10)**. **TUYỆT ĐỐI KHÔNG hỏi lại
"framework nào? ở đâu?"** — chính là ứng dụng đang chạy đây.
🛟 **Skill Failed / chưa upload trong app → KHÔNG dead-end (áp cho MỌI skill):** ① có workflow tương đương → chạy
workflow trong `workflows/` (bảng CLAUDE.md §0; project không có → `~/.claude/kora-framework/workflows/`); ② không có
workflow → **mở file skill trên đĩa** `Skill/claude-knowledge-<x>.md` (fallback `~/.claude/commands/` →
`~/.claude/kora-framework/Skill/`) và LÀM THEO NỘI DUNG. KHÔNG xin lỗi suông, KHÔNG hỏi ngược, KHÔNG bắt user gõ lại.
🔒 = cần mật khẩu vận hành · 🔒m = chỉ maintainer · 🔵 = tự chạy không cần lệnh.
