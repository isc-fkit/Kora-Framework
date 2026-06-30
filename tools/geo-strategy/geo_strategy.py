#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo_strategy.py — Engine GEO (Generative Engine Optimization).

Nhận đánh giá per-content do Agent GEO Analyst sinh (reports/_geo-rows.json) → chấm 8 CHIỀU
(extractability/statistics/citations/schema/authority/offsite/freshness/technical, trọng số 100)
→ scorecard tổng + theo từng nội dung → DANH SÁCH VIỆC CẦN LÀM ưu tiên (effort×impact, bám CHIỀU yếu)
→ ROADMAP 1 năm (theo quý) + 5 năm (theo năm) → dashboard HTML + tiêu đề mail động (reports/_subject-latest.txt).

CHỈ thư viện chuẩn. Tiêu chí tổng hợp từ nghiên cứu GEO 2025–2026 (xem README.md, có trích nguồn).

Dùng:
  geo_strategy.py --rows reports/_geo-rows.json [--brand "FPT Medicare"] [--period 2026-Q2] [--out reports]
  geo_strategy.py --self-test
"""
import argparse
import datetime
import html
import json
import os
import sys

# ── 8 CHIỀU + trọng số (tổng 100) ──
GEO_DIMS = [
    ("extractability", "Cấu trúc & trích xuất (quick-answer · định nghĩa · TL;DR · FAQ · bảng)", 20),
    ("statistics",     "Số liệu gốc / nghiên cứu dữ liệu first-party", 15),
    ("citations",      "Trích dẫn nguồn uy tín & quotation (3–5/bài)", 15),
    ("authority",      "Authority / E-E-A-T (author bio · entity · outbound uy tín)", 15),
    ("schema",         "Schema JSON-LD xếp chồng (Article+FAQ+ItemList+Organization)", 10),
    ("offsite",        "Hiện diện off-site (Reddit · LinkedIn · Wikipedia · YouTube · Quora)", 10),
    ("technical",      "Technical / crawlability (HTTPS · tốc độ · llms.txt · cho AI-bot)", 10),
    ("freshness",      "Độ tươi (cập nhật theo quý · version history)", 5),
]
DIM_W = {k: w for k, _l, w in GEO_DIMS}
DIM_LABEL = {k: l for k, l, _w in GEO_DIMS}

# ── THƯ VIỆN HÀNH ĐỘNG: mỗi chiều → các việc, kèm effort/impact/horizon ──
# horizon: quick (Q1 / quick-win) · mid (Q2–Q3) · long (Q4+/đa năm)
ACTION_LIBRARY = {
    "extractability": [
        ("Thêm Quick-answer 40–80 từ ở ĐẦU mỗi trang top", "low", "high", "quick"),
        ("Mở mỗi mục bằng câu định-nghĩa-dẫn (definition-lead)", "low", "high", "quick"),
        ("Thêm TL;DR + bullet tóm tắt + bảng so sánh", "low", "med", "quick"),
        ("Tái cấu trúc pillar content theo Q&A / FAQ", "med", "high", "mid"),
    ],
    "statistics": [
        ("Chèn thống kê gốc + nguồn vào top content", "low", "high", "quick"),
        ("Xuất bản 1 nghiên cứu dữ liệu / whitepaper gốc (quý)", "high", "high", "mid"),
        ("Dựng cỗ máy nghiên cứu dữ liệu định kỳ (original research)", "high", "high", "long"),
    ],
    "citations": [
        ("Thêm 3–5 trích dẫn nguồn uy tín + quotation mỗi bài", "low", "high", "quick"),
        ("Liên kết tới framework/chuẩn ngành & first-party data", "med", "med", "mid"),
    ],
    "authority": [
        ("Viết author bio chi tiết + tín hiệu chuyên môn", "low", "med", "quick"),
        ("Liên kết thực thể (Wikipedia/Wikidata) + brand entity", "med", "high", "mid"),
        ("Định vị lãnh đạo là thought leader (PR/bài chuyên gia)", "high", "high", "long"),
        ("Earn citation từ ≥20 domain uy tín mỗi quý", "high", "high", "long"),
    ],
    "schema": [
        ("Triển khai JSON-LD: Article + FAQPage + Organization", "low", "med", "quick"),
        ("Xếp chồng schema theo loại trang (ItemList/HowTo/Product/Review)", "med", "med", "mid"),
    ],
    "offsite": [
        ("Tạo hiện diện Reddit/Quora đúng chủ đề (câu trả lời giá trị)", "med", "high", "mid"),
        ("Đăng nội dung LinkedIn/YouTube bám chủ đề lõi", "med", "med", "mid"),
        ("Hiện diện Wikipedia/entity nguồn AI hay trích", "high", "high", "long"),
    ],
    "technical": [
        ("Cho phép GPTBot·PerplexityBot·ClaudeBot·Google-Extended·BingBot (robots.txt)", "low", "high", "quick"),
        ("Thêm llms.txt + bật Agent Analytics theo dõi AI-bot crawl", "low", "med", "quick"),
        ("HTTPS toàn site + tối ưu tốc độ < 2.5s (lý tưởng < 1.8s)", "med", "med", "mid"),
    ],
    "freshness": [
        ("Lập lịch cập nhật top content theo QUÝ + version history", "low", "med", "quick"),
        ("Gỡ/cập nhật nội dung cũ, low-trust", "med", "med", "mid"),
    ],
}

# ── KHUNG ROADMAP (focus dims theo giai đoạn — engine sẽ chèn action thật) ──
ROADMAP_1Y = [
    ("Q1", "Audit + Quick-win", ["technical", "extractability", "schema"]),
    ("Q2", "Tái cấu trúc nội dung + số liệu gốc", ["extractability", "statistics", "citations"]),
    ("Q3", "Authority + Off-site", ["authority", "offsite", "citations"]),
    ("Q4", "Đo lường trưởng thành + lặp", ["freshness", "authority", "statistics"]),
]
ROADMAP_5Y = [
    ("Năm 1", "Nền tảng GEO", ["technical", "extractability", "schema", "citations"]),
    ("Năm 2", "Mở rộng cluster + entity authority", ["authority", "statistics", "offsite"]),
    ("Năm 3", "Dẫn đầu share-of-voice chủ đề lõi", ["authority", "offsite", "citations"]),
    ("Năm 4", "Đa-engine + mở rộng vùng/ngôn ngữ", ["offsite", "statistics", "technical"]),
    ("Năm 5", "Thống trị bền vững + hệ thống thích ứng", ["freshness", "authority", "statistics"]),
]

METRICS = [
    "AI Citation Rate — % prompt mà brand được AI nhắc",
    "Share of Voice — tỉ lệ xuất hiện so với đối thủ",
    "Inclusion Rate / Share of Answers",
    "Sentiment — mục tiêu ≥ 90% tích cực",
    "AI-attributed leads/traffic — mục tiêu +20% YoY",
    "Theo platform: ChatGPT · Perplexity · Google AI Overviews · Gemini · Claude · Copilot",
]


def die(msg):
    print(f"LỖI: {msg}", file=sys.stderr)
    sys.exit(1)


def esc(s):
    return html.escape(str(s if s is not None else ""))


def load_rows(path):
    if not os.path.exists(path):
        die(f"Không thấy file đánh giá GEO: {path}. Agent GEO Analyst phải sinh file này trước "
            f"(đọc nội dung → chấm 8 chiều 0–100 + liệt kê gap mỗi nội dung).")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    pieces = data.get("pieces") or []
    if not pieces:
        die("File _geo-rows.json không có 'pieces' (danh sách nội dung đã chấm).")
    return data


def _clamp(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, v))


def score_portfolio(data):
    """Trả per-dim trung bình, overall (0–100), per-piece overall, xếp hạng CHIỀU yếu (gap×weight)."""
    pieces = data["pieces"]
    dim_sum = {k: 0.0 for k, _l, _w in GEO_DIMS}
    per_piece = []
    for p in pieces:
        sc = p.get("scores") or {}
        wsum, piece_w = 0.0, 0.0
        for k, _l, w in GEO_DIMS:
            v = _clamp(sc.get(k, 0))
            dim_sum[k] += v
            wsum += v * w
            piece_w += w
        overall = round(wsum / piece_w, 1) if piece_w else 0.0
        per_piece.append({"id": p.get("id") or p.get("title") or "?",
                           "title": p.get("title") or p.get("id") or "?",
                           "url": p.get("url", ""), "overall": overall,
                           "scores": {k: _clamp(sc.get(k, 0)) for k, _l, _w in GEO_DIMS},
                           "gaps": p.get("gaps") or []})
    n = len(pieces)
    dim_avg = {k: round(dim_sum[k] / n, 1) for k in dim_sum}
    overall = round(sum(dim_avg[k] * DIM_W[k] for k in dim_avg) / 100.0, 1)
    # CHIỀU yếu: gap có trọng số = weight × (100 - avg) → cao = ưu tiên
    weak = sorted(GEO_DIMS, key=lambda d: -(d[2] * (100 - dim_avg[d[0]])))
    weak_rank = [{"key": k, "label": l, "weight": w, "avg": dim_avg[k],
                  "gap_weighted": round(w * (100 - dim_avg[k]) / 100.0, 1)} for k, l, w in weak]
    per_piece.sort(key=lambda x: x["overall"])
    return {"dim_avg": dim_avg, "overall": overall, "per_piece": per_piece,
            "weak_rank": weak_rank, "n": n, "brand": data.get("brand", ""),
            "period": data.get("period", ""), "competitors": data.get("competitors") or [],
            "notes": data.get("overall_notes", "")}


_EFFORT_ORD = {"low": 0, "med": 1, "high": 2}
_IMPACT_ORD = {"high": 0, "med": 1, "low": 2}
_HOR_ORD = {"quick": 0, "mid": 1, "long": 2}


def prioritize_actions(port, limit=24):
    """Danh sách việc ưu tiên: bám CHIỀU yếu (gap×weight) → impact cao → effort thấp → quick trước."""
    actions = []
    weak_order = {d["key"]: i for i, d in enumerate(port["weak_rank"])}
    for dim, items in ACTION_LIBRARY.items():
        for title, effort, impact, horizon in items:
            actions.append({"dim": dim, "dim_label": DIM_LABEL[dim], "title": title,
                            "effort": effort, "impact": impact, "horizon": horizon,
                            "dim_avg": port["dim_avg"][dim],
                            "_rank": (weak_order.get(dim, 9), _IMPACT_ORD[impact],
                                      _EFFORT_ORD[effort], _HOR_ORD[horizon])})
    actions.sort(key=lambda a: a["_rank"])
    for a in actions:
        a.pop("_rank", None)
    return actions[:limit]


def _phase_actions(focus_dims, port, k=3):
    out = []
    for dim in focus_dims:
        items = sorted(ACTION_LIBRARY.get(dim, []), key=lambda x: (_HOR_ORD[x[3]], _IMPACT_ORD[x[2]], _EFFORT_ORD[x[1]]))
        for title, effort, impact, horizon in items[:k]:
            out.append({"dim": dim, "dim_label": DIM_LABEL[dim], "title": title,
                        "effort": effort, "impact": impact})
    return out


def build_roadmap(port):
    one = [{"phase": ph, "theme": th, "focus": [DIM_LABEL[d] for d in dims],
            "actions": _phase_actions(dims, port, 2)} for ph, th, dims in ROADMAP_1Y]
    five = [{"phase": ph, "theme": th, "focus": [DIM_LABEL[d] for d in dims],
             "actions": _phase_actions(dims, port, 2)} for ph, th, dims in ROADMAP_5Y]
    return {"one_year": one, "five_year": five}


# ───────────────────────── RENDER HTML ─────────────────────────
_PAL = {"deep": "#0b2a5e", "accent": "#1f7a4d", "warn": "#d98a00", "risk": "#c0392b",
        "ink": "#1d2733", "mut": "#5b6b7d", "card": "#ffffff", "bg": "#eef2f7"}


def _score_color(v):
    return _PAL["accent"] if v >= 70 else (_PAL["warn"] if v >= 40 else _PAL["risk"])


def _eff_chip(effort, impact):
    em = {"low": "Dễ", "med": "Vừa", "high": "Khó"}[effort]
    im = {"high": "Tác động CAO", "med": "Tác động vừa", "low": "Tác động thấp"}[impact]
    bg = _PAL["accent"] if impact == "high" else (_PAL["warn"] if impact == "med" else _PAL["mut"])
    return (f'<span style="background:{bg};color:#fff;border-radius:999px;padding:1px 8px;font-size:11px;'
            f'font-weight:700;white-space:nowrap">{im} · {em}</span>')


def render_html(port, actions, roadmap, gen):
    dim_bars = ""
    for k, label, w in GEO_DIMS:
        v = port["dim_avg"][k]
        dim_bars += (
            f'<div style="margin:7px 0"><div style="display:flex;justify-content:space-between;font-size:13px;color:{_PAL["ink"]}">'
            f'<span><b>{esc(label)}</b> <span style="color:{_PAL["mut"]}">({w}%)</span></span>'
            f'<span style="font-weight:800;color:{_score_color(v)}">{v:.0f}/100</span></div>'
            f'<div style="background:#e6ebf2;border-radius:999px;height:9px;overflow:hidden;margin-top:3px">'
            f'<div style="width:{v:.0f}%;height:9px;background:{_score_color(v)}"></div></div></div>')

    act_rows = ""
    for i, a in enumerate(actions, 1):
        act_rows += (
            f'<tr><td style="padding:6px 8px;color:{_PAL["mut"]}">{i}</td>'
            f'<td style="padding:6px 8px"><b>{esc(a["title"])}</b><div style="font-size:11.5px;color:{_PAL["mut"]}">'
            f'{esc(a["dim_label"])} · điểm chiều {a["dim_avg"]:.0f}/100</div></td>'
            f'<td style="padding:6px 8px;text-align:right">{_eff_chip(a["effort"], a["impact"])}</td>'
            f'<td style="padding:6px 8px;text-align:center;font-size:11.5px;color:{_PAL["mut"]}">'
            f'{ {"quick":"Quick-win","mid":"Trung hạn","long":"Dài hạn"}[a["horizon"]] }</td></tr>')

    def roadmap_cards(items):
        out = ""
        for r in items:
            acts = "".join(f'<li style="margin:2px 0">{esc(a["title"])} '
                           f'<span style="color:{_PAL["mut"]};font-size:11px">({esc(a["dim_label"].split(" ")[0])})</span></li>'
                           for a in r["actions"])
            out += (f'<div style="border:1px solid #dce3ec;border-radius:10px;padding:12px 14px;margin:8px 0;background:#fafcff">'
                    f'<div style="font-weight:800;color:{_PAL["deep"]}">{esc(r["phase"])} — {esc(r["theme"])}</div>'
                    f'<div style="font-size:12px;color:{_PAL["mut"]};margin:3px 0 6px">Trọng tâm: {esc(" · ".join(d.split(" ")[0] for d in r["focus"]))}</div>'
                    f'<ul style="margin:0;padding-left:18px;font-size:12.5px;color:{_PAL["ink"]}">{acts}</ul></div>')
        return out

    piece_rows = ""
    for p in port["per_piece"][:30]:
        gaps = ", ".join(esc(g) for g in p["gaps"][:4]) or "—"
        piece_rows += (
            f'<tr><td style="padding:5px 8px"><b>{esc(p["title"])}</b></td>'
            f'<td style="padding:5px 8px;text-align:center;font-weight:800;color:{_score_color(p["overall"])}">{p["overall"]:.0f}</td>'
            f'<td style="padding:5px 8px;font-size:12px;color:{_PAL["mut"]}">{gaps}</td></tr>')

    metrics = "".join(f'<li style="margin:2px 0">{esc(m)}</li>' for m in METRICS)
    comp = (f'<div style="font-size:12.5px;color:{_PAL["mut"]};margin-top:4px">Đối thủ theo dõi share-of-voice: '
            f'{esc(" · ".join(port["competitors"]))}</div>') if port["competitors"] else ""
    ov = port["overall"]
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>GEO Strategy — {esc(port['brand'])}</title></head>
<body style="margin:0;background:{_PAL['bg']};font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;color:{_PAL['ink']}">
<div style="max-width:880px;margin:0 auto;padding:18px 14px">
  <div style="background:linear-gradient(135deg,{_PAL['deep']},#15428f);color:#fff;border-radius:14px;padding:20px 22px">
    <div style="font-size:12px;letter-spacing:.06em;text-transform:uppercase;opacity:.85">Generative Engine Optimization</div>
    <div style="font-size:22px;font-weight:800;margin-top:2px">Chiến lược GEO — {esc(port['brand'] or 'Thương hiệu')}</div>
    <div style="font-size:12.5px;opacity:.9;margin-top:3px">{esc(port['period'])} · {port['n']} nội dung · tạo {esc(gen)} (UTC)</div>
  </div>
  <div style="display:flex;gap:12px;flex-wrap:wrap;margin:14px 0">
    <div style="flex:1;min-width:180px;background:{_PAL['card']};border-radius:12px;padding:16px;text-align:center">
      <div style="font-size:12px;color:{_PAL['mut']}">ĐIỂM GEO TỔNG</div>
      <div style="font-size:40px;font-weight:900;color:{_score_color(ov)}">{ov:.0f}<span style="font-size:18px;color:{_PAL['mut']}">/100</span></div>
      <div style="font-size:12px;color:{_PAL['mut']}">{'Tốt' if ov>=70 else ('Cần cải thiện' if ov>=40 else 'Yếu — ưu tiên cao')}</div>
    </div>
    <div style="flex:2;min-width:280px;background:{_PAL['card']};border-radius:12px;padding:14px 16px">
      <div style="font-weight:800;margin-bottom:6px">Điểm theo 8 chiều</div>{dim_bars}
    </div>
  </div>
  <div style="background:{_PAL['card']};border-radius:12px;padding:14px 16px;margin-bottom:14px">
    <div style="font-weight:800;margin-bottom:6px">🎯 Việc cần làm để TĂNG GEO (ưu tiên theo chiều yếu × tác động)</div>
    <table style="width:100%;border-collapse:collapse;font-size:13px"><tr style="color:{_PAL['mut']};text-align:left;border-bottom:1px solid #e6ebf2">
      <th style="padding:4px 8px">#</th><th style="padding:4px 8px">Hành động</th><th style="padding:4px 8px;text-align:right">Ưu tiên</th><th style="padding:4px 8px;text-align:center">Mốc</th></tr>
      {act_rows}</table>
  </div>
  <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px">
    <div style="flex:1;min-width:300px;background:{_PAL['card']};border-radius:12px;padding:14px 16px">
      <div style="font-weight:800;margin-bottom:4px">🗓️ Roadmap 1 năm (theo quý)</div>{roadmap_cards(roadmap['one_year'])}</div>
    <div style="flex:1;min-width:300px;background:{_PAL['card']};border-radius:12px;padding:14px 16px">
      <div style="font-weight:800;margin-bottom:4px">🧭 Roadmap 5 năm (theo năm)</div>{roadmap_cards(roadmap['five_year'])}</div>
  </div>
  <div style="background:{_PAL['card']};border-radius:12px;padding:14px 16px;margin-bottom:14px">
    <div style="font-weight:800;margin-bottom:6px">📄 Nội dung GEO yếu nhất (ưu tiên xử lý trước)</div>
    <table style="width:100%;border-collapse:collapse;font-size:13px"><tr style="color:{_PAL['mut']};text-align:left;border-bottom:1px solid #e6ebf2">
      <th style="padding:4px 8px">Nội dung</th><th style="padding:4px 8px;text-align:center">Điểm</th><th style="padding:4px 8px">Gap chính</th></tr>{piece_rows}</table>
  </div>
  <div style="background:{_PAL['card']};border-radius:12px;padding:14px 16px">
    <div style="font-weight:800;margin-bottom:6px">📊 Đo lường (theo dõi liên tục)</div>
    <ul style="margin:0;padding-left:18px;font-size:13px">{metrics}</ul>{comp}
  </div>
</div></body></html>"""


def write_outputs(port, actions, roadmap, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    gen = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    html_out = render_html(port, actions, roadmap, gen)
    latest = os.path.join(out_dir, "geo-strategy-latest.html")
    with open(latest, "w", encoding="utf-8") as f:
        f.write(html_out)
    data_out = {"overall": port["overall"], "dim_avg": port["dim_avg"], "weak_rank": port["weak_rank"],
                "actions": actions, "roadmap": roadmap, "metrics": METRICS,
                "brand": port["brand"], "period": port["period"], "n": port["n"],
                "weakest_pieces": port["per_piece"][:30]}
    with open(os.path.join(out_dir, "geo-strategy-latest.json"), "w", encoding="utf-8") as f:
        json.dump(data_out, f, ensure_ascii=False, indent=2)
    # tiêu đề mail động (KHÔNG [Kora]) — đồng bộ cơ chế _subject-latest.txt
    subj = "Chiến lược GEO"
    if port["brand"]:
        subj += f" — {port['brand']}"
    if port["period"]:
        subj += f" — {port['period']}"
    with open(os.path.join(out_dir, "_subject-latest.txt"), "w", encoding="utf-8") as f:
        f.write(subj)
    return latest, data_out


def self_test():
    sample = {"brand": "FPT Medicare", "period": "2026-Q2", "competitors": ["Đối thủ A", "Đối thủ B"],
              "overall_notes": "Mẫu self-test.",
              "pieces": [
                  {"id": "blog/insulin", "title": "Hướng dẫn theo dõi insulin",
                   "scores": {"extractability": 30, "statistics": 10, "citations": 0, "authority": 40,
                              "schema": 0, "offsite": 20, "technical": 60, "freshness": 50},
                   "gaps": ["không có quick-answer", "thiếu số liệu gốc", "không FAQ schema"]},
                  {"id": "landing/app", "title": "Trang giới thiệu app",
                   "scores": {"extractability": 70, "statistics": 40, "citations": 30, "authority": 60,
                              "schema": 50, "offsite": 40, "technical": 80, "freshness": 70},
                   "gaps": ["thiếu trích dẫn nguồn"]},
              ]}
    port = score_portfolio(sample)
    actions = prioritize_actions(port)
    roadmap = build_roadmap(port)
    assert 0 <= port["overall"] <= 100, "overall ngoài [0,100]"
    # piece yếu hơn phải đứng trước (sort tăng theo overall)
    assert port["per_piece"][0]["overall"] <= port["per_piece"][-1]["overall"], "sort per_piece sai"
    # citations toàn 0–30 → phải nằm nhóm chiều yếu đầu; action #1 phải thuộc 1 chiều yếu nhất
    weak_keys = [d["key"] for d in port["weak_rank"][:4]]
    assert actions[0]["dim"] in weak_keys, "action ưu tiên không bám chiều yếu"
    assert len(roadmap["one_year"]) == 4 and len(roadmap["five_year"]) == 5, "roadmap thiếu giai đoạn"
    assert all(0 <= v <= 100 for v in port["dim_avg"].values()), "dim_avg ngoài [0,100]"
    print("✓ self-test OK")
    print(f"  overall={port['overall']} · chiều yếu nhất={port['weak_rank'][0]['key']} "
          f"({port['weak_rank'][0]['avg']:.0f}/100) · #actions={len(actions)}")
    print(f"  action#1: {actions[0]['title']} [{actions[0]['dim']}]")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", help="reports/_geo-rows.json (Agent GEO Analyst sinh).")
    ap.add_argument("--brand", default="")
    ap.add_argument("--period", default="")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--self-test", action="store_true", dest="self_test")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.rows:
        die("Cần --rows reports/_geo-rows.json (hoặc --self-test).")
    data = load_rows(args.rows)
    if args.brand:
        data["brand"] = args.brand
    if args.period:
        data["period"] = args.period
    port = score_portfolio(data)
    actions = prioritize_actions(port)
    roadmap = build_roadmap(port)
    latest, _ = write_outputs(port, actions, roadmap, args.out)
    print(f"✓ GEO strategy: {latest}")
    print(f"  Điểm GEO tổng: {port['overall']:.0f}/100 · {port['n']} nội dung · "
          f"chiều yếu nhất: {DIM_LABEL[port['weak_rank'][0]['key']].split(' ')[0]} ({port['weak_rank'][0]['avg']:.0f})")
    print(f"  {len(actions)} việc ưu tiên · roadmap 1 năm (4 quý) + 5 năm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
