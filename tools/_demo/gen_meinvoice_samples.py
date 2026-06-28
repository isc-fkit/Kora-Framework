#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_meinvoice_samples.py — Sinh NHIỀU hóa đơn GTGT (VAT) mẫu theo bố cục MISA meInvoice
(dựa trên mẫu 'Hóa đơn nháp x TIDU&TORO'): người MUA cố định = CÔNG TY CỔ PHẦN TIDU VÀ TORO,
đa dạng NHÀ CUNG CẤP / dịch vụ / thuế suất (5/8/10%). Xuất PNG để quét qua luồng hóa đơn.

   python3 tools/_demo/gen_meinvoice_samples.py [--out inbox/_invoices-tidutoro] [--n 8]
"""
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def font(sz, bold=False):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                continue
    return ImageFont.load_default()


def vnd(n):
    return f"{n:,.0f}".replace(",", ".")


def doc_so_tien(amount):
    """Đọc số tiền (VND) thành chữ tiếng Việt — vd 32524200 → 'Ba mươi hai triệu ... đồng chẵn'."""
    amount = int(round(amount))
    if amount == 0:
        return "Không đồng"
    digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

    def read_three(num, show_hundred):
        h, t, u = num // 100, (num % 100) // 10, num % 10
        w = []
        if show_hundred or h > 0:
            w.append(digits[h] + " trăm")
        if t == 0:
            if u > 0 and (show_hundred or h > 0):
                w.append("lẻ")
            if u > 0:
                w.append(digits[u])
        elif t == 1:
            w.append("mười")
            if u == 5:
                w.append("lăm")
            elif u > 0:
                w.append(digits[u])
        else:
            w.append(digits[t] + " mươi")
            if u == 1:
                w.append("mốt")
            elif u == 5:
                w.append("lăm")
            elif u > 0:
                w.append(digits[u])
        return " ".join(w)

    units = ["", "nghìn", "triệu", "tỷ"]
    groups = []
    while amount > 0:
        groups.append(amount % 1000)
        amount //= 1000
    n = len(groups)
    parts = []
    for idx in range(n - 1, -1, -1):
        if groups[idx] == 0:
            continue
        seg = read_three(groups[idx], idx != n - 1)
        if units[idx]:
            seg += " " + units[idx]
        parts.append(seg)
    s = " ".join(parts).strip()
    return s[0].upper() + s[1:] + " đồng chẵn"


BUYER = {
    "name": "CÔNG TY CỔ PHẦN TIDU VÀ TORO",
    "mst": "0314589471",
    "addr": "Số 12 đường số 4, KDC Sông Giồng, Khu Phố 2, Phường Bình Trưng, TP Hồ Chí Minh, Việt Nam",
}

# Mỗi hóa đơn: seller, serial (ký hiệu), date, vat_rate, items [(tên, đvt, sl, đơn giá)]
INVOICES = [
    {"seller": {"name": "CÔNG TY TNHH 9ENT DỪA CON", "mst": "1301146237",
                "addr": "Số nhà 297, Tổ 17, Ấp 1 Giồng Sào, Xã Bình Thới, Huyện Bình Đại, Tỉnh Bến Tre, Việt Nam",
                "bank": "19990990 - TECHCOMBANK - CN Trần Não"},
     "serial": "1C26TĐC", "date": "2026-06-02", "vat": 0.08,
     "items": [("Thanh toán đợt 1: 50% phí dịch vụ quảng cáo theo hợp đồng số 010626/HĐDV/CPLMS/TĐ&TORO", "Gói", 1, 30115000)]},

    {"seller": {"name": "CÔNG TY TNHH QUẢNG CÁO SÁNG TẠO Á CHÂU", "mst": "0312456789",
                "addr": "12 Nguyễn Huệ, P. Bến Nghé, Quận 1, TP. Hồ Chí Minh, Việt Nam",
                "bank": "0601234567 - VIETCOMBANK - CN TP.HCM"},
     "serial": "1C26ACH", "date": "2026-04-11", "vat": 0.08,
     "items": [("Thiết kế bộ nhận diện chiến dịch (Key Visual)", "Gói", 1, 18000000),
               ("Booking bài PR báo điện tử", "Bài", 5, 4000000)]},

    {"seller": {"name": "CÔNG TY TNHH TRUYỀN THÔNG MẶT TRỜI", "mst": "0309988776",
                "addr": "88 Trần Hưng Đạo, P. Phạm Ngũ Lão, Quận 1, TP. Hồ Chí Minh, Việt Nam",
                "bank": "1234567890 - ACB - CN Sài Gòn"},
     "serial": "1C26MTR", "date": "2026-04-28", "vat": 0.10,
     "items": [("Sản xuất TVC quảng cáo thời lượng 30 giây", "Gói", 1, 85000000)]},

    {"seller": {"name": "CÔNG TY CỔ PHẦN IN ẤN HOÀNG GIA", "mst": "0311223344",
                "addr": "45 Lý Thường Kiệt, Quận Tân Bình, TP. Hồ Chí Minh, Việt Nam",
                "bank": "711A12345678 - VIETINBANK - CN Tân Bình"},
     "serial": "1C26HGA", "date": "2026-05-06", "vat": 0.08,
     "items": [("In catalogue A4 4 màu (couche 150gsm)", "Quyển", 1000, 25000),
               ("Standee cuốn 0.8 x 1.8m", "Cái", 20, 350000)]},

    {"seller": {"name": "CÔNG TY TNHH GIẢI PHÁP SỐ FPT", "mst": "0301345678",
                "addr": "Lô T2, Đường D1, KCN Tân Thuận, Quận 7, TP. Hồ Chí Minh, Việt Nam",
                "bank": "0071000999888 - VIETCOMBANK - CN Phú Mỹ Hưng"},
     "serial": "1C26FPT", "date": "2026-05-15", "vat": 0.10,
     "items": [("Chi phí chạy quảng cáo Google Ads tháng 5/2026", "Gói", 1, 45000000),
               ("Chi phí chạy quảng cáo Facebook Ads tháng 5/2026", "Gói", 1, 38000000)]},

    {"seller": {"name": "CÔNG TY TNHH SỰ KIỆN NGÔI SAO", "mst": "0313579246",
                "addr": "20 Phan Xích Long, P.2, Quận Phú Nhuận, TP. Hồ Chí Minh, Việt Nam",
                "bank": "1901234567 - TECHCOMBANK - CN Phú Nhuận"},
     "serial": "1C26SKN", "date": "2026-05-23", "vat": 0.08,
     "items": [("Tổ chức activation tại TTTM GigaMall (2 ngày)", "Gói", 1, 120000000)]},

    {"seller": {"name": "CÔNG TY TNHH NỘI DUNG SỐ VIỆT", "mst": "0316802468",
                "addr": "15 Hoàng Diệu, P.13, Quận 4, TP. Hồ Chí Minh, Việt Nam",
                "bank": "0021000111222 - VIETCOMBANK - CN Quận 4"},
     "serial": "1C26NDS", "date": "2026-06-10", "vat": 0.05,
     "items": [("Sản xuất video ngắn TikTok", "Video", 10, 3500000),
               ("Booking KOL review sản phẩm", "Hợp đồng", 2, 15000000)]},

    {"seller": {"name": "CÔNG TY TNHH TBVP MINH KHANG", "mst": "0305112233",
                "addr": "78 Cách Mạng Tháng 8, P.6, Quận 3, TP. Hồ Chí Minh, Việt Nam",
                "bank": "0600112233 - VIETCOMBANK - CN Quận 3"},
     "serial": "1C26MKH", "date": "2026-06-20", "vat": 0.10,
     "items": [("Giấy in A4 Double A 70gsm", "Ream", 80, 72000),
               ("Mực in Canon 337 (chính hãng)", "Hộp", 15, 1250000)]},
]


def draw_invoice(inv, idx):
    W, H = 1000, 1414
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_title = font(30, True)
    f_h = font(16, True)
    f = font(15)
    f_sm = font(13)
    f_it = font(14)
    BLUE = (10, 40, 130)
    RED = (185, 30, 30)
    M = 40

    # tính tiền
    sub = sum(q * p for _, _, q, p in inv["items"])
    vat = round(sub * inv["vat"])
    total = sub + vat
    inv["_sub"], inv["_vat"], inv["_total"] = sub, vat, total

    # ── Header ──
    dt = inv["date"].split("-")
    d.text((W / 2, 36), "HÓA ĐƠN GIÁ TRỊ GIA TĂNG", font=f_title, fill=BLUE, anchor="mm")
    d.text((W / 2, 70), f"Ngày {dt[2]} tháng {dt[1]} năm {dt[0]}", font=f, fill=(0, 0, 0), anchor="mm")
    d.text((W - M, 92), f"Ký hiệu: {inv['serial']}", font=f_sm, fill=(0, 0, 0), anchor="ra")
    d.text((W - M, 112), "Số: <Chưa cấp số>", font=f_sm, fill=RED, anchor="ra")
    # QR placeholder (lưới ô vuông)
    qx, qy, qs = M, 90, 70
    d.rectangle([qx, qy, qx + qs, qy + qs], outline=(0, 0, 0), width=1)
    for r in range(7):
        for c in range(7):
            if (r * 7 + c * 3 + idx) % 2 == 0:
                d.rectangle([qx + 4 + c * 9, qy + 4 + r * 9, qx + 11 + c * 9, qy + 11 + r * 9], fill=(0, 0, 0))

    y = 180
    # ── Đơn vị bán ──
    s = inv["seller"]
    d.text((M, y), s["name"], font=f_h, fill=BLUE); y += 26
    d.text((M, y), f"Mã số thuế: {s['mst']}", font=f, fill=(0, 0, 0)); y += 22
    d.text((M, y), f"Địa chỉ: {s['addr']}", font=f_sm, fill=(0, 0, 0)); y += 22
    d.text((M, y), f"Số tài khoản: {s['bank']}", font=f_sm, fill=(0, 0, 0)); y += 30

    # ── Người mua ──
    d.text((M, y), "Họ tên người mua hàng:", font=f, fill=(0, 0, 0)); y += 22
    d.text((M, y), f"Tên đơn vị: {BUYER['name']}", font=f_h, fill=BLUE); y += 24
    d.text((M, y), f"Mã số thuế: {BUYER['mst']}", font=f, fill=(0, 0, 0)); y += 22
    d.text((M, y), f"Địa chỉ: {BUYER['addr']}", font=f_sm, fill=(0, 0, 0)); y += 22
    d.text((M, y), "Hình thức thanh toán: TM/CK", font=f_sm, fill=(0, 0, 0)); y += 28

    # ── Bảng hàng hóa ──
    cols = [M, M + 40, 560, 650, 740, W - M]   # STT | tên | ĐVT | SL | đơn giá | thành tiền (mép phải)
    th = 34
    d.rectangle([M, y, W - M, y + th], fill=(225, 232, 248), outline=(120, 130, 160))
    d.text((cols[0] + 6, y + 8), "STT", font=f_sm, fill=(0, 0, 0))
    d.text((cols[1] + 6, y + 8), "Tên hàng hóa, dịch vụ", font=f_sm, fill=(0, 0, 0))
    d.text((cols[2] + 4, y + 8), "ĐVT", font=f_sm, fill=(0, 0, 0))
    d.text((cols[3] + 4, y + 8), "Số lượng", font=f_sm, fill=(0, 0, 0))
    d.text((cols[4] + 4, y + 8), "Đơn giá", font=f_sm, fill=(0, 0, 0))
    d.text((cols[5] - 6, y + 8), "Thành tiền", font=f_sm, fill=(0, 0, 0), anchor="ra")
    y += th

    def wrap(txt, fnt, maxw):
        words, lines, cur = txt.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=fnt) <= maxw:
                cur = t
            else:
                lines.append(cur); cur = w
        if cur:
            lines.append(cur)
        return lines or [""]

    for i, (name, unit, qty, price) in enumerate(inv["items"], 1):
        nlines = wrap(name, f_it, cols[2] - cols[1] - 12)
        rh = max(34, 8 + len(nlines) * 18 + 6)
        d.rectangle([M, y, W - M, y + rh], outline=(210, 215, 230))
        d.text((cols[0] + 10, y + 8), str(i), font=f_it, fill=(0, 0, 0))
        for k, ln in enumerate(nlines):
            d.text((cols[1] + 6, y + 8 + k * 18), ln, font=f_it, fill=(0, 0, 0))
        d.text((cols[2] + 4, y + 8), unit, font=f_it, fill=(0, 0, 0))
        d.text((cols[3] + 60, y + 8), f"{qty:g}", font=f_it, fill=(0, 0, 0), anchor="ra")
        d.text((cols[4] + 85, y + 8), vnd(price), font=f_it, fill=(0, 0, 0), anchor="ra")
        d.text((cols[5] - 6, y + 8), vnd(qty * price), font=f_it, fill=(0, 0, 0), anchor="ra")
        y += rh

    # ── Tổng ──
    y += 16
    d.text((600, y), "Cộng tiền hàng:", font=f, fill=(0, 0, 0)); d.text((W - M, y), vnd(sub), font=f, fill=(0, 0, 0), anchor="ra"); y += 26
    d.text((600, y), f"Thuế suất GTGT: {int(inv['vat']*100)}%   Tiền thuế GTGT:", font=f, fill=(0, 0, 0)); d.text((W - M, y), vnd(vat), font=f, fill=(0, 0, 0), anchor="ra"); y += 30
    d.text((600, y), "Tổng tiền thanh toán:", font=f_h, fill=RED); d.text((W - M, y), vnd(total), font=f_h, fill=RED, anchor="ra"); y += 34
    d.text((M, y), f"Số tiền viết bằng chữ: {doc_so_tien(total)}.", font=f_sm, fill=(0, 0, 0)); y += 40

    # ── Chữ ký ──
    d.text((W * 0.27, y), "Người mua hàng", font=f, fill=(0, 0, 0), anchor="mm")
    d.text((W * 0.73, y), "Người bán hàng", font=f, fill=(0, 0, 0), anchor="mm")
    d.rectangle([W * 0.58, y + 24, W - M, y + 110], outline=(40, 120, 60))
    d.text((W * 0.58 + 10, y + 30), "Signature Valid", font=f_sm, fill=(40, 120, 60))
    d.text((W * 0.58 + 10, y + 52), f"Ký bởi: {inv['seller']['name'][:34]}", font=f_sm, fill=(60, 60, 60))
    d.text((W * 0.58 + 10, y + 74), f"Ký ngày: {inv['date']}", font=f_sm, fill=(60, 60, 60))

    d.text((W / 2, H - 40), "Phát hành bởi MISA meInvoice - Công ty CP MISA - www.meinvoice.vn - MST 0101243130",
           font=f_sm, fill=(150, 150, 150), anchor="mm")
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="inbox/_invoices-tidutoro")
    ap.add_argument("--n", type=int, default=len(INVOICES))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    grand = 0
    for idx, inv in enumerate(INVOICES[:args.n]):
        img = draw_invoice(inv, idx)
        fn = f"HD-{inv['serial']}-{inv['date']}.png"
        img.save(os.path.join(args.out, fn))
        grand += inv["_total"]
        print(f"✓ {fn} | {inv['seller']['name'][:34]:34} | VAT {int(inv['vat']*100)}% | tổng {vnd(inv['_total'])}")
    print(f"\n{min(args.n, len(INVOICES))} hóa đơn → {args.out}")
    print(f"Tổng cộng (đối chiếu report): {vnd(grand)} đồng")


if __name__ == "__main__":
    main()
