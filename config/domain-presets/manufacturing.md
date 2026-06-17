# Domain Preset — Manufacturing / Sản xuất & Điện tử

### 1. Thuật ngữ & quy ước
- Thuật ngữ sản xuất kèm giải thích: BOM, MES, OEE, lô (batch/lot), QC/QA, truy xuất (traceability), serial.

### 2. Rule phân tích nghiệp vụ
- Feature đụng dây chuyền/thiết bị phải nêu: trạng thái máy, lỗi/cảnh báo, dữ liệu cảm biến, tần suất.
- Truy xuất nguồn gốc theo lô/serial là BẮT BUỘC cho khâu chất lượng.

### 3. Rule thận trọng (BẮT BUỘC)
- KHÔNG tự bịa ngưỡng kỹ thuật / an toàn (nhiệt độ, dung sai, điện áp) → `[CẦN XÁC NHẬN CHUYÊN MÔN]`.
- Tiêu chuẩn (IPC, ISO, IEC...) phải trích nguồn từ `docs/01-domain/`.

### 4. Design Rules
- Dashboard vận hành: phân biệt mức cảnh báo, có trạng thái "mất kết nối thiết bị"; tối ưu cho màn nhà xưởng.

### 5. Code Rules
- Không hardcode ngưỡng/dung sai; cấu hình + có nguồn. Dữ liệu cảm biến gắn timestamp + đơn vị.

### 6. Rule tài liệu & ngôn ngữ
- Tài liệu có mục "Rủi ro & câu hỏi cần xác nhận"; nêu rõ tiêu chuẩn áp dụng.
