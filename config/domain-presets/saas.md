# Domain Preset — SaaS / Phần mềm B2B

### 1. Thuật ngữ & quy ước
- Thuật ngữ SaaS kèm giải thích VN trong glossary (vd tenant, subscription, seat, MRR/ARR, churn, SLA, webhook).
- Phân biệt rõ tổ chức (tenant), người dùng, vai trò, gói (plan/tier).

### 2. Rule phân tích nghiệp vụ
- Mỗi feature phải nêu mô hình multi-tenant: cô lập dữ liệu giữa tenant, phân quyền RBAC, giới hạn theo gói.
- Vòng đời subscription: dùng thử → mua → gia hạn → nâng/hạ cấp → hủy; nêu proration & hóa đơn.
- Tích hợp (API/webhook/SSO) phải nêu xác thực, idempotency, rate limit, versioning.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa giá gói/giới hạn/SLA; thiếu nguồn → `[CẦN XÁC NHẬN]`.
- Tuân thủ dữ liệu (GDPR/Nghị định 13, data residency, audit log) phải trích nguồn từ `docs/01-domain/`.
- Cô lập tenant là BẮT BUỘC: mọi truy vấn/feature phải nêu cách chặn rò rỉ dữ liệu chéo tenant.

### 4. Design Rules
- Phân biệt rõ ngữ cảnh tenant đang thao tác; hành động phá hủy (xóa/hủy gói) phải có xác nhận.
- Mock số liệu sử dụng/billing ghi chú "dữ liệu minh họa".

### 5. Code Rules
- Mọi truy vấn dữ liệu phải gắn tenant_id (không truy vấn xuyên tenant); không hardcode giới hạn gói.
- API key/secret/token chỉ ở biến môi trường; log không chứa secret.

### 6. Rule tài liệu & ngôn ngữ
- URD/SRS theo mẫu công ty; mọi tài liệu có mục "Rủi ro & câu hỏi cần xác nhận" + mục tuân thủ dữ liệu.
