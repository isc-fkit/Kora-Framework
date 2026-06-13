# Workflow 09 — Tự tiến hóa Knowledge Base (self-evolving)

> Trigger: "tiến hóa KB", "dọn dẹp KB", "kiểm tra sức khỏe KB" (confirm ý định trước),
> hoặc tự chạy theo lịch (workflows/08 có thể gọi định kỳ).
>
> Đây là phần biến hệ thống từ "tích lũy tri thức" thành "tự tiến hóa": index không
> bao giờ lệch docs/, tự phát hiện lỗ hổng/mâu thuẫn/trùng lặp, và học từ phản hồi.

---

## A. Tái lập chỉ mục (BẮT BUỘC — nền tảng, chạy bằng máy, không tốn token)

Bất cứ khi nào `docs/` thay đổi (sau mỗi lần ghi tri thức ở workflow 02/03/05) hoặc
đầu mỗi phiên tiến hóa, chạy:

```bash
python3 tools/kb-indexer/build_index.py --root .
```

Script tự dựng lại `.kb/index.json` + `.kb/relation-graph.json` (gộp graph raw của
vault), và xuất `.kb/health-report.md`. Đây là cách giữ tri thức luôn khớp thực tế —
**không để index rỗng/cũ làm Claude trả lời chay**.

> Quy ước trong CLAUDE.md: SAU MỖI lần ghi vào `docs/` đã được duyệt → chạy lại lệnh
> này ngay (rẻ, tức thì). Không chờ đến phiên tiến hóa.

## B. Đọc & trình bày Health Report

Đọc `.kb/health-report.md`, trình bày cho user bằng tiếng Việt tự nhiên:
- Bao nhiêu tài liệu, node, quan hệ.
- **Dead links** (tham chiếu tới ID không tồn tại) → cần sửa.
- **Feature thiếu Business Rule / Acceptance Criteria** → lỗ hổng coverage.
- **Tài liệu lỗi thời** (quá ngưỡng ngày chưa sửa) → cần rà lại độ chính xác.

## C. Đề xuất tiến hóa (mỗi nhóm là một đề xuất có thể duyệt)

Dựa trên report + đọc các file liên quan, đề xuất (KHÔNG tự sửa):

1. **Sửa dead link** — tạo node còn thiếu hoặc sửa tham chiếu sai.
2. **Hợp nhất trùng lặp** — quét BR/AC/feature có nội dung gần giống (cùng màn hình,
   cùng rule) → đề xuất gộp thành một, cập nhật backlink, giữ lại bản chuẩn.
3. **Phát hiện mâu thuẫn** — BR mới vs BR cũ nói khác nhau; AC giữa 2 feature xung đột;
   feature vi phạm `config/domain-rules.md` → nêu rõ cặp mâu thuẫn, đề nghị user quyết.
4. **Bù lỗ hổng** — feature thiếu BR/AC → gợi ý bổ sung (hoặc đánh dấu `[CẦN XÁC NHẬN]`).
5. **Gom cụm** — nhiều feature liên quan chặt → đề xuất gộp thành Epic/megafeature.

## D. ✋ Approval Gate

Trình bày danh sách đề xuất, hỏi: [A] làm tất cả · [B] chọn mục · [C] bỏ qua.
Chỉ sửa `docs/` + vault sau khi duyệt → rồi chạy lại mục A (reindex) → ghi changelog.

## E. Học từ phản hồi (feedback loop) — ghi vào `.kb/lessons.md`

Khi một feature/design/code bị user reject hoặc phải sửa lớn, sau khi xử lý xong:
- Ghi 1 mục vào `.kb/lessons.md`: ngày — bối cảnh — "lần đầu sai gì" — "rút ra điều gì".
- Nếu là quyết định lớn → tạo ADR trong `docs/06-decisions/`.
- Lần sau ở workflow 03 (Bước 2 phân tích), Claude đọc `.kb/lessons.md` để KHÔNG lặp lỗi cũ.

> Đây là cốt lõi "tiến hóa": KB không chỉ lớn lên, mà còn **học từ thất bại** và
> ngày càng ít sai.

## F. Lịch tiến hóa (tùy chọn)

Hỏi user có muốn đặt lịch chạy mục A+B định kỳ (vd mỗi tuần) để nhận health report
tự động không → tạo scheduled task (như workflows/08), ghi `kb.evolve_schedule` vào config.
