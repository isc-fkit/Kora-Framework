---
description: Khởi tạo AI Product Factory — chạy workflows/00-setup.md từng bước (cài đặt 1 lần)
---

Người dùng vừa CHỦ ĐỘNG gõ lệnh `/kora-khoi-tao` — đây là **lệnh rõ ràng** để khởi tạo dự án
(tương đương "@khởi tạo dự án"). KHÔNG cần hỏi lại "bạn muốn chạy hay chỉ hỏi thông tin".

Hãy đọc và thực thi `workflows/00-setup.md` theo đúng `CLAUDE.md`:

- Chạy **từng bước MỘT**, mỗi bước DỪNG hỏi user (AskUserQuestion hoặc câu thường) rồi mới
  sang bước kế.
- TUYỆT ĐỐI không tự chọn thay user, không chạy lướt nhiều bước liền nhau.
- Tuân thủ Approval Gate: trình bày "sẽ làm gì" → chờ user đồng ý mới làm.
- Nếu thiếu `config/factory-config.yaml` → copy từ `config/factory-config.example.yaml` rồi điền.
