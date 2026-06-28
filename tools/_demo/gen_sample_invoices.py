#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_sample_invoices.py — Sinh ẢNH HOÁ ĐƠN MẪU (PoC) để demo luồng:
   ảnh → đọc (vision/OCR) → tổng hợp → report.

Dùng Pillow. Dữ liệu CỐ ĐỊNH (deterministic) để có thể đối chiếu số liệu report.
Xuất PNG vào: inbox/_demo-invoices/

   python3 tools/_demo/gen_sample_invoices.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join("inbox", "_demo-invoices")

# ── Font: thử vài font macOS hỗ trợ tiếng Việt, fallback default ──────────────
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Tahoma.ttf",
]


def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ── Dữ liệu hoá đơn mẫu (Q2/2026) — tổng = subtotal + vat ─────────────────────
# amount của mỗi dòng = qty * unit; subtotal = tổng amount; vat = subtotal*rate; total = subtotal+vat
INVOICES = [
    {
        "no": "HD-2026-0412", "date": "2026-04-05", "vendor": "Công ty TNHH Thiết bị Y tế Tâm Đức",
        "category": "Thiết bị y tế", "vat_rate": 0.08,
        "items": [
            ("Máy đo huyết áp Omron HEM-7156", 10, 850000),
            ("Nhiệt kế hồng ngoại Microlife", 20, 320000),
        ],
    },
    {
        "no": "HD-2026-0455", "date": "2026-04-22", "vendor": "Nhà thuốc Long Châu - CN Q1",
        "category": "Thuốc & vật tư", "vat_rate": 0.05,
        "items": [
            ("Khẩu trang y tế 4 lớp (hộp 50)", 100, 45000),
            ("Cồn sát khuẩn 70 độ 500ml", 60, 28000),
            ("Găng tay y tế nitrile (hộp 100)", 40, 95000),
        ],
    },
    {
        "no": "VPP-0590", "date": "2026-05-03", "vendor": "Văn phòng phẩm Hồng Hà",
        "category": "Văn phòng phẩm", "vat_rate": 0.10,
        "items": [
            ("Giấy A4 Double A (ream)", 50, 72000),
            ("Bút bi Thiên Long (hộp 20)", 30, 48000),
        ],
    },
    {
        "no": "CNTT-2026-118", "date": "2026-05-19", "vendor": "FPT Telecom - Dịch vụ CNTT",
        "category": "Dịch vụ CNTT", "vat_rate": 0.10,
        "items": [
            ("Thuê máy chủ Cloud (tháng)", 3, 4500000),
            ("Tên miền + SSL (năm)", 2, 1200000),
        ],
    },
    {
        "no": "HD-2026-0631", "date": "2026-06-08", "vendor": "Công ty TNHH Thiết bị Y tế Tâm Đức",
        "category": "Thiết bị y tế", "vat_rate": 0.08,
        "items": [
            ("Máy xông khí dung Omron NE-C28", 8, 1650000),
            ("Cân sức khoẻ điện tử", 12, 540000),
        ],
    },
    {
        "no": "DV-2026-077", "date": "2026-06-25", "vendor": "Công ty Vệ sinh Công nghiệp Sạch Xanh",
        "category": "Dịch vụ", "vat_rate": 0.08,
        "items": [
            ("Vệ sinh văn phòng (tháng 6)", 1, 8500000),
            ("Phun khử khuẩn định kỳ", 2, 1500000),
        ],
    },
]


def vnd(n):
    return f"{n:,.0f}".replace(",", ".") + " ₫"


def build_invoice(inv):
    subtotal = sum(q * u for _, q, u in inv["items"])
    vat = round(subtotal * inv["vat_rate"])
    total = subtotal + vat
    inv["_subtotal"], inv["_vat"], inv["_total"] = subtotal, vat, total

    W, H = 1000, 1400
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_title = load_font(40)
    f_h = load_font(26)
    f = load_font(22)
    f_sm = load_font(18)

    # Khung
    d.rectangle([20, 20, W - 20, H - 20], outline=(40, 60, 120), width=3)
    # Header
    d.text((50, 50), "HOÁ ĐƠN GIÁ TRỊ GIA TĂNG", font=f_title, fill=(20, 40, 100))
    d.text((50, 110), f"Số: {inv['no']}", font=f_h, fill=(0, 0, 0))
    d.text((50, 150), f"Ngày: {inv['date']}", font=f, fill=(0, 0, 0))
    d.text((50, 190), f"Đơn vị bán: {inv['vendor']}", font=f, fill=(0, 0, 0))
    d.text((50, 225), f"Phân loại: {inv['category']}", font=f, fill=(80, 80, 80))
    d.text((50, 260), "Đơn vị mua: Công ty CP FPT Medicare", font=f, fill=(0, 0, 0))

    # Bảng items
    y = 330
    d.rectangle([50, y, W - 50, y + 45], fill=(230, 235, 250))
    d.text((60, y + 10), "Mô tả", font=f_sm, fill=(0, 0, 0))
    d.text((560, y + 10), "SL", font=f_sm, fill=(0, 0, 0))
    d.text((650, y + 10), "Đơn giá", font=f_sm, fill=(0, 0, 0))
    d.text((830, y + 10), "Thành tiền", font=f_sm, fill=(0, 0, 0))
    y += 45
    for name, qty, unit in inv["items"]:
        d.text((60, y + 10), name, font=f_sm, fill=(0, 0, 0))
        d.text((560, y + 10), str(qty), font=f_sm, fill=(0, 0, 0))
        d.text((650, y + 10), vnd(unit), font=f_sm, fill=(0, 0, 0))
        d.text((830, y + 10), vnd(qty * unit), font=f_sm, fill=(0, 0, 0))
        d.line([50, y + 45, W - 50, y + 45], fill=(210, 210, 210), width=1)
        y += 50

    # Tổng
    y += 30
    d.text((600, y), "Cộng tiền hàng:", font=f, fill=(0, 0, 0))
    d.text((830, y), vnd(subtotal), font=f, fill=(0, 0, 0))
    y += 40
    d.text((600, y), f"Thuế VAT ({int(inv['vat_rate']*100)}%):", font=f, fill=(0, 0, 0))
    d.text((830, y), vnd(vat), font=f, fill=(0, 0, 0))
    y += 50
    d.text((600, y), "TỔNG CỘNG:", font=f_h, fill=(180, 30, 30))
    d.text((830, y), vnd(total), font=f_h, fill=(180, 30, 30))

    d.text((50, H - 70), "(Hoá đơn mẫu PoC — dữ liệu giả lập)", font=f_sm, fill=(150, 150, 150))
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for inv in INVOICES:
        img = build_invoice(inv)
        path = os.path.join(OUT_DIR, f"{inv['no']}.png")
        img.save(path)
        print(f"✓ {path}  | {inv['vendor'][:30]:30} | total={vnd(inv['_total'])}")
    grand = sum(i["_total"] for i in INVOICES)
    print(f"\n{len(INVOICES)} hoá đơn → {OUT_DIR}")
    print(f"Tổng cộng tất cả (để đối chiếu report): {vnd(grand)}")


if __name__ == "__main__":
    main()
