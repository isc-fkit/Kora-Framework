# Workflow 01 — Import Jira → Obsidian (tự động hoàn toàn)

> Spec gốc: `tools/jira-to-obsidian/CLAUDE_CODE_JIRA_TO_OBSIDIAN_SETUP.md` (Bước 1→7).
> Script đã viết sẵn: `tools/jira-to-obsidian/import_jira.py` — KHÔNG cần viết lại,
> chỉ cấu hình và chạy. Muốn quét RIÊNG 1 vài issue → dùng `workflows/01b-import-jira-single.md`.

## Bước 1 — Kiểm tra môi trường

Script chỉ dùng **thư viện chuẩn Python 3** — KHÔNG cần venv, KHÔNG cần pip install.
Chỉ cần kiểm tra máy có Python 3: `python3 --version` (Windows: `py --version`).
Chưa có → hướng dẫn cài theo OS.

## Bước 2 — Cấu hình `.env.local` (tự động + user chỉ điền token)

1. **Tự kiểm tra** `.env.local`: chưa có → tự copy từ `.env.example` tạo mới.
2. Hỏi các giá trị KHÔNG nhạy cảm ngay trong chat (URL Jira, project keys) →
   Claude tự điền vào `.env.local`. `OBSIDIAN_VAULT` tự đặt theo `vault_path`
   trong `config/factory-config.yaml`.
3. **Xác định loại Jira** (quyết định cách lấy token) — nhìn URL hoặc hỏi user:

   - **Jira Cloud / Atlassian** (`https://<tên>.atlassian.net`): cần **email + API token**.
     Điền `JIRA_EMAIL` = email tài khoản. Hướng dẫn tạo token:
     > avatar (góc phải trên) → **Account settings** → tab **Security** →
     > **Create and manage API tokens** → **Create API token** → đặt tên → copy.
     > (Link nhanh: https://id.atlassian.com/manage-profile/security/api-tokens)
   - **Jira Server / Data Center** (tự host, vd `https://jira.fptmedicare.vn`): chỉ cần **PAT**.
     > avatar → **Profile** → **Personal Access Tokens** → **Create token** → copy.

   Hỏi: "Bạn đã có token chưa?" — Chưa → hướng dẫn theo loại ở trên; Có → sang bước 4.
   `JIRA_AUTH_MODE=auto` tự nhận diện, không cần user chọn thủ công.

4. **Mở file cho user tự điền**: present file `.env.local` (card bấm mở được) +
   hướng dẫn: "Mở file, dán token vào dòng `JIRA_PAT=`, lưu lại (Cmd+S)."
   Tuyệt đối KHÔNG yêu cầu dán token vào chat. Nếu user lỡ dán vào chat → coi như
   token đã lộ: hướng dẫn thu hồi trong Jira, tạo token mới, điền lại vào file.
5. Hỏi xác nhận:

   > "Bạn đã điền token và lưu file chưa?"
   > - [A] Rồi → kiểm tra `JIRA_PAT` trong file khác rỗng/khác placeholder
   >   (chỉ kiểm tra, KHÔNG in giá trị ra chat) → sang Bước 3
   > - [B] Chưa / cần trợ giúp → hỗ trợ rồi hỏi lại

   Nếu token vẫn là `PASTE_TOKEN_MOI_VAO_DAY` hoặc rỗng → báo nhẹ nhàng
   "file chưa được lưu hoặc chưa điền" và quay lại bước 4.

## Bước 3 — Test kết nối (dynamic theo môi trường — KHÔNG giả định)

> **Nguyên tắc: thử thật rồi mới kết luận, mọi lệnh sinh ra phải khớp máy/OS của user.**
>
> 1. **Luôn thử trong sandbox trước**: `python3 import_jira.py --test`.
>    `--test` tự làm 2 việc theo thứ tự: (a) gọi `/rest/api/2/myself` xác thực token
>    và in tên user Jira (không in token); (b) lấy danh sách project thấy được.
>    Tương đương 2 lệnh curl /myself + /project nhưng gộp sẵn — KHÔNG cần chạy curl riêng.
>    Jira public/cloud thường chạy được → tự động hoàn toàn, không phiền user.
> 2. Sandbox lỗi mạng (timeout / DNS / bị chặn) → KHÔNG retry vô ích, KHÔNG kết luận
>    "Jira hỏng". Giải thích: sandbox của Claude có thể không ra được domain này dù
>    domain public. Chuyển sang **chế độ user tự chạy**.
> 3. **Sinh lệnh theo OS của user** (xác định từ context phiên làm việc; không chắc
>    thì hỏi 1 câu: macOS / Windows / Linux). Điền `<TOOL_DIR>` = đường dẫn tuyệt đối
>    thật của `tools/jira-to-obsidian` lấy từ project hiện tại — không viết cứng:
>
>    **macOS / Linux:**
>    ```bash
>    cd "<TOOL_DIR>"
>    python3 import_jira.py --test
>    ```
>
>    **Windows (PowerShell):**
>    ```powershell
>    cd "<TOOL_DIR>"
>    py import_jira.py --test
>    ```
>
>    Nếu máy user không có Python → hướng dẫn cài theo OS (macOS: `brew install python3`
>    hoặc python.org; Windows: Microsoft Store / python.org, tick "Add to PATH").
> 4. User dán kết quả (danh sách project) vào chat → Claude tiếp tục như thường.

- Thành công: danh sách project user thấy được → hỏi user muốn quét project nào
  (cập nhật `PROJECT_KEYS` nếu cần) + hỏi `GROUP_BY_PROJECT` nếu nhiều project.
- Lỗi 401/403/404: giải thích theo bảng trong spec gốc, bằng lời thường.

## Bước 4 — Chạy import

- Bước 3 chạy được trong sandbox → Claude tự chạy `python3 import_jira.py` (tự động hoàn toàn).
  **Tường thuật console cho user:** script in tiến độ từng project
  (`Đang quét project FA — → 2347 issues`...). Claude phải hiển thị lại các dòng này
  trong chat (nguyên văn hoặc tóm tắt theo thời gian thực từng project) để user biết
  hệ thống đang quét gì — không chạy im lặng. Quét xong báo dòng cuối:
  `Obsidian Vault đã tạo tại: <path>`.
- Bước 3 phải chạy ở máy user → sinh lệnh import theo đúng OS như Bước 3
  (macOS/Linux: `python3 import_jira.py`; Windows: `py import_jira.py`).

  Chờ user xác nhận "chạy xong" → Claude kiểm tra vault (đường dẫn theo `vault_path`
  trong config) đã có notes + `_system/*.json` → tiếp Bước 5 như thường.

  Ghi nhớ kết quả vào `config/factory-config.yaml > jira.run_mode: sandbox | user_terminal`
  — lần sau dùng đúng chế độ đã biết, khỏi thử lại từ đầu (vẫn cho user đổi nếu môi
  trường thay đổi, vd vừa bật VPN).

### ⚡ Chế độ user_terminal — KHÔNG chặn setup

Khi sandbox không chạy được, KHÔNG dừng luồng setup lại chờ:

1. Hoàn tất mọi cấu hình trước (`.env.local` đầy đủ).
2. **Ưu tiên cách 1 — file double-click (gần như tự động):**
   present file cho user kèm hướng dẫn 1 dòng:
   - macOS: `quet-jira.command` — double-click trong Finder → Terminal tự mở,
     tự test kết nối, hiện danh sách project, user nhấn Enter là quét, console
     hiện tiến độ trực tiếp. (Lần đầu nếu macOS chặn: chuột phải → Open.
     Nếu báo không có quyền chạy: hướng dẫn 1 lệnh `chmod +x quet-jira.command`.)
   - Windows: `quet-jira.bat` — double-click tương tự.
   File này nằm sẵn trong `tools/jira-to-obsidian/`, KHÔNG phải copy lệnh gì cả.
3. **Cách 2 — copy-paste lệnh** (khi user thích Terminal): in **MỘT khối lệnh
   hoàn chỉnh, đã điền sẵn đường dẫn thật**. **Quy tắc trình bày lệnh:**

   - **Dòng đầu tiên LUÔN là `cd` vào thư mục chứa `.env.local`** (tool dir) —
     script đọc `.env.local` theo thư mục hiện hành, đứng sai chỗ là lỗi.
   - **Mỗi bước một dòng riêng** (xuống dòng, KHÔNG nối && thành 1 dòng dài) —
     dễ đọc, không bị cắt trong khung chat, paste cả khối vẫn chạy tuần tự.
   - Chỉ 2 dòng — không venv, không pip (script dùng thư viện chuẩn Python):

   ```bash
   cd "/đường/dẫn/thật/tới/tools/jira-to-obsidian"
   python3 import_jira.py
   ```

   (Windows: khối PowerShell tương đương, cũng mỗi bước một dòng.)
4. Đánh dấu `jira.import_status: pending_user_run` trong `factory-config.yaml`,
   rồi **tiếp tục các bước setup còn lại** (Bước 5, 6, 7) — không chờ.
5. User chạy xong lúc nào thì nhắn "đã quét xong" (hoặc bất cứ lúc nào sau này) →
   Claude kiểm tra vault có notes + `_system/*.json` → chạy Bước 5 (báo cáo + merge)
   → đổi `import_status: done`.

### 📍 Kết quả lưu ở đâu?

- **Nhiều project?** Bật `GROUP_BY_PROJECT=true` trong `.env.local` (hoặc chạy
  `python import_jira.py --per-project`) → mỗi project Jira một thư mục con trong
  vault: `<Vault>/FA/...`, `<Vault>/FC/...` — dễ duyệt theo project.
  `00_Index` và `_system` (graph, registry) vẫn dùng chung ở gốc vault.
  Lúc setup, nếu user có nhiều hơn 1 project key → hỏi user có muốn bật không (khuyến nghị: có).

- Toàn bộ output ghi vào thư mục khai báo ở biến **`OBSIDIAN_VAULT`** trong `.env.local`.
- `OBSIDIAN_VAULT` là **đường dẫn thư mục vault** — chính là thư mục user sẽ mở trong
  Obsidian bằng "Open folder as vault". KHÔNG phải tên project hay key Jira.
- Mặc định `.env.example` đặt `../../Project_Name_Brain` = thư mục vault của
  project này (tương đối từ `tools/jira-to-obsidian/` — nơi chạy script). Claude phải
  đồng bộ giá trị này với `vault_path` trong `config/factory-config.yaml`.
- Sau khi chạy, script in dòng cuối: `Obsidian Vault đã tạo tại: <đường dẫn tuyệt đối>` —
  đọc dòng này và báo lại cho user kèm hướng dẫn mở bằng Obsidian.
- Nếu user lỡ chạy với vault path khác (vd folder cũ): hỏi user muốn (a) chạy lại với
  path đúng, hay (b) move thư mục output về `Project_Name_Brain/` của project.

Script tự tạo trong vault: notes Project/Epic/Story/Task/Bug/Sub-task có backlink,
`_system/relation-graph.json`, `_system/source-registry.json`, `00_Index/Jira-Knowledge-Base.md`.

## Bước 5 — Báo cáo + Approval Gate

1. Đọc kết quả import, tóm tắt bằng tiếng Việt: bao nhiêu project/epic/story, cái gì
   thiếu parent (nằm ở `08_RawIssues`), cái gì đáng chú ý.
2. **Đây là RAW KB** — chưa phải tri thức chính thức. Hỏi user:
   - [A] Phân loại ngay (chạy `workflows/03-request.md` chế độ classify-batch)
   - [B] Để raw đó, phân loại sau theo từng yêu cầu
3. Merge `_system/*.json` của vault vào `.kb/relation-graph.json` + `.kb/source-registry.json`
   (đánh dấu `status: raw`).
4. Ghi changelog.

## Guardrails riêng

- Không in token, không ghi token vào log.
- Không sửa `.env.local` trừ khi user yêu cầu.
- Không suy diễn Business Rule chính thức từ Jira raw trong bước import.
- Import lại (re-run): script ghi đè note theo `jira_key`, không nhân bản.
- **Lấy dữ liệu MỚI (request mới / issue vừa cập nhật)** mà không quét lại từ đầu:
  `python3 import_jira.py --since` — chỉ kéo issue `updated >=` mốc lần quét trước
  (lưu ở `_system/last-import.txt`), merge vào vault, cập nhật relation graph + registry.
  Lần quét full đầu tiên tự ghi mốc; từ đó về sau dùng `--since` để đồng bộ tăng dần.
  Đây là cách khuyến nghị cho lịch quét định kỳ (có thể đặt scheduled task chạy `--since`).
