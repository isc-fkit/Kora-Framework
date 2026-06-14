# Workflow 13 — Tiến hóa hệ thống (workflow & rule)

> Trigger: "tiến hóa hệ thống", "rà soát workflow", "cải tiến quy trình/rule" (confirm trước).
> Đây là **meta-tiến hóa**: làm cho *workflow & rule* đúng những gì `workflows/09-evolve.md` làm
> cho *tri thức (KB)*. **CHỈ người DUY TRÌ app** (sửa CORE — như release).

## Bước 0 — Guard maintainer (KIỂM TRA TRƯỚC TIÊN)

**Chạy NGUYÊN Bước 0 của `workflows/12-release.md`** (cùng cơ chế: kiểm tra `.maintainer` + `.git`/remote
+ fallback "chủ repo trên máy mới chưa có `.maintainer` → hỏi xác nhận rồi tạo"). Một nguồn sự thật —
guard không lệch nhau.
- Không phải maintainer → DỪNG, nói nhẹ: *"Lệnh 'tiến hóa hệ thống' là của người DUY TRÌ app. Bạn đang
  dùng bản đã cài — góp ý thì gửi GitHub Issues, hoặc gõ **'cập nhật phiên bản'** để lấy bản mới."*
- Là maintainer → tiếp Bước 1.

## Bước 1 — Thu tín hiệu

Đọc và tổng hợp:
- `.kb/system-lessons.md` — bài học TẦNG QUY TRÌNH tích lũy (khác `.kb/lessons.md` là tầng tri thức).
- `CHANGELOG.md` — đã sửa gì ở các bản trước (tránh lặp).
- Bug/feedback user báo gần đây trong phiên + GitHub Issues nếu có.

## Bước 2 — Review đối kháng (cơ chế đã chứng minh)

Chạy **nhiều Agent song song** (hoặc Workflow tool nếu được phép) soi TOÀN BỘ
`workflows/*.md` + `CLAUDE.md` + `config/domain-presets/` (defaults ship sẵn — KHÔNG soi
`config/domain-rules.md` vì đó là DATA của user), mỗi agent một góc:
- Mẫu lỗi LẶP ở tầng quy trình (vd dùng AskUserQuestion cho input tự do → "Failed").
- Lỗ hổng / bước thiếu / mâu thuẫn giữa các workflow.
- Rule mơ hồ, dễ hiểu sai, hoặc còn dính dự án cụ thể (đáng lẽ chung).
- Tính nhất quán: trigger ↔ workflow ↔ guard ↔ release.
Mỗi agent trả về finding có cấu trúc (file + mục + severity + cách sửa).

## Bước 3 — Đề xuất + ✋ GATE

Tổng hợp findings → trình bày theo nhóm mức (critical/high/medium/low) + đề xuất sửa cụ thể.
User duyệt từng nhóm (làm tất / chọn / bỏ qua). KHÔNG tự sửa khi chưa duyệt.

## Bước 4 — Áp + ghi học + phát hành

1. Áp các sửa đã duyệt vào CORE: `workflows/`, `CLAUDE.md`, `config/domain-presets/`, `scripts/`,
   `tools/`… (KHÔNG sửa `config/domain-rules.md` — DATA của user; rule cần ship → bỏ vào preset).
2. Ghi 1 mục vào `.kb/system-lessons.md`: `## YYYY-MM-DD — <bối cảnh>` + sai gì / sửa gì / rút ra.
3. Vì đã đổi CORE → chuyển `workflows/12-release.md` **Luồng B** (đã biết là CORE), kèm gợi ý mức bump:
   chỉ vá rule mơ hồ = **patch**; thêm bước/khả năng workflow = **minor**; đổi cấu trúc bắt migrate = **major**.

## Guardrails
- **CHỈ maintainer** (Bước 0). User thường → không chạy, điều hướng sang lệnh người dùng.
- Mọi sửa **CORE** ⇒ **bump version** (qua workflow 12). Sửa chỉ `config/domain-rules.md` (DATA của user) ⇒ KHÔNG bump.
- Review đối kháng là **cổng chất lượng** — đừng tự tin sửa khi chưa có nhiều góc soi.
- Phân biệt rõ: `09-evolve.md` = tiến hóa TRI THỨC (KB) ↔ `13-evolve-system.md` = tiến hóa QUY TRÌNH
  (workflow/rule). Đừng lẫn.
