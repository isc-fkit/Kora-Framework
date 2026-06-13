#!/bin/bash
# Double-click file này trong Finder để quét Jira → vault (macOS).
# Terminal sẽ mở và hiện tiến độ trực tiếp.
cd "$(dirname "$0")"
echo "=== AI Product Factory — Quét Jira → Obsidian Vault ==="
echo
python3 import_jira.py --test || { echo; read -p "Lỗi kết nối/cấu hình (xem ở trên). Nhấn Enter để đóng..."; exit 1; }
echo
read -p "Kết nối OK (danh sách project ở trên). Nhấn Enter để BẮT ĐẦU QUÉT, hoặc Cmd+. để hủy..."
python3 import_jira.py
echo
read -p "Xong! Quay lại Cowork nhắn 'đã quét xong'. Nhấn Enter để đóng..."
