# Domain Preset — E-commerce

### 1. Thuật ngữ & quy ước
- Thuật ngữ (SKU, fulfillment, COD...) vào glossary.

### 2. Rule phân tích nghiệp vụ
- Feature phải nêu tác động lên: giỏ hàng, đơn hàng, tồn kho, khuyến mãi, vận chuyển.
- Luồng đặt hàng phải xử lý: hết hàng giữa chừng, thay đổi giá, hủy/hoàn.

### 3. Rule thận trọng
- Không tự đặt chính sách giá/khuyến mãi/hoàn trả. Thiếu nguồn → `[CẦN XÁC NHẬN]`.

### 4. Design Rules
- Trạng thái đơn hàng phải có timeline rõ; giỏ hàng rỗng/hết hàng phải có empty state.

### 5. Code Rules
- Tồn kho và giá xử lý transaction-safe; không sửa code khi chưa có BR/AC duyệt.

### 6. Rule tài liệu & ngôn ngữ
- Tài liệu có mục "Tác động vận hành (kho, CSKH, vận chuyển)".
