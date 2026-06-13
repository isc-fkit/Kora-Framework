# Domain Preset — Fintech

### 1. Thuật ngữ & quy ước
- Thuật ngữ tài chính (KYC, AML, settlement...) phải vào glossary kèm giải thích.

### 2. Rule phân tích nghiệp vụ
- Feature liên quan tiền phải nêu: luồng tiền, đối soát, rollback khi lỗi, hạn mức.
- Mọi giao dịch phải có trạng thái trung gian (pending) và luồng xử lý timeout.

### 3. Rule thận trọng
- Không bịa quy định pháp lý (NHNN, PCI-DSS...). Thiếu nguồn → `[CẦN XÁC NHẬN PHÁP LÝ]`.
- Không tự đặt phí, hạn mức, lãi suất.

### 4. Design Rules
- Luồng giao dịch phải có bước xác nhận + biên lai; số tiền hiển thị nhất quán định dạng.
- Trạng thái lỗi giao dịch phải nói rõ tiền có bị trừ không.

### 5. Code Rules
- Số tiền dùng kiểu chính xác (không float). Không log thông tin thẻ/tài khoản.

### 6. Rule tài liệu & ngôn ngữ
- Tài liệu có mục "Rủi ro tài chính & tuân thủ".
