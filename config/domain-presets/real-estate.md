# Domain Preset — Real-estate / Bất động sản

### 1. Thuật ngữ & quy ước
- Thuật ngữ BĐS kèm giải thích VN trong glossary (vd dự án, phân khu, căn/lô, giỏ hàng, đặt cọc, hợp đồng mua bán/HĐMB, sổ).
- Phân biệt rõ khách hàng, môi giới/sàn, chủ đầu tư, giao dịch.

### 2. Rule phân tích nghiệp vụ
- Mỗi feature phải nêu vòng đời giao dịch: giữ chỗ → đặt cọc → ký HĐMB → thanh toán theo tiến độ → bàn giao.
- Quản lý giỏ hàng/căn phải tránh bán trùng (locking khi giữ chỗ), trạng thái căn rõ ràng.
- Chính sách bán hàng (chiết khấu, tiến độ thanh toán, khuyến mãi) phải nêu điều kiện áp dụng.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa giá/chính sách/pháp lý dự án; thiếu nguồn → `[CẦN XÁC NHẬN]`.
- Quy định (Luật Đất đai, Luật Kinh doanh BĐS, điều kiện mở bán) phải trích nguồn từ `docs/01-domain/`.
- Giao dịch tiền (cọc, thanh toán) phải nêu đối soát + ghi vết; thông tin pháp lý phải có nguồn.

### 4. Design Rules
- Sơ đồ căn/giỏ hàng hiển thị trạng thái rõ (còn/giữ chỗ/đã bán) phân biệt màu; tránh hiểu nhầm còn-hàng.
- Mock giá/chính sách ghi chú "dữ liệu minh họa".

### 5. Code Rules
- Giữ chỗ/đặt cọc phải có cơ chế khóa chống bán trùng (concurrency); không hardcode giá/chính sách.
- Log không chứa thông tin khách/định danh ở dạng rõ khi không cần.

### 6. Rule tài liệu & ngôn ngữ
- URD/SRS theo mẫu công ty; mọi tài liệu có mục "Rủi ro & câu hỏi cần xác nhận".
