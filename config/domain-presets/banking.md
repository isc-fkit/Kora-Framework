# Domain Preset — Banking / Ngân hàng

### 1. Thuật ngữ & quy ước
- Thuật ngữ ngân hàng kèm giải thích VN trong glossary (vd KYC, AML, CASA, hạn mức, sao kê, đối soát).
- Phân biệt rõ tài khoản, giao dịch, hạn mức, sản phẩm tín dụng (vay/thẻ).

### 2. Rule phân tích nghiệp vụ
- Mỗi feature giao dịch tiền phải nêu: hạn mức, xác thực (OTP/sinh trắc), đối soát, hoàn/hủy, idempotency.
- Luồng tiền phải nêu trạng thái giao dịch (pending/success/failed/reversed) và xử lý lỗi/timeout.
- Tính lãi/phí phải nêu công thức, chu kỳ, làm tròn, ngày giá trị.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa lãi suất/phí/hạn mức; thiếu nguồn → `[CẦN XÁC NHẬN]`.
- Quy định (Luật các TCTD, Thông tư NHNN, AML/KYC, PCI-DSS) phải trích nguồn từ `docs/01-domain/`.
- KHÔNG đưa lời khuyên đầu tư/tài chính cá nhân; chỉ mô tả nghiệp vụ.
- Mọi thao tác chuyển/giao dịch tiền phải có xác thực + ghi vết kiểm toán (audit trail).

### 4. Design Rules
- Màn hình giao dịch phải hiện rõ số tiền, phí, người nhận, và bước xác nhận TRƯỚC khi thực hiện.
- Mock số dư/giao dịch ghi chú "dữ liệu minh họa"; không dùng số tài khoản thật.

### 5. Code Rules
- Giao dịch tiền phải idempotent (idempotency key); không hardcode phí/lãi/hạn mức.
- Log KHÔNG chứa số thẻ/CVV/số tài khoản đầy đủ/OTP; mask theo PCI-DSS.

### 6. Rule tài liệu & ngôn ngữ
- URD/SRS theo mẫu công ty; mọi tài liệu có mục "Rủi ro & câu hỏi cần xác nhận" + mục tuân thủ/compliance.
