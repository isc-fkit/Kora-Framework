---
description: Quét 1 task/epic Jira theo mã — vd /kora-quet-task PROJ-102
argument-hint: <JIRA-KEY> (vd PROJ-102)
---

Người dùng vừa CHỦ ĐỘNG gõ `/kora-quet-task $ARGUMENTS` — đây là **lệnh rõ ràng** để quét một
task/epic Jira theo mã.

Mã issue cần quét: **$ARGUMENTS**

- Nếu phần mã ở trên TRỐNG → hỏi user nhập mã issue (AskUserQuestion: vài gợi ý + ô "Other"
  để gõ mã thật), KHÔNG tự bịa mã.
- Khi đã có mã → đọc và thực thi `workflows/01b-import-jira-single.md` theo `CLAUDE.md` cho
  đúng mã đó.
- Giữ nguyên Approval Gate + bảo mật token (.env.local, xóa sau khi dùng).
