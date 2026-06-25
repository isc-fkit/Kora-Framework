#!/usr/bin/env python3
"""
make_sample.py — Xuất file Excel MẪU CHUYÊN NGHIỆP (~100 dòng) theo ĐÚNG format `Import_Task`
(19 cột gốc + STATUS + ACTUAL TIME) + sheet Guideline. Chỉ thư viện chuẩn.

Chạy:  python3 tools/excel-to-obsidian/make_sample.py [đường_dẫn.xlsx] [số_dòng]
Mặc định: /Users/<bạn>/Downloads/Import_Task_v1.0_sample100.xlsx, 100 dòng.

Nạp vào báo cáo:
  python3 tools/excel-to-obsidian/import_excel.py --file <file>.xlsx --sheet Import \
    --map '{"SUBJECT":"summary","ID":"excel_key","TRACKER":"type","STATUS":"status","ASSIGNEE":"assignee","AUTHOR":"reporter","DIVISION":"project","DUE DATE":"duedate","ESTIMATED TIME":"estimate_hours","ACTUAL TIME":"spent_hours","COMPLEXITY":"complexity","TARGET VERSION":"sprint_name"}'
"""
import os
import random
import sys
import zipfile
from datetime import date, timedelta
from xml.sax.saxutils import escape

HEAD = ["SUBJECT", "TASK PROCESS", "TYPE OF WORK", "ASSIGNEE", "START DATE", "DUE DATE", "ESTIMATED TIME",
        "COMPLEXITY", "REVIEW COMPLEXITY", "DESCRIPTION", "TARGET VERSION", "TRACKER", "DIVISION", "TYPE",
        "ID", "PARENT TASK", "RELATED TO", "AUTHOR", "IDENTIFIER", "STATUS", "ACTUAL TIME"]

TODAY = date(2026, 6, 25)
DEVS = ["An", "Bình", "Dũng", "Em", "Phúc", "Giang"]
PM = "Khánh (PO)"
QCS = ["Châu (QC)", "Linh (QC)"]
DIVISIONS = ["BDH", "MKT", "ADM", "BIL", "BOD", "SUP"]
SPRINTS = ["v1.1", "v1.2", "v1.3"]
PRIORITY = ["Normal", "High", "Urgent", "Low"]
PROCESS = ["Service Request", "Requirement & Design", "Coding", "Unit Test", "Testing", "Deployment", "Support"]
TOW = ["Study", "Do", "Review", "Fix/Rework"]
STATUS = ["Hoàn thành", "Đang làm", "Chưa làm"]

SUBJECTS = [
    "Đăng nhập SSO cho nhân viên", "Bổ sung API đăng ký thành viên", "Thiết kế CSDL hồ sơ sức khỏe",
    "Tối ưu truy vấn báo cáo doanh thu", "Tích hợp cổng thanh toán VNPay", "Màn hình quản lý gói khám",
    "Đồng bộ dữ liệu KHTN theo quý", "Xây dựng dashboard tiến độ dự án", "Quản lý phân quyền người dùng",
    "Tích hợp eKYC định danh điện tử", "Thông báo đẩy (push notification)", "Xuất báo cáo PDF tự động",
    "Tối ưu thời gian tải trang chủ", "Quản lý lịch hẹn khám bệnh", "Tích hợp BHYT trực tuyến",
    "Module nhắc lịch tái khám", "Lưu trữ hồ sơ bệnh án điện tử", "Tìm kiếm bác sĩ theo chuyên khoa",
    "Đánh giá & phản hồi dịch vụ", "Quản lý kho thuốc & tồn kho", "API tra cứu kết quả xét nghiệm",
    "Tích hợp bản đồ phòng khám", "Đặt lịch tiêm chủng", "Quản lý hợp đồng đối tác",
    "Báo cáo thống kê theo vùng", "Cấu hình quy tắc tính phí", "Migrate dữ liệu hệ thống cũ",
    "Kiểm thử hiệu năng API", "Pentest cổng thanh toán", "Tài liệu hướng dẫn tích hợp đối tác",
]
BUGS = [
    "Lỗi sai số dư ví khi hoàn tiền", "Không gửi được email OTP", "Sai múi giờ lịch hẹn",
    "Treo app khi mở hồ sơ lớn", "Trùng bản ghi khi đồng bộ", "Lỗi phân trang danh sách bác sĩ",
    "Tính sai phí gói gia đình", "Mất session sau 5 phút", "Hiển thị sai trạng thái thanh toán",
    "Crash khi upload ảnh > 10MB", "Sai định dạng ngày trên báo cáo", "Lỗi 500 khi tra cứu BHYT",
]


def colref(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def sheet_xml(rows, shared):
    o = ['<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    for r, row in enumerate(rows, 1):
        cs = []
        for c, v in enumerate(row):
            if v == "" or v is None:
                continue
            ref = f"{colref(c)}{r}"
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                cs.append(f'<c r="{ref}"><v>{v}</v></c>')
            else:
                cs.append(f'<c r="{ref}" t="s"><v>{shared[str(v)]}</v></c>')
        o.append(f'<row r="{r}">' + "".join(cs) + "</row>")
    o.append("</sheetData></worksheet>")
    return "".join(o)


def write_xlsx(path, sheets):
    order, shared = [], {}
    for _n, rows in sheets:
        for row in rows:
            for v in row:
                if isinstance(v, str) and v != "" and v not in shared:
                    shared[v] = len(order)
                    order.append(v)
    sst = ('<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
           f'count="{len(order)}" uniqueCount="{len(order)}">'
           + "".join('<si><t xml:space="preserve">%s</t></si>' % escape(s) for s in order) + "</sst>")
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
          + "".join(f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                    for i in range(len(sheets))) + "</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    stags = "".join(f'<sheet name="{escape(n)}" sheetId="{i+1}" r:id="rId{i+1}"/>' for i, (n, _) in enumerate(sheets))
    wb = ('<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          f'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{stags}</sheets></workbook>')
    wbr = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
           + "".join(f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i+1}.xml"/>'
                     for i in range(len(sheets)))
           + f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>')
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wbr)
        z.writestr("xl/sharedStrings.xml", sst)
        for i, (_n, rows) in enumerate(sheets):
            z.writestr(f"xl/worksheets/sheet{i+1}.xml", sheet_xml(rows, shared))


def gen_rows(n):
    rnd = random.Random(20260625)   # seed cố định → tái tạo được
    rows = [HEAD]
    for i in range(1, n + 1):
        # ~15% User Story (PM tạo), ~20% Bug (QC tạo), còn lại Task (Dev làm)
        roll = rnd.random()
        if roll < 0.15:
            tracker, subj, author = "User Story", rnd.choice(SUBJECTS), PM
            tow, proc = "Study", "Requirement & Design"
        elif roll < 0.35:
            tracker, subj, author = "Bug", rnd.choice(BUGS), rnd.choice(QCS)
            tow, proc = "Fix/Rework", "Testing"
        else:
            tracker, subj, author = "Task", rnd.choice(SUBJECTS), PM
            tow, proc = rnd.choice(TOW), rnd.choice(PROCESS)
        assignee = rnd.choice(DEVS)
        status = rnd.choices(STATUS, weights=[3, 4, 3])[0]
        cx = rnd.choices(range(1, 11), weights=[2, 3, 4, 5, 6, 6, 5, 4, 3, 2])[0]
        est = rnd.choice([4, 6, 8, 12, 16, 20, 24, 32])
        if status == "Hoàn thành":
            act = est + rnd.choice([-4, -2, 0, 0, 2])
        elif status == "Đang làm":
            act = max(0, int(est * rnd.choice([0.2, 0.4, 0.5, 0.6])))
        else:
            act = 0
        act = max(0, act)
        start = TODAY - timedelta(days=rnd.randint(5, 40))
        due = start + timedelta(days=rnd.randint(5, 35))   # nhiều mục quá hạn vs TODAY
        rid = f"T{i:03d}"
        review = "Cần review kỹ" if cx >= 8 and rnd.random() < 0.5 else ""
        rows.append([
            subj, proc, tow, assignee, start.isoformat(), due.isoformat(), est, cx, review,
            subj, rnd.choice(SPRINTS), tracker, rnd.choice(DIVISIONS), rnd.choice(PRIORITY),
            rid, "", "", author, "fmc", status, act,
        ])
    return rows


GUIDE = [["Cột", "Ý nghĩa", "Ghi chú / map → field báo cáo"],
         ["SUBJECT", "Tên công việc", "→ summary (BẮT BUỘC)"],
         ["STATUS", "Trạng thái", "→ status (Chưa làm/Đang làm/Hoàn thành) — BẮT BUỘC cho báo cáo tiến độ"],
         ["ASSIGNEE", "Người làm", "→ assignee"],
         ["AUTHOR", "Người tạo", "→ reporter (PM tạo User Story; QC tạo Bug)"],
         ["TRACKER", "Loại", "→ type (Task/Bug/User Story)"],
         ["DIVISION", "Bộ phận", "→ project (gộp/lọc theo bộ phận)"],
         ["DUE DATE", "Hạn", "→ duedate (YYYY-MM-DD; quá hạn + chưa done → cảnh báo)"],
         ["ESTIMATED TIME", "Giờ ước tính", "→ estimate_hours (×3600 thành giây)"],
         ["ACTUAL TIME", "Giờ thực tế", "→ spent_hours"],
         ["COMPLEXITY", "Độ phức tạp", "→ complexity (≥7 = phức tạp cao)"],
         ["TARGET VERSION", "Phiên bản/Sprint", "→ sprint_name"],
         ["", "", ""],
         ["LƯU Ý", "Sheet dữ liệu = 'Import' (sheet đầu)", "Sheet 'Guideline' này KHÔNG bị nạp."],
         ["", "Cột gốc Import_Task được giữ nguyên", "Đã thêm STATUS + ACTUAL TIME để báo cáo tiến độ có nghĩa."]]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expanduser("~"), "Downloads", "Import_Task_v1.0_sample100.xlsx")
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    rows = gen_rows(n)
    write_xlsx(out, [("Import", rows), ("Guideline", GUIDE)])
    print(f"✅ Đã xuất {n} dòng mẫu → {os.path.abspath(out)}")
    print("   Sheet 'Import' (dữ liệu) + 'Guideline'. Nạp: import_excel.py --file <file> --sheet Import --map <map Import_Task>")


if __name__ == "__main__":
    main()
