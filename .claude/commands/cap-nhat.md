---
description: Cập nhật ỨNG DỤNG lên bản mới nhất, giữ nguyên tri thức (workflows/10)
---

Người dùng vừa CHỦ ĐỘNG gõ `/cap-nhat` — đây là **lệnh rõ ràng** = cập nhật CHƯƠNG TRÌNH
(app) lên bản phát hành mới nhất, GIỮ NGUYÊN toàn bộ tri thức.

TUYỆT ĐỐI KHÔNG hỏi "bạn muốn cập nhật cái gì". Đọc và thực thi thẳng `workflows/10-update.md`
theo `CLAUDE.md`:

- WF10 tự so `version.json` local với bản trên GitHub; nếu có bản mới → hiện `intro` + tóm tắt
  CHANGELOG + cách nâng cấp.
- ✋ WF10 tự confirm trước khi tải/ghi đè; `scripts/update.command` CHỈ thay CORE, **KHÔNG đụng
  DATA** (docs/, vault, config, .env.local).
