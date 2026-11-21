# -*- coding: utf-8 -*-
"""渲染总图：支持任意层级（册→章→节→点→子点），像书上那样逐级缩进。"""
import io
import json

TREE = r"C:\myapp\assets\chem_tree.json"
SVG = r"C:\myapp\化学总图.svg"

tree = json.load(io.open(TREE, encoding="utf-8"))

LINE = 26
X_BOOK, X_CHAP = 40, 300
BOOK_W, CHAP_W = 230, 1460
COLORS = [("#17324F", "#7AA2F7"), ("#173D33", "#4DB6AC"), ("#33204A", "#BB9AF7"),
          ("#3D2E17", "#E0AF68"), ("#3F1B2A", "#F7768E"), ("#1E3A3A", "#2AC3A2")]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def flatten(items, depth=0, acc=None):
    """把树拍平成 [(depth, title, facts_text)]"""
    if acc is None:
        acc = []
    for it in items:
        facts = it.get("facts") or []
        ftxt = ""
        if facts:
            ftxt = esc(facts[0])
            if len(facts) > 1:
                ftxt += f"（等 {len(facts)} 条）"
        acc.append(("PT", depth, it.get("title", ""), ftxt))
        flatten(it.get("sub") or [], depth + 1, acc)
    return acc


def count_nodes(items):
    n = 0
    for it in items:
        n += 1 + count_nodes(it.get("sub") or [])
    return n


blocks = []
y = 80
for bi, book in enumerate(tree["books"]):
    chaps = []
    bh = 0
    for chap in book["chapters"]:
        lines = []
        for sec in chap["sections"]:
            lines.append(("SEC", sec["section"]))
            lines.extend(flatten(sec["points"]))
        h = 46 + len(lines) * LINE + 18
        chaps.append((chap, y + bh, h, lines))
        bh += h + 16
    blocks.append((bi, book, chaps, bh, y))
    y += bh + 40

H = y + 40
W = X_CHAP + CHAP_W + 40

out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#15161E"/>',
       f'<text x="40" y="48" fill="#E8EBF5" font-size="28" font-weight="bold">'
       f'人教A版高中化学 · 章末知识体系总图（全层级）</text>']

for bi, book, chaps, bh, y0 in blocks:
    fill, stroke = COLORS[bi % len(COLORS)]
    by = y0 + bh / 2 - 30
    out.append(f'<rect x="{X_BOOK}" y="{by}" width="{BOOK_W}" height="60" rx="14" '
               f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    out.append(f'<text x="{X_BOOK + BOOK_W / 2}" y="{by + 37}" fill="#F5F7FF" font-size="17" '
               f'text-anchor="middle">{esc(book["name"])}</text>')
    bx, byy = X_BOOK + BOOK_W, by + 30

    for chap, cy, ch, lines in chaps:
        out.append(f'<rect x="{X_CHAP}" y="{cy}" width="{CHAP_W}" height="{ch}" rx="12" '
                   f'fill="#1B1F2E" stroke="{stroke}" stroke-width="1.4"/>')
        out.append(f'<text x="{X_CHAP + 14}" y="{cy + 28}" fill="#E8EBF5" font-size="17" '
                   f'font-weight="600">{esc(chap["name"])}</text>')
        out.append(f'<path d="M{bx},{byy} C{bx + 40},{byy} {X_CHAP - 60},{cy + ch / 2} '
                   f'{X_CHAP},{cy + ch / 2}" fill="none" stroke="{stroke}" stroke-width="2" '
                   f'opacity="0.6"/>')

        py = cy + 54
        for kind, *rest in lines:
            if kind == "SEC":
                out.append(f'<text x="{X_CHAP + 18}" y="{py}" fill="{stroke}" font-size="14" '
                           f'font-weight="600">{esc(rest[0])}</text>')
            else:
                depth, title, ftxt = rest
                x = X_CHAP + 30 + depth * 34
                if depth == 0:
                    out.append(f'<circle cx="{x - 10}" cy="{py - 5}" r="3" fill="{stroke}"/>')
                    out.append(f'<text x="{x}" y="{py}" fill="#E4E8F2" font-size="14" '
                               f'font-weight="600">{esc(title)}</text>')
                else:
                    out.append(f'<text x="{x - 12}" y="{py}" fill="{stroke}" font-size="12" '
                               f'opacity="0.7">·</text>')
                    out.append(f'<text x="{x}" y="{py}" fill="#C2C8D8" font-size="13.5">'
                               f'{esc(title)}</text>')
                if ftxt:
                    out.append(f'<text x="{X_CHAP + 760}" y="{py}" fill="#7E879C" '
                               f'font-size="12">{ftxt}</text>')
            py += LINE

out.append("</svg>")
io.open(SVG, "w", encoding="utf-8", newline="\n").write("\n".join(out))

tot = sum(count_nodes(s["points"]) for b in tree["books"] for c in b["chapters"] for s in c["sections"])
print(f"SVG {W}x{H} | 节点总数 {tot}")
