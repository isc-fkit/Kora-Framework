# Domain Preset — Insurance / Bảo hiểm

### 1. Thuật ngữ & quy ước
- Thuật ngữ bảo hiểm kèm giải thích VN trong glossary (vd hợp đồng/policy, phí/premium, quyền lợi, bồi thường/claim, loại trừ).
- Phân biệt rõ chủ hợp đồng, người được bảo hiểm, người thụ hưởng.

### 2. Rule phân tích nghiệp vụ
- Mỗi feature phải nêu vòng đời hợp đồng: chào phí → phát hành → đóng phí → yêu cầu bồi thường → tất toán.
- Quy tắc thẩm định (underwriting) và bồi thường (claim) phải nêu điều kiện, loại trừ, hồ sơ cần.
- Tính phí phải nêu yếu tố rủi ro, biểu phí, kỳ đóng, gia hạn/khôi phục hiệu lực.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa biểu phí/điều khoản/điều kiện loại trừ; thiếu nguồn → `[CẦN XÁC NHẬN]`.
- Quy định (Luật KDBH, thông tư, quy tắc sản phẩm đã duyệt) phải trích nguồn từ `docs/01-domain/`.
- Dữ liệu sức khỏe/tài chính của khách là nhạy cảm: mọi feature phải nêu cách xử lý quyền riêng tư.

### 4. Design Rules
- Màn hình quyền lợi/loại trừ phải rõ ràng, không gây hiểu nhầm phạm vi bảo hiểm.
- Mock số liệu phí/quyền lợi ghi chú "dữ liệu minh họa".

### 5. Code Rules
- Không hardcode biểu phí/quy tắc thẩm định; phải cấu hình được và có nguồn/phiên bản.
- Log không chứa thông tin sức khỏe/định danh khách ở dạng rõ.

### 6. Rule tài liệu & ngôn ngữ
- URD/SRS theo mẫu công ty; mọi tài liệu có mục "Rủi ro & câu hỏi cần xác nhận".
