# Workflow 01 — Import Jira → Obsidian (tự động hoàn toàn)

> Spec gốc: `tools/jira-to-obsidian/CLAUDE_CODE_JIRA_TO_OBSIDIAN_SETUP.md` (Bước 1→7).
> Script đã viết sẵn: `tools/jira-to-obsidian/import_jira.py` — KHÔNG cần viết lại,
> chỉ cấu hình và chạy. Muốn quét RIÊNG 1 vài issue → dùng `workflows/01b-import-jira-single.md`.
>
> **Lưu ý (đã vá 2026-06-13):** script tự tìm `.env.local` và vault theo **vị trí FILE script**,
> KHÔNG theo thư mục đang đứng (cwd). Nhờ vậy chạy từ bất kỳ cwd nào cũng nạp đúng config + ghi
> đúng vault. Vì thế **lệnh chạy nên dùng đường dẫn TUYỆT ĐỐI tới script, KHÔNG cần `cd`** — gọi
> `python3 "<TOOL_DIR>/import_jira.py"` là đủ, bền nhất, không lo đứng sai thư mục.

## Bước 0 — Chọn NGUỒN Jira (domain) cần quét

Hỗ trợ **nhiều nguồn** (Server tự host + Cloud Atlassian), mỗi nguồn một file cấu hình
`tools/jira-to-obsidian/.env.<tên>` (mặc định `.env.local`). TRƯỚC khi quét, để user CHỌN nguồn:

1. Liệt kê nguồn đã cấu hình: các file `tools/jira-to-obsidian/.env*` (TRỪ `.env.example`).
   Với mỗi file đọc `JIRA_BASE_URL` → hiện domain + loại, vd `jira.company.vn (Server)`,
   `myteam.atlassian.net (Cloud)`.
2. **Chọn nguồn (AskUserQuestion):** mỗi nguồn đã có = 1 lựa chọn + **"➕ Thêm nguồn mới
   (vd Atlassian Cloud)"**.
   - Chưa có nguồn nào (chỉ `.env.example`) → coi như "thêm nguồn mới" luôn.
   - Chỉ có đúng 1 nguồn và user không nhắc nguồn khác → dùng luôn, nhưng vẫn nói 1 câu:
     *"Đang quét từ `<domain>`. Muốn thêm/đổi sang nguồn khác (vd Atlassian Cloud) thì báo nhé."*
3. **Chọn nguồn có sẵn** → MỌI lệnh quét bên dưới dùng đúng file đó:
   `JIRA_ENV_FILE=.env.<tên> python3 import_jira.py …` (nếu là `.env.local` thì khỏi cần biến).
4. **"Thêm nguồn mới"** → hỏi loại (Server tự host / Cloud Atlassian) → tạo `.env.<tên-nguồn>`
   rồi làm token flow như **Bước 2** (Cloud cần email + API token; Server chỉ PAT).
   **Tên nguồn / URL / email là input TỰ DO → hỏi bằng CÂU THƯỜNG, KHÔNG nhồi vào AskUserQuestion**
   (nguyên tắc 8). Mốc `--since` tách theo host (`last-import-<host>.txt`) nên sync KHÔNG đè nhau.
   ⚠️ Notes/graph để CHUNG vault và phân theo **MÃ project** (không theo host) → để 2 nguồn KHÔNG
   đè nhau: đặt `PROJECT_KEYS` không trùng mã giữa các nguồn, HOẶC cho mỗi nguồn một
   `OBSIDIAN_VAULT` riêng trong `.env.<tên>` (xem CLAUDE.md §6 "Giới hạn đã biết").

> Nhờ bước này, "quét jira" LUÔN cho chọn quét từ domain nào (nội bộ hay Atlassian Cloud),
> không bị khóa cứng vào một nguồn.

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
   - **Jira Server / Data Center** (tự host, vd `https://jira.company.vn`): chỉ cần **PAT**.
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
>    thì hỏi 1 câu: macOS / Windows / Linux). Điền `<TOOL_DIR>` = **đường dẫn tuyệt đối
>    THẬT của máy này** tới `tools/jira-to-obsidian` (lấy từ project root hiện tại — Claude
>    tự tính, **KHÔNG viết cứng đường dẫn mẫu**). Dùng **đường dẫn tuyệt đối tới script,
>    KHÔNG cần `cd`** (script tự định vị `.env.local`/vault theo vị trí file — xem lưu ý đầu trang):
>
>    **macOS / Linux:**
>    ```bash
>    python3 "<TOOL_DIR>/import_jira.py" --test
>    ```
>
>    **Windows (PowerShell):**
>    ```powershell
>    py "<TOOL_DIR>\import_jira.py" --test
>    ```
>
>    Đa nguồn (file `.env.<tên>` khác `.env.local`): thêm tiền tố `JIRA_ENV_FILE=.env.<tên> `
>    trước lệnh (bash) hoặc `$env:JIRA_ENV_FILE=".env.<tên>"; ` (PowerShell).
>    Nếu máy user không có Python → hướng dẫn cài theo OS (macOS: `brew install python3`
>    hoặc python.org; Windows: Microsoft Store / python.org, tick "Add to PATH").
> 4. User dán kết quả (danh sách project) vào chat → Claude tiếp tục như thường.

- **Thành công → BẮT BUỘC hiện danh sách project cho user CHỌN** (Bước 3.5). KHÔNG tự ý quét tất cả.
- Lỗi 401/403/404: giải thích theo bảng trong spec gốc, bằng lời thường.

## Bước 3.5 — Hiện danh sách project → user chọn lấy dữ liệu nào (BẮT BUỘC)

Sau khi `--test` trả về danh sách project, KHÔNG tự quyết phạm vi. Trình bày danh sách rõ
ràng (mã + tên project) và cho user CHỌN bằng AskUserQuestion:

- Mỗi project = một lựa chọn, cho **chọn nhiều** (`multiSelect`); thêm phương án "Tất cả"
  và (nếu nhiều project) "Vài project chính".
- User chọn xong → ghi đúng các mã đã chọn vào `PROJECT_KEYS` trong `.env.local`
  (cách nhau dấu phẩy). Chọn ≥2 project → bật `GROUP_BY_PROJECT=true`.
- Project rất lớn (hàng nghìn issue) → báo trước "sẽ lâu + vault lớn, nên chạy nền".

> Ví dụ: `--test` thấy N project (PROJ1, PROJ2, PROJ3…) → hiện cho user tick chọn → chỉ
> quét đúng cái đã chọn (vd PROJ1 = vài nghìn issue).

## Bước 4 — Chạy import

- Bước 3 chạy được trong sandbox → Claude tự chạy `python3 "<TOOL_DIR>/import_jira.py"`
  (đường dẫn tuyệt đối, không cần `cd`; tự động hoàn toàn).
  **Tường thuật console cho user:** script in tiến độ từng project
  (`Đang quét project FA — → 2347 issues`...). Claude phải hiển thị lại các dòng này
  trong chat (nguyên văn hoặc tóm tắt theo thời gian thực từng project) để user biết
  hệ thống đang quét gì — không chạy im lặng. Quét xong báo dòng cuối:
  `Obsidian Vault đã tạo tại: <path>` → rồi **HIỆN KẾT QUẢ NGAY** (Bước 5): bảng số lượng
  theo loại + đường dẫn vault, KHÔNG đợi user hỏi mới hiện.
- Bước 3 phải chạy ở máy user → sinh lệnh import theo đúng OS như Bước 3, dạng đường dẫn
  tuyệt đối không cần `cd` (macOS/Linux: `python3 "<TOOL_DIR>/import_jira.py"`;
  Windows: `py "<TOOL_DIR>\import_jira.py"`).

  Chờ user xác nhận "chạy xong" → Claude kiểm tra vault (đường dẫn theo `vault_path`
  trong config) đã có notes + `_system/*.json` → tiếp Bước 5 như thường.

  Ghi nhớ kết quả vào `config/factory-config.yaml > jira.run_mode: sandbox | user_terminal`
  — lần sau dùng đúng chế độ đã biết, khỏi thử lại từ đầu (vẫn cho user đổi nếu môi
  trường thay đổi, vd vừa bật VPN).

### ⚡ Chế độ user_terminal — KHÔNG chặn setup

Khi sandbox không chạy được (lỗi mạng), KHÔNG dừng luồng setup lại chờ:

1. Hoàn tất mọi cấu hình trước (`.env.local` đầy đủ).
2. **Cách DUY NHẤT cho user tự chạy = lệnh Terminal copy-paste.**
   > 🚫 KHÔNG dùng file double-click (`.command`/`.bat`) — macOS Gatekeeper hay chặn
   > "không đáng tin cậy / không mở được" gây hoang mang. Đã bỏ 2 file đó khỏi tool.

   In **MỘT khối lệnh hoàn chỉnh, đã điền sẵn đường dẫn TUYỆT ĐỐI THẬT của máy này**.
   **Quy tắc trình bày lệnh:**
   - **Đường dẫn `<TOOL_DIR>` Claude tự tính** từ project root hiện tại + `/tools/jira-to-obsidian`
     — **dynamic theo từng máy/OS, TUYỆT ĐỐI KHÔNG hardcode đường dẫn mẫu.**
   - **KHÔNG cần `cd`**: gọi thẳng `python3 "<TOOL_DIR>/import_jira.py"` (script tự định vị
     `.env.local`/vault theo vị trí file — xem lưu ý đầu trang). Đứng sai thư mục cũng chạy đúng.
   - **Mỗi bước một dòng riêng** (xuống dòng, KHÔNG nối `&&`) — dễ đọc, paste cả khối vẫn chạy tuần tự.
   - Không venv, không pip (script chỉ dùng thư viện chuẩn Python):

   **macOS / Linux:**
   ```bash
   python3 "<TOOL_DIR>/import_jira.py" --test
   python3 "<TOOL_DIR>/import_jira.py"
   ```

   **Windows (PowerShell):**
   ```powershell
   py "<TOOL_DIR>\import_jira.py" --test
   py "<TOOL_DIR>\import_jira.py"
   ```

   Đa nguồn (`.env.<tên>`): thêm `JIRA_ENV_FILE=.env.<tên> ` trước lệnh (bash) /
   `$env:JIRA_ENV_FILE=".env.<tên>"; ` (PowerShell).
3. Đánh dấu `jira.import_status: pending_user_run` trong `factory-config.yaml`,
   rồi **tiếp tục các bước setup còn lại** (Bước 5, 6, 7) — không chờ.
4. User chạy xong lúc nào thì nhắn "đã quét xong" (hoặc bất cứ lúc nào sau này) →
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

1. **Hiện NGAY bảng kết quả** (tiếng Việt): đếm theo loại — Epics / User Stories / Tasks /
   Bugs / Sub-tasks + **tổng issue** + đường dẫn vault. Lấy số từ dòng script in ra, hoặc
   đếm file `.md` trong vault. Nêu thêm: cái gì thiếu parent (ở `08_RawIssues`), điểm đáng chú ý.
2. **Đây là RAW KB** — chưa phải tri thức chính thức. Hỏi user:
   - [A] Phân loại ngay (chạy `workflows/03-request.md` chế độ classify-batch)
   - [B] Để raw đó, phân loại sau theo từng yêu cầu
3. Merge `_system/*.json` của vault vào `.kb/relation-graph.json` + `.kb/source-registry.json`
   (đánh dấu `status: raw`).
4. Chạy `python3 tools/kb-indexer/build_index.py --root .` → index/graph/health phản ánh
   NGAY dữ liệu vault vừa quét, để auto-phân tích (Tầng A) có dữ liệu tra cứu, khỏi grep chay.
5. Ghi changelog.

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
