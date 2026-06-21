# Domain Preset — Telecom / Viễn thông

### 1. Thuật ngữ & quy ước
- Thuật ngữ viễn thông kèm giải thích VN trong glossary (vd OLT, ONU, FTTH, SLA, MSISDN, IMSI, KPI mạng).
- Phân biệt rõ thuê bao (subscriber), gói cước (plan), dịch vụ giá trị gia tăng (VAS).

### 2. Rule phân tích nghiệp vụ
- Mỗi feature liên quan thuê bao/cước phải nêu: vòng đời thuê bao, trạng thái (active/suspend/terminate), tính cước (prepaid/postpaid).
- Quy trình tính cước (rating/billing) phải nêu rõ chu kỳ, proration, thuế, khuyến mãi chồng lấn.
- SLA/chất lượng dịch vụ: nêu chỉ tiêu (uptime, độ trễ, mất gói) và cách đo.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa biểu cước/chỉ tiêu SLA; thiếu nguồn → `[CẦN XÁC NHẬN]`.
- Quy định viễn thông (giấy phép, quản lý thuê bao, eKYC, lưu trữ CDR) phải trích nguồn từ `docs/01-domain/`.
- Dữ liệu cuộc gọi/định vị (CDR, location) là nhạy cảm: mọi feature phải nêu cách xử lý quyền riêng tư & thời hạn lưu.

### 4. Design Rules
- Màn hình trạng thái dịch vụ/sự cố phải có mức độ (bình thường/cảnh báo/mất kết nối) phân biệt màu+icon.
- Mock số liệu mạng/cước không dùng số "thật" gây hiểu nhầm; ghi chú "dữ liệu minh họa".

### 5. Code Rules
- Không hardcode biểu cước/ngưỡng SLA; phải cấu hình được và có nguồn.
- Log không chứa MSISDN/IMSI/định danh thuê bao ở dạng rõ; che/mask khi cần.

### 6. Rule tài liệu & ngôn ngữ
- URD/SRS theo mẫu công ty; mọi tài liệu có mục "Rủi ro & câu hỏi cần xác nhận".
