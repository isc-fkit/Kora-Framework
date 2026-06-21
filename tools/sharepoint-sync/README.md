# tools/sharepoint-sync

Đồng bộ Knowledge Base ↔ **SharePoint** (document library) qua **Microsoft Graph**. Anh em với
`confluence-sync` / `github-sync` — cùng "gom KB cục bộ → ĐẨY lên nơi chung; chỉ-đọc thì KÉO về".
Idempotent (map theo `kb_id`, chỉ ghi file đổi nội dung). Đường HEADLESS (chạy được trong scheduler).

## Xác thực (TỰ NHẬN DIỆN — cả hai)
- **App-only (client-credentials)** — *chạy NỀN được*: cần `SHAREPOINT_TENANT_ID` +
  `SHAREPOINT_CLIENT_ID` + `SHAREPOINT_CLIENT_SECRET`. App đăng ký Azure AD phải có **admin consent**
  quyền **`Sites.ReadWrite.All`** (Application). Token xin mới mỗi lần chạy.
- **Device-flow (delegated)** — *chỉ tương tác*: chạy `--login` 1 lần (nhập mã trên trình duyệt) →
  lưu `.oauth-token.json` (tự refresh). Token hết hạn refresh-token thì đăng nhập lại.

Bí mật để ở **shell ENV** (`~/.zshrc`) hoặc `.env.local` (chỉ cho lịch nền). KHÔNG vào chat/git/config.

## Cấu hình (`config/factory-config.yaml` khối `sharepoint:`)
```yaml
sharepoint:
  enabled: true
  base_url: "https://<tenant>.sharepoint.com"
  site_name: "FTEL_Medicare"      # tên site
  library: "Knowledge Base"        # tên thư viện tài liệu (rỗng = thư viện mặc định)
  drive_id: ""                     # override trực tiếp drive id (nếu biết)
  permission: read_write           # read_only → chỉ pull
  push: { source: both, scope: "", subdir: "" }
  pull: { into: "", subdir: "" }
```

## Lệnh
```bash
python3 tools/sharepoint-sync/sync_sharepoint.py --check
python3 tools/sharepoint-sync/sync_sharepoint.py --login          # device-flow
python3 tools/sharepoint-sync/sync_sharepoint.py --push --dry-run # xem +tạo/~sửa/-xóa (không cần mạng)
python3 tools/sharepoint-sync/sync_sharepoint.py --push
python3 tools/sharepoint-sync/sync_sharepoint.py --pull
# Windows: thay python3 bằng py
```

## Lưu ý
- **Sandbox Cowork chặn API ra ngoài** → mọi lệnh gọi Graph (`--check/--push/--pull`) phải chạy ở
  **máy thật** (hoặc qua lịch HĐH launchd/cron). `--push --dry-run` chạy offline được (chỉ đọc local + map).
- Map idempotent: `<vault>/_system/sharepoint/sharepoint-map-<host>-<site>.json`.
- File đẩy lên là **raw `.md`** (thư viện hỗ trợ Markdown document) — không convert.
- Trong lịch nền (`/kora-schedule`) token `sharepoint:<site>` ở scan/post; `sharepoint` ở sync-targets.
