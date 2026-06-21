# Domain Preset — Government / Khu vực công

### 1. Thuật ngữ & quy ước
- Thuật ngữ hành chính công kèm giải thích VN trong glossary (vd thủ tục hành chính/TTHC, hồ sơ một cửa, DVC trực tuyến, mức độ 3/4).
- Phân biệt rõ công dân/doanh nghiệp, cán bộ xử lý, cơ quan/đơn vị.

### 2. Rule phân tích nghiệp vụ
- Mỗi feature dịch vụ công phải nêu: quy trình một cửa, các bước duyệt, thời hạn xử lý (SLA pháp định), hồ sơ thành phần.
- Trạng thái hồ sơ phải định nghĩa rõ (tiếp nhận/đang xử lý/yêu cầu bổ sung/trả kết quả/từ chối) + thông báo công dân.
- Phân quyền theo vai trò/cấp đơn vị, có ủy quyền và ghi vết đầy đủ.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa quy trình/thời hạn pháp định; thiếu nguồn → `[CẦN XÁC NHẬN]`.
- Quy định (Luật, Nghị định, Thông tư, quy chế đơn vị, định danh điện tử) phải trích nguồn từ `docs/01-domain/`.
- Dữ liệu công dân là nhạy cảm: mọi feature nêu cách xử lý quyền riêng tư + lưu trữ theo quy định.
- Tuân thủ chuẩn kết nối/khả năng tiếp cận (accessibility) nếu phục vụ người dân.

### 4. Design Rules
- Ngôn ngữ chính xác, trung lập, dễ hiểu cho người dân; tránh thuật ngữ kỹ thuật khó.
- Trạng thái hồ sơ/biểu mẫu rõ ràng; đáp ứng accessibility (tương phản, cỡ chữ, đọc màn hình).

### 5. Code Rules
- Không hardcode thời hạn/quy trình; phải cấu hình theo văn bản. Mọi hành động có audit trail.
- Log không chứa định danh công dân (CCCD…) ở dạng rõ khi không cần.

### 6. Rule tài liệu & ngôn ngữ
- URD/SRS theo mẫu cơ quan; mọi tài liệu có mục "Căn cứ pháp lý" + "Rủi ro & câu hỏi cần xác nhận".
