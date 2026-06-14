# Claude Code Setup Guide — Jira → Obsidian Knowledge Base

> Mục tiêu: giúp Claude Code hiểu và thực thi từ **Bước 1 đến Bước 7** để tạo một tool local quét Jira và chuyển dữ liệu thành Obsidian Vault có backlink + relation graph.

---

## 0. Vai trò của file này

File này dùng cho Claude Code khi mở project local `jira-to-obsidian`.

Claude Code cần đọc file này trước khi:
- tạo script import Jira;
- kiểm tra cấu trúc folder;
- chỉnh lỗi kết nối Jira API;
- chuẩn hóa dữ liệu Jira;
- sinh Markdown cho Obsidian;
- tạo `relation-graph.json`;
- tạo `source-registry.json`.

---

## 1. Nguyên tắc bảo mật bắt buộc

### 1.1 Không dùng password Jira

Không được dùng password Jira trong code, markdown, Obsidian hoặc Git.

Chỉ dùng:

```env
JIRA_PAT=...
```

Trong đó `JIRA_PAT` là Jira Personal Access Token.

### 1.2 Không commit token

File chứa token phải là:

```text
.env.local
```

File này bắt buộc nằm trong `.gitignore`.

### 1.3 Nếu token từng bị paste ra ngoài

Phải xem token đó là đã lộ.

Quy trình:
1. Thu hồi token cũ trong Jira.
2. Tạo token mới.
3. Chỉ lưu token mới trong `.env.local`.
4. Không paste token vào Claude / ChatGPT / Git / Obsidian.

---

## 2. Bước 1 — Môi trường (KHÔNG cần cài gì)

Script `import_jira.py` đã nằm sẵn trong `tools/jira-to-obsidian/` và **chỉ dùng thư viện
chuẩn Python 3** — **KHÔNG cần tạo venv, KHÔNG cần `pip install`** (requests/python-dotenv
không dùng tới). Chỉ cần máy có Python 3:

```bash
python3 --version   # macOS/Linux
py --version        # Windows
```

Chưa có Python → cài theo OS (macOS: `brew install python3` hoặc python.org;
Windows: Microsoft Store / python.org, tick "Add to PATH").

---

## 3. Bước 2 — Tạo file `.env.local`

Tạo file:

```bash
touch .env.local
```

Nội dung mẫu:

```env
JIRA_BASE_URL=https://jira.company.vn
JIRA_PAT=PASTE_TOKEN_MOI_VAO_DAY
OBSIDIAN_VAULT=./Project_Name_Brain

# Nếu để trống thì quét tất cả project account có quyền thấy
PROJECT_KEYS=

# Nếu Jira có custom field Acceptance Criteria / Business Rule thì điền field id
JIRA_AC_FIELD=
JIRA_BR_FIELD=
```

Ý nghĩa biến môi trường:

| Biến | Ý nghĩa |
|---|---|
| `JIRA_BASE_URL` | URL Jira server |
| `JIRA_PAT` | Jira Personal Access Token |
| `OBSIDIAN_VAULT` | Folder output Obsidian Vault |
| `PROJECT_KEYS` | Danh sách project key muốn quét, cách nhau bằng dấu phẩy |
| `JIRA_AC_FIELD` | Custom field chứa Acceptance Criteria nếu có |
| `JIRA_BR_FIELD` | Custom field chứa Business Rules nếu có |

Ví dụ chỉ quét 2 project:

```env
PROJECT_KEYS=PROJ,SHOP
```

---

## 4. Bước 3 — Tạo `.gitignore`

Tạo file `.gitignore`:

```bash
echo ".env.local" > .gitignore
echo ".venv/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "Project_Name_Brain/" >> .gitignore
```

Mục tiêu:
- không đẩy token lên Git;
- không đẩy virtual environment;
- không đẩy output thô nếu chưa review.

---

## 5. Bước 4 — Test kết nối Jira API

Chạy:

```bash
source .env.local

curl -H "Authorization: Bearer $JIRA_PAT" \
  "$JIRA_BASE_URL/rest/api/2/project"
```

Kết quả thành công:

```text
Trả về danh sách project dạng JSON.
```

Lỗi thường gặp:

| Lỗi | Ý nghĩa | Cách xử lý |
|---|---|---|
| `401 Unauthorized` | Token sai, hết hạn hoặc Jira không nhận PAT | Tạo token mới / kiểm tra Jira PAT |
| `403 Forbidden` | Account không có quyền xem project | Cấp quyền Browse Project |
| `404 Not Found` | Sai URL hoặc API path | Kiểm tra `JIRA_BASE_URL` |
| Timeout | Không truy cập được mạng nội bộ | Kiểm tra VPN / LAN / proxy |

---

## 6. Bước 5 — Tạo script `import_jira.py`

Tạo file:

```bash
touch import_jira.py
```

Claude Code cần tạo nội dung script theo yêu cầu sau.

### 6.1 Nhiệm vụ của script

Script phải thực hiện:

1. Đọc biến môi trường từ `.env.local`.
2. Kết nối Jira bằng `Authorization: Bearer $JIRA_PAT`.
3. Lấy danh sách project user có quyền xem.
4. Với mỗi project:
   - quét toàn bộ issue bằng JQL;
   - lấy Epic, Story, Task, Bug, Sub-task;
   - lấy parent;
   - lấy linked issues;
   - lấy comments;
   - lấy attachment metadata;
   - lấy custom field nếu có.
5. Sinh Obsidian Markdown.
6. Tạo backlink giữa Project → Epic → Story → Task/Bug/Sub-task.
7. Tạo `_system/relation-graph.json`.
8. Tạo `_system/source-registry.json`.
9. Tạo `00_Index/Jira-Knowledge-Base.md`.

### 6.2 Cấu trúc output bắt buộc

Sau khi chạy, script phải tạo:

```text
Project_Name_Brain/
  00_Index/
    Jira-Knowledge-Base.md
  01_Projects/
  02_Epics/
  03_UserStories/
  04_Tasks/
  05_Bugs/
  06_SubTasks/
  08_RawIssues/
  09_SourceRegistry/
  _system/
    relation-graph.json
    source-registry.json
```

### 6.3 Chuẩn đặt tên file Markdown

Format:

```text
{JIRA_KEY}_{safe-summary}.md
```

Ví dụ:

```text
PROJ-102_Xin-quyen-Apple-HealthKit.md
```

Tên file phải:
- không chứa ký tự đặc biệt gây lỗi path;
- giữ được tiếng Việt nếu có;
- thay khoảng trắng bằng dấu `-`;
- giới hạn độ dài an toàn.

### 6.4 YAML frontmatter bắt buộc

Mỗi issue note cần có:

```yaml
---
type: user_story
source: jira
jira_key: PROJ-102
jira_issue_type: Story
project: PROJ
status: To Do
parent: PROJ-101
imported_at: 2026-06-13T00:00:00
---
```

### 6.5 Nội dung Markdown cho issue

Mỗi issue note cần có các section:

```markdown
# PROJ-102 — Tên issue

## Metadata

## Description

## Acceptance Criteria Raw

## Business Rule Raw

## Parent

## Linked Issues

## Attachments Metadata

## Comments

## Source
```

Nếu không có dữ liệu section nào thì có thể bỏ section đó.

### 6.6 Relation graph schema

File:

```text
_system/relation-graph.json
```

Schema:

```json
{
  "generated_at": "ISO_DATETIME",
  "nodes": [
    {
      "id": "PROJ-102",
      "type": "user_story",
      "title": "Xin quyền Apple HealthKit",
      "status": "To Do",
      "project": "PROJ"
    }
  ],
  "edges": [
    {
      "from": "PROJ",
      "to": "PROJ-102",
      "relation": "has_issue"
    },
    {
      "from": "PROJ-101",
      "to": "PROJ-102",
      "relation": "parent_of"
    }
  ]
}
```

### 6.7 Source registry schema

File:

```text
_system/source-registry.json
```

Schema:

```json
[
  {
    "source_id": "SRC-JIRA-PROJ-102",
    "source_type": "jira_issue",
    "jira_key": "PROJ-102",
    "project": "PROJ",
    "issue_type": "Story",
    "title": "Xin quyền Apple HealthKit",
    "status": "To Do",
    "imported_at": "ISO_DATETIME"
  }
]
```

---

## 7. Bước 6 — Chạy import

Chạy:

```bash
python import_jira.py
```

Kết quả terminal mong đợi:

```text
Đang lấy danh sách project...
Tìm thấy X project.
Đang quét project PROJ — MyApp
  → 128 issues

Hoàn tất.
Obsidian Vault đã tạo tại: /path/to/Project_Name_Brain
```

Nếu lỗi API:
- in rõ status code;
- in tối đa 500 ký tự response;
- không in token;
- không ghi token vào log.

---

## 8. Bước 7 — Mở output bằng Obsidian

Mở Obsidian:

```text
Open folder as vault
```

Chọn folder:

```text
jira-to-obsidian/Project_Name_Brain
```

Mở file index:

```text
00_Index/Jira-Knowledge-Base.md
```

Kiểm tra:
- các project đã được tạo note;
- epic có link đến story;
- story có link đến parent;
- linked issue có backlink;
- `_system/relation-graph.json` tồn tại;
- `_system/source-registry.json` tồn tại.

---

## 9. Tiêu chí hoàn thành Bước 1 → Bước 7

Hoàn thành khi có đủ:

```text
[ ] `.env.local` tồn tại nhưng không bị commit
[ ] Kết nối Jira API thành công
[ ] Script `import_jira.py` chạy được
[ ] Obsidian Vault được tạo
[ ] Có note Project
[ ] Có note Epic
[ ] Có note Story / Task / Bug / Sub-task
[ ] Có backlink giữa các issue
[ ] Có `relation-graph.json`
[ ] Có `source-registry.json`
[ ] Có `00_Index/Jira-Knowledge-Base.md`
```

---

## 10. Những gì chưa làm ở bước này

Bước 1 → Bước 7 chỉ tạo **raw Obsidian Knowledge Base từ Jira**.

Chưa làm:
- chưa tạo PRD;
- chưa tạo SRS;
- chưa tạo URD;
- chưa tạo Business Rule chính thức;
- chưa tạo Acceptance Criteria chuẩn hóa;
- chưa chạy Claude Design;
- chưa sửa source code;
- chưa export DOCX/PDF.

Các bước đó chỉ được thực hiện sau khi:
1. Claude phân tích raw KB;
2. user review;
3. user approve;
4. mới promote vào Knowledge Base chính.

---

## 11. Workflow tiếp theo sau Bước 7

Sau khi mở được Obsidian Vault:

```text
Raw Jira Import
↓
Claude đọc vault
↓
Claude phân loại thành Feature / Requirement / BR / AC
↓
User approve
↓
Ghi vào Knowledge Base chính
↓
Export DOCX/PDF
↓
Generate Claude Design Prompt
↓
Claude Design tạo workflow / wireframe / prototype
↓
Claude Code tạo implementation plan
```

---

## 12. Instruction riêng cho Claude Code

Khi làm việc trên repo này, Claude Code phải tuân thủ:

1. Không hỏi user cung cấp password.
2. Không in token ra terminal.
3. Không ghi token vào file log.
4. Không sửa `.env.local` trừ khi user yêu cầu.
5. Không commit output raw nếu user chưa duyệt.
6. Nếu Jira API lỗi, báo rõ lỗi và gợi ý kiểm tra quyền.
7. Nếu thiếu custom field Acceptance Criteria, vẫn import description/comment raw.
8. Nếu không xác định được Epic/Parent, giữ issue trong `08_RawIssues`.
9. Không tự suy diễn Business Rule chính thức từ Jira raw trong bước import.
10. Chỉ tạo raw Obsidian KB ở bước này.

---

## 13. Prompt ngắn để chạy trong Claude Code

User có thể mở Claude Code trong folder `jira-to-obsidian` và dùng prompt:

```text
Hãy đọc file CLAUDE_CODE_JIRA_TO_OBSIDIAN_SETUP.md và thực hiện từ Bước 1 đến Bước 7. 
Mục tiêu là tạo script local import Jira sang Obsidian Vault.
Không được dùng password Jira, chỉ dùng JIRA_PAT từ .env.local.
Không được in token ra log.
Sau khi chạy xong, kiểm tra output gồm Markdown notes, relation-graph.json và source-registry.json.
```
