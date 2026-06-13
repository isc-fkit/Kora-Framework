# Domain Preset — Generic

### 1. Thuật ngữ & quy ước
- Dùng thuật ngữ do user cung cấp; mọi thuật ngữ mới phải vào `docs/08-glossary/`.

### 2. Rule phân tích nghiệp vụ
- Mỗi feature phải có: mục tiêu, đối tượng, luồng chính, rule, tiêu chí nghiệm thu.
- Yêu cầu mơ hồ → đặt câu hỏi `[CẦN XÁC NHẬN]`, không tự đoán.

### 3. Rule thận trọng
- Không bịa số liệu, ngưỡng, quy định pháp lý. Thiếu nguồn → `[CẦN XÁC NHẬN]`.

### 4. Design Rules
- Prototype phải có đủ trạng thái: bình thường / rỗng / lỗi / loading.
- Màn hình mới phải liên kết điều hướng với màn hình hiện có liên quan.

### 5. Code Rules
- Không sửa code khi chưa có BR/AC được duyệt (Gate 4).

### 6. Rule tài liệu & ngôn ngữ
- Tài liệu cho người đọc: tiếng Việt chuẩn, không jargon. Context cho Claude: có ID, metadata, related links.
