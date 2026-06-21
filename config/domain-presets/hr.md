# Domain Preset — HR / Nhân sự

### 1. Thuật ngữ & quy ước
- Thuật ngữ nhân sự kèm giải thích VN trong glossary (vd onboarding, payroll, chấm công, OT, KPI/OKR, nghỉ phép).
- Phân biệt rõ nhân viên, phòng ban, chức danh, hợp đồng lao động.

### 2. Rule phân tích nghiệp vụ
- Mỗi feature phải nêu vòng đời nhân viên: tuyển → onboarding → đánh giá → điều chuyển → nghỉ việc.
- Chấm công/tính lương phải nêu công thức, kỳ lương, OT, phụ cấp, thuế TNCN, bảo hiểm, làm tròn.
- Quy trình duyệt (nghỉ phép, OT, chi phí) phải nêu cấp duyệt và SLA.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa công thức lương/thuế/bảo hiểm; thiếu nguồn → `[CẦN XÁC NHẬN]`.
- Quy định (Bộ luật Lao động, BHXH, thuế TNCN, nội quy công ty) phải trích nguồn từ `docs/01-domain/`.
- Dữ liệu nhân sự (lương, đánh giá, sức khỏe) là nhạy cảm: nêu cách xử lý quyền riêng tư + phân quyền chặt.

### 4. Design Rules
- Màn hình lương/đánh giá chỉ hiển thị cho người có quyền; che thông tin nhạy cảm theo vai trò.
- Mock số liệu lương/đánh giá ghi chú "dữ liệu minh họa".

### 5. Code Rules
- Không hardcode công thức lương/thuế/phụ cấp; phải cấu hình được và có nguồn.
- Log không chứa lương/đánh giá/định danh nhân viên ở dạng rõ.

### 6. Rule tài liệu & ngôn ngữ
- URD/SRS theo mẫu công ty; mọi tài liệu có mục "Rủi ro & câu hỏi cần xác nhận".
