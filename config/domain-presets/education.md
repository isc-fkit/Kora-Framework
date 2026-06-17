# Domain Preset — Education / Giáo dục

### 1. Thuật ngữ & quy ước
- Thuật ngữ giáo dục kèm giải thích: LMS, khóa học (course), lớp (class), điểm danh, học liệu, đánh giá (assessment).

### 2. Rule phân tích nghiệp vụ
- Feature đụng tới điểm/đánh giá phải nêu: thang điểm, quy tắc tính, quyền sửa, lịch sử thay đổi.
- Phân biệt vai trò: học viên / giảng viên / phụ huynh / quản trị — quyền xem khác nhau.

### 3. Rule thận trọng (BẮT BUỘC)
- Dữ liệu trẻ vị thành niên là nhạy cảm: nêu rõ đồng thuận phụ huynh + quyền riêng tư.
- KHÔNG tự bịa quy chế thi / đào tạo → `[CẦN XÁC NHẬN]`; trích nguồn từ `docs/01-domain/`.

### 4. Design Rules
- Giao diện phù hợp lứa tuổi; học liệu rõ trạng thái (nháp / đã duyệt / đã xuất bản).

### 5. Code Rules
- Không hardcode thang điểm / quy tắc xếp loại; cấu hình + có nguồn. Log không chứa dữ liệu định danh học viên.

### 6. Rule tài liệu & ngôn ngữ
- Tài liệu có mục "Rủi ro & câu hỏi cần xác nhận".
