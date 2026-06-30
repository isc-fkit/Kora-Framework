# GEO Strategy — Generative Engine Optimization

Bộ công cụ giúp framework **phân tích GEO** (tối ưu để thương hiệu/nội dung được các AI engine
như **ChatGPT · Perplexity · Google AI Overviews · Gemini · Claude · Copilot** trích dẫn & gợi ý),
dựng **roadmap 1 năm / 5 năm**, rồi **lên chiến dịch tự động** (`claude-knowledge-campaign`) theo roadmap.

> GEO ≠ SEO truyền thống: mục tiêu không phải thứ hạng trang kết quả, mà là **được AI trích làm nguồn**.

## 8 CHIỀU CHẤM ĐIỂM GEO (trọng số — tổng 100)

| Chiều | Trọng số | Nội dung (best-practice tổng hợp 2025–2026) |
|---|---|---|
| **Extractability / Cấu trúc** | 20 | Quick-answer 40–80 từ ở đầu trang; câu định-nghĩa-dẫn (definition-lead); TL;DR + bullet; bảng so sánh; FAQ/Q&A. *AI Overviews trích từ 30% đầu nội dung ~55% số lần.* |
| **Statistics / Số liệu gốc** | 15 | Thống kê gốc, nghiên cứu dữ liệu, first-party data. *"Statistics Addition" là 1 trong các phương pháp tăng visibility mạnh nhất (arXiv GEO study).* |
| **Citations & Quotations** | 15 | 3–5 trích dẫn nguồn uy tín / bài + quotation. *Trích dẫn tăng AI visibility tới ~40%.* |
| **Schema / Dữ liệu cấu trúc** | 10 | JSON-LD xếp chồng: Article + FAQPage + ItemList + Organization (+ HowTo/Product/Review). |
| **Authority / E-E-A-T** | 15 | Author bio + chuyên môn; liên kết thực thể (Wikipedia/Wikidata); outbound tới nguồn uy tín; brand entity. |
| **Off-site presence** | 10 | Reddit · LinkedIn · YouTube · Quora · Wikipedia. *Semrush 1/2026: Reddit & LinkedIn là 2 domain được trích nhiều nhất.* |
| **Freshness / Độ tươi** | 5 | Cập nhật theo quý + version history. *Trang không cập nhật mất citation nhanh gấp 3 lần.* |
| **Technical / Crawlability** | 10 | HTTPS; tốc độ < 2.5s (lý tưởng < 1.8s); `llms.txt`; robots.txt cho **GPTBot · PerplexityBot · ClaudeBot · Google-Extended · BingBot**. |

## ĐO LƯỜNG (metrics)
- **AI Citation Rate** — % prompt mà brand được AI nhắc.
- **Share of Voice** — tỉ lệ xuất hiện so với đối thủ.
- **Inclusion Rate / Share of Answers** · **Sentiment** (mục tiêu ≥ 90% tích cực).
- Per-platform: ChatGPT · Perplexity · Google AI Overviews · Gemini · Claude · Copilot.
- **AI-attributed leads/traffic** (mục tiêu +20% YoY) · Citation count + citation score.

## KHÁC BIỆT THEO PLATFORM (citation logic)
- **ChatGPT** — đồng thuận + nguồn tổng hợp toàn diện; Bing-indexed; authority kiểu Wikipedia.
- **Perplexity** — độ tươi + thảo luận cộng đồng + nguồn theo từng claim; real-time.
- **Google AI Overviews** — chồng lên ranking organic; E-E-A-T + Knowledge Graph entity là điều kiện cần.

## ROADMAP CHUẨN
- **1 năm (theo quý):** Q1 audit + quick-win (cấu trúc top content · schema · crawlability · llms.txt · baseline đo) → Q2 restructure pillar + nghiên cứu dữ liệu gốc #1 → Q3 authority + off-site (PR, citation, Reddit/LinkedIn/Wikipedia, E-E-A-T) → Q4 trưởng thành đo lường (share-of-voice, benchmark đối thủ, sentiment) + lặp.
- **5 năm (theo năm):** Y1 nền tảng → Y2 mở rộng cluster + entity authority → Y3 dẫn đầu share-of-voice chủ đề lõi → Y4 đa-engine + mở rộng vùng/ngôn ngữ + cỗ máy nghiên cứu gốc → Y5 thống trị bền vững + hệ thống thích ứng (tự giám sát thay đổi AI engine).

## Nguồn (truy vết)
- arXiv 2311.09735 — "GEO: Generative Engine Optimization" (nghiên cứu gốc; Cite Sources/Quotation/Statistics Addition tăng visibility tới ~40%).
- Profound — 10-step GEO framework 2025 (llms.txt, AI-bot crawl, metrics, phasing).
- Backlinko · Frase · Directive · GenOptima · Manhattan Strategies — GEO best-practice guides 2025–2026.
- Google Search Central — AI optimization guide (E-E-A-T, structured data).
- Semrush Enterprise AIO / SE Ranking / HubSpot AEO — đo share-of-voice & citation (1/2026).

## File
- `geo_strategy.py` — engine: chấm 8 chiều từ đánh giá per-content của Agent GEO Analyst → scorecard + action-list ưu tiên (effort×impact) → roadmap 1y/5y → dashboard HTML + tiêu đề mail động. `--self-test`.
- Đầu vào `reports/_geo-rows.json` do **Agent GEO Analyst** sinh (đọc nội dung thật, chấm từng chiều + liệt kê gap).
