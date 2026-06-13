# Domain Preset — Healthcare / Y tế

### 1. Thuật ngữ & quy ước
- Thuật ngữ y khoa phải kèm giải thích tiếng Việt trong glossary (vd CGM, SpO2, HbA1c).

### 2. Rule phân tích nghiệp vụ
- Mỗi feature liên quan dữ liệu sức khỏe phải nêu rõ: nguồn dữ liệu, tần suất, quyền truy cập, luồng cảnh báo.
- Phân biệt rõ "hiển thị thông tin" và "tư vấn y tế" — app không được chẩn đoán thay bác sĩ.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa ngưỡng lâm sàng (đường huyết, huyết áp...). Thiếu nguồn chuyên môn → `[CẦN XÁC NHẬN CHUYÊN MÔN]`.
- Quy định pháp lý (Nghị định, HIPAA, GDPR...) phải trích nguồn từ `docs/01-domain/`.
- Dữ liệu sức khỏe là dữ liệu nhạy cảm: mọi feature phải nêu cách xử lý quyền riêng tư.

### 4. Design Rules
- Mock data trong prototype không được dùng số liệu lâm sàng bịa như thật; ghi chú "dữ liệu minh họa".
- Cảnh báo sức khỏe: màu/icon phải phân biệt mức độ, có trạng thái "thiết bị mất kết nối".

### 5. Code Rules
- Không hardcode ngưỡng y tế; ngưỡng phải cấu hình được và có nguồn.
- Log không chứa dữ liệu sức khỏe định danh.

### 6. Rule tài liệu & ngôn ngữ
- URD/SRS theo mẫu biểu công ty nếu có; mọi tài liệu có mục "Rủi ro & câu hỏi cần xác nhận".
