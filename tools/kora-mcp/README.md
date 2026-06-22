# tools/kora-mcp — MCP `local-terminal` (chạy terminal local cho Claude Desktop / Cowork)

**Mục đích:** Cowork (chế độ agentic) chạy tool `Bash` trong **sandbox chặn mạng** → không quét được Jira nội bộ,
không gửi SMTP. MCP server này phơi tool **`run_command`** chạy như **tiến trình local riêng** (do Claude Desktop
spawn, mang quyền user) → chạy lệnh THẲNG trên máy thật (đúng PATH/VPN), **ngoài sandbox**. Nhờ đó skill Kora
quét/report/gửi-mail thẳng trong chat, **không cần bàn giao file `.command` cho Terminal**.

> ⚠️ **Chỉ Claude Desktop** (app macOS/Windows) — **web Cowork KHÔNG** chạy được local stdio MCP.
> ⚠️ **`run_command` = arbitrary command execution** với quyền của bạn. Opt-in. Mỗi lần gọi vẫn qua permission prompt
> của Claude. **KHÔNG** bật cho người dùng cuối nếu không cố ý. Đây KHÔNG phải phần cài tự động của framework.

## Cài (macOS) — CÁCH NHANH (script)
**Thoát hẳn Claude Desktop (`Cmd+Q`)** rồi chạy ở Terminal:
```bash
bash "$HOME/.claude/kora-framework/tools/kora-mcp/setup_macos.command"
```
Script tự backup + thêm `mcpServers.local-terminal` (trỏ server bản cài) + từ chối chạy nếu Claude đang mở (tránh app
ghi đè). Xong → đặt token vào `~/.zshrc` (xem dưới) → mở lại Claude.

> 🔑 **Token đặt ở `~/.zshrc`** (đúng rule #6 — `/claude-knowledge-connect` cũng ghi vào đây): `export JIRA_BASE_URL=… JIRA_PAT=… JIRA_AUTH_MODE=server`.
> `run_command` **source `~/.zshrc` mỗi lần chạy** → đổi/thêm token KHÔNG cần restart Claude.

## Cài (macOS) — THỦ CÔNG
1. Mở `~/Library/Application Support/Claude/claude_desktop_config.json`, thêm (giữ nguyên các key cũ):
   ```json
   {
     "mcpServers": {
       "local-terminal": {
         "command": "/opt/homebrew/bin/python3",
         "args": ["<ĐƯỜNG-DẪN-TUYỆT-ĐỐI>/tools/kora-mcp/local_terminal_mcp.py"]
       }
     }
   }
   ```
   (Đổi `command` cho đúng `which python3` của bạn; đường dẫn server là tuyệt đối.)
2. **Thoát hẳn Claude** (`Cmd+Q`) rồi mở lại. Nếu không thấy tool → Settings → **Developer** bật Developer mode → restart.
3. Test trong Cowork: *"dùng `run_command` chạy: `whoami && pwd`"* → ra tên máy bạn.
4. **Phép thử vượt sandbox:** *"dùng `run_command` chạy: `python3 \"…/tools/jira-to-obsidian/import_jira.py\" --test`"*
   → ra kết quả thật / mã 200 = MCP đã thoát sandbox.

## Skill tự ưu tiên
Khi đã có `run_command`, các skill (`/claude-knowledge-scan`, `/claude-knowledge-send-mail`, `/claude-knowledge-daily-report`)
+ workflow 01/14 **tự ưu tiên gọi `run_command`** chạy `import_jira.py`/`build_report.py`/`send_report.py` thẳng; KHÔNG có
thì fallback bàn giao bash như cũ. (Lịch NỀN vẫn chạy qua OS launchd/cron, không qua MCP này.)

## Giao thức
JSON-RPC 2.0 newline-delimited qua stdio (MCP stdio transport). Chỉ thư viện chuẩn Python 3 — không cần `pip install`.
Tool `run_command(command, cwd?, timeout?)` → chạy bằng SHELL đăng nhập (`$SHELL`, zsh trên macOS) và **source `~/.zshrc`** (hoặc `~/.bashrc`) trước → có đúng biến env user khai (JIRA_PAT…) + PATH như Terminal thật. Trả stdout + stderr + exit code.

## Gỡ
Xoá entry `local-terminal` trong `mcpServers` (hoặc khôi phục file backup `claude_desktop_config.json.bak-*`) → restart Claude.
