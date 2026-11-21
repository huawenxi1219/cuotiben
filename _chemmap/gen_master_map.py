# -*- coding: utf-8 -*-
"""把 chem_tree.json 渲染成一张超大总图（册 → 章 → 节 → 知识点），输出 SVG 与 PNG。"""
import io
import json

TREE = r"C:\myapp\assets\chem_tree.json"
SVG = r"C:\myapp\化学总图.svg"

tree = json.load(io.open(TREE, encoding="utf-8"))

# 版面
X_BOOK, X_CHAP, X_PT = 40, 300, 1180
BOOK_W, CHAP_W = 230, 840
LINE = 26
PAD = 16

COLORS = [("#17324F", "#7AA2F7"), ("#173D33", "#4DB6AC"), ("#33204A", "#BB9AF7"),
          ("#3D2E17", "#E0AF68"), ("#3F1B2A", "#F7768E"), ("#1E3A3A", "#2AC3A2")]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


blocks = []
y = 80
for bi, book in enumerate(tree["books"]):
    chaps = []
    book_h = 0
    for chap in book["chapters"]:
        h = 64
        for sec in chap["sections"]:
            h += LINE                      # 节标题
            h += len(sec["points"]) * LINE  # 知识点行
            h += 10
        h += PAD
        chaps.append((chap, y + book_h, h))
        book_h += h + 16
    blocks.append((bi, book, chaps, book_h, y))
    y += book_h + 40

H = y + 40
W = X_PT + 620

out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#15161E"/>',
       f'<text x="40" y="48" fill="#E8EBF5" font-size="28" font-weight="bold">'
       f'人教A版高中化学 · 章末知识体系总图</text>']

for bi, book, chaps, book_h, y0 in blocks:
    fill, stroke = COLORS[bi % len(COLORS)]
    by = y0 + book_h / 2 - 30
    out.append(f'<rect x="{X_BOOK}" y="{by}" width="{BOOK_W}" height="60" rx="14" '
               f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    out.append(f'<text x="{X_BOOK + BOOK_W / 2}" y="{by + 37}" fill="#F5F7FF" font-size="17" '
               f'text-anchor="middle">{esc(book["name"])}</text>')
    bx, byy = X_BOOK + BOOK_W, by + 30

    for chap, cy, ch in chaps:
        out.append(f'<rect x="{X_CHAP}" y="{cy}" width="{CHAP_W}" height="{ch}" rx="12" '
                   f'fill="#1B1F2E" stroke="{stroke}" stroke-width="1.4"/>')
        out.append(f'<text x="{X_CHAP + 14}" y="{cy + 28}" fill="#E8EBF5" font-size="17" '
                   f'font-weight="600">{esc(chap["name"])}</text>')
        out.append(f'<path d="M{bx},{byy} C{bx + 40},{byy} {X_CHAP - 60},{cy + ch / 2} '
                   f'{X_CHAP},{cy + ch / 2}" fill="none" stroke="{stroke}" stroke-width="2" '
                   f'opacity="0.65"/>')

        py = cy + 66
        for sec in chap["sections"]:
            out.append(f'<text x="{X_CHAP + 20}" y="{py}" fill="{stroke}" font-size="14" '
                       f'font-weight="600">{esc(sec["section"])}</text>')
            py += LINE
            for pt in sec["points"]:
                out.append(f'<circle cx="{X_CHAP + 26}" cy="{py - 5}" r="2.4" fill="{stroke}"/>')
                out.append(f'<text x="{X_CHAP + 38}" y="{py}" fill="#C9CFE0" font-size="13.5">'
                           f'{esc(pt["title"])}</text>')
                # 右侧第一/二条要点
                facts = pt.get("facts") or []
                if facts:
                    f0 = esc(facts[0])
                    if len(f0) > 34:
                        f0 = f0[:33] + "…"
                    out.append(f'<text x="{X_PT}" y="{py}" fill="#8A93A8" font-size="12">'
                               f'{f0}</text>')
                py += LINE
            py += 2
        py += 6

out.append("</svg>")
io.open(SVG, "w", encoding="utf-8", newline="\n").write("\n".join(out))
n = sum(len(s["points"]) for b in tree["books"] for c in b["chapters"] for s in c["sections"])
print(f"SVG {W}x{H} | 册 {len(tree['books'])} 章 "
      f"{sum(len(b['chapters']) for b in tree['books'])} 知识点 {n}")
