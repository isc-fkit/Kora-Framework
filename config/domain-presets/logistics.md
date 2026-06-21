# Domain Preset — Logistics / Chuỗi cung ứng

### 1. Thuật ngữ & quy ước
- Thuật ngữ logistics kèm giải thích VN trong glossary (vd SKU, lô/batch, vận đơn/AWB, tracking, tồn kho, ETA).
- Phân biệt rõ đơn hàng, kiện hàng, chuyến/tuyến, kho/điểm giao.

### 2. Rule phân tích nghiệp vụ
- Mỗi feature phải nêu vòng đời đơn/kiện: tạo → lấy hàng → vận chuyển → giao → đối soát COD.
- Trạng thái và sự kiện tracking phải định nghĩa rõ (timestamp, vị trí, lý do thất bại, giao lại).
- Tồn kho phải nêu cơ chế cập nhật (nhập/xuất/điều chuyển), tránh âm kho, đối soát định kỳ.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa biểu cước vận chuyển/ETA/thời gian giao; thiếu nguồn → `[CẦN XÁC NHẬN]`.
- Quy định vận chuyển (hàng nguy hiểm, hải quan, hóa đơn) phải trích nguồn từ `docs/01-domain/`.
- COD liên quan tiền: mọi luồng phải nêu đối soát + ghi vết.

### 4. Design Rules
- Màn hình tracking phải hiện trạng thái + mốc thời gian rõ; trạng thái lỗi/giao thất bại phân biệt màu+icon.
- Mock số liệu tracking/tồn kho ghi chú "dữ liệu minh họa".

### 5. Code Rules
- Không hardcode biểu cước/định mức; phải cấu hình được. Cập nhật tồn kho phải nhất quán (tránh race/âm kho).
- Log không chứa thông tin người nhận đầy đủ ở dạng rõ khi không cần.

### 6. Rule tài liệu & ngôn ngữ
- URD/SRS theo mẫu công ty; mọi tài liệu có mục "Rủi ro & câu hỏi cần xác nhận".
