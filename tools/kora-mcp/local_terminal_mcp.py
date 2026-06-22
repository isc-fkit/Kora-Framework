#!/usr/bin/env python3
"""
local_terminal_mcp.py — MCP server (stdio) cho Claude Desktop / Cowork chạy LỆNH TERMINAL trên
MÁY LOCAL THẬT (ngoài sandbox của agent). CHỈ thư viện chuẩn Python 3 — KHÔNG cần pip install.

VÌ SAO: tool Bash của agent Cowork chạy trong SANDBOX (chặn mạng outbound). MCP server này là một
TIẾN TRÌNH LOCAL riêng do Claude Desktop spawn, mang QUYỀN USER → chạy được lệnh thật: quét Jira
nội bộ, gửi SMTP, chạy script... — đúng thứ sandbox chặn.

⚠️ BẢO MẬT: `run_command` THỰC THI LỆNH TÙY Ý với quyền của bạn. Chỉ bật khi hiểu rủi ro. Mọi lần
gọi vẫn qua permission prompt của Claude. KHÔNG ship cho người dùng cuối nếu không cố ý.

CẤU HÌNH (macOS) — ~/Library/Application Support/Claude/claude_desktop_config.json:
  "mcpServers": {
    "local-terminal": {
      "command": "/opt/homebrew/bin/python3",
      "args": ["<đường-dẫn-tuyệt-đối>/tools/kora-mcp/local_terminal_mcp.py"]
    }
  }
→ Thoát hẳn Claude (Cmd+Q) rồi mở lại. Tool `run_command` sẽ xuất hiện.

Giao thức: JSON-RPC 2.0 newline-delimited qua stdio (MCP stdio transport). stdout CHỈ dùng cho
JSON-RPC; mọi log → stderr.
"""
import json
import os
import shlex
import subprocess
import sys
import traceback

SERVER_NAME = "local-terminal"
SERVER_VERSION = "1.1.0"
DEFAULT_PROTOCOL = "2024-11-05"


def log(msg):
    print(f"[local-terminal-mcp] {msg}", file=sys.stderr, flush=True)


def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


TOOLS = [{
    "name": "run_command",
    "description": ("Chạy 1 lệnh shell trên MÁY LOCAL thật (bash -lc, đúng PATH/VPN của bạn), trả "
                    "stdout + stderr + exit code. Dùng để VƯỢT sandbox: quét Jira nội bộ, gửi SMTP, "
                    "chạy import_jira.py / build_report.py / send_report.py... Chạy với QUYỀN USER."),
    "inputSchema": {
        "type": "object",
        "properties": {
            "command": {"type": "string",
                        "description": "Lệnh shell, vd: python3 \"tools/jira-to-obsidian/import_jira.py\" --test"},
            "cwd": {"type": "string", "description": "Thư mục chạy (mặc định HOME của bạn)"},
            "timeout": {"type": "number", "description": "Giới hạn giây (mặc định 600)"},
        },
        "required": ["command"],
    },
}]


def tool_run_command(args):
    cmd = (args.get("command") or "").strip()
    cwd = args.get("cwd") or os.path.expanduser("~")
    timeout = args.get("timeout") or 600
    if not cmd:
        return {"content": [{"type": "text", "text": "LỖI: command rỗng."}], "isError": True}
    if not os.path.isdir(os.path.expanduser(cwd)):
        return {"content": [{"type": "text", "text": f"LỖI: cwd không tồn tại: {cwd}"}], "isError": True}
    # Chạy bằng SHELL ĐĂNG NHẬP của user (zsh trên macOS) và SOURCE ~/.zshrc (hoặc ~/.bashrc) trước —
    # để có ĐÚNG biến môi trường user khai trong rc (JIRA_PAT, JIRA_BASE_URL…) + PATH như Terminal thật.
    # (App GUI spawn MCP KHÔNG có env shell; `bash -lc` cũng không đọc ~/.zshrc → phải source tay.)
    shell = os.environ.get("SHELL") or "/bin/zsh"
    rc = os.path.expanduser("~/.zshrc" if "zsh" in shell else "~/.bashrc")
    wrapped = f"[ -f {shlex.quote(rc)} ] && source {shlex.quote(rc)} >/dev/null 2>&1; {cmd}"
    try:
        p = subprocess.run([shell, "-c", wrapped], cwd=os.path.expanduser(cwd),
                           capture_output=True, text=True, timeout=float(timeout))
        out = p.stdout or ""
        if p.stderr:
            out += ("\n--- stderr ---\n" + p.stderr)
        out += f"\n[exit code: {p.returncode}]"
        return {"content": [{"type": "text", "text": out[:100000]}], "isError": p.returncode != 0}
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": f"LỖI: lệnh chạy quá {timeout}s → đã hủy."}], "isError": True}
    except Exception as e:  # noqa: BLE001
        return {"content": [{"type": "text", "text": f"LỖI khi chạy: {e}"}], "isError": True}


def handle(msg):
    mid = msg.get("id")
    method = msg.get("method")
    if method == "initialize":
        pv = (msg.get("params") or {}).get("protocolVersion") or DEFAULT_PROTOCOL
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": pv,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        if name == "run_command":
            return {"jsonrpc": "2.0", "id": mid, "result": tool_run_command(params.get("arguments") or {})}
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if mid is None:          # notification (vd notifications/initialized) → không trả lời
        return None
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main():
    log("started — chờ JSON-RPC qua stdin")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            log(f"JSON hỏng: {e}")
            continue
        try:
            resp = handle(msg)
            if resp is not None:
                send(resp)
        except Exception:  # noqa: BLE001
            log("lỗi handler:\n" + traceback.format_exc())
            if msg.get("id") is not None:
                send({"jsonrpc": "2.0", "id": msg.get("id"),
                      "error": {"code": -32603, "message": "internal error"}})


if __name__ == "__main__":
    main()
