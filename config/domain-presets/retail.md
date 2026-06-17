# Domain Preset — Retail / Bán hàng & Bán lẻ

### 1. Thuật ngữ & quy ước
- Thuật ngữ bán hàng kèm giải thích: SKU, POS, tồn kho (stock), đơn hàng (order), CK (chiết khấu), GMV, AOV.

### 2. Rule phân tích nghiệp vụ
- Mỗi feature đụng tới giá/khuyến mãi/tồn kho phải nêu: nguồn giá, quy tắc làm tròn, đồng bộ tồn kho đa kênh.
- Phân biệt rõ "đơn online" và "đơn tại quầy (POS)"; nêu luồng hoàn / đổi / hủy.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa quy tắc thuế / hóa đơn (VAT, hóa đơn điện tử) → `[CẦN XÁC NHẬN]`; trích nguồn từ `docs/01-domain/`.
- Tiền tệ/giá: rõ đơn vị, làm tròn, khuyến mãi chồng nhau — tránh sai số tài chính.

### 4. Design Rules
- Luồng thanh toán tối thiểu số bước; trạng thái đơn rõ ràng; lỗi tồn kho/giá phải báo trước khi đặt.

### 5. Code Rules
- Không hardcode giá/thuế/CK; phải cấu hình + có nguồn. Tạo đơn idempotent (tránh trùng đơn).
- Log không chứa thông tin thanh toán nhạy cảm (số thẻ, CVV).

### 6. Rule tài liệu & ngôn ngữ
- Mỗi tài liệu có mục "Rủi ro & câu hỏi cần xác nhận"; nêu rõ kênh bán (online / POS / marketplace).
