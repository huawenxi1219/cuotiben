# -*- coding: utf-8 -*-
"""缩进树 + 折线连接（教辅式导图）。

- 每个节点一行，按层级缩进
- 父子用直角折线连接，结构上不可能交叉
- 说明文字作为子行（灰色），不再甩到右边一列
"""
import io
import json

TREE = r"C:\myapp\assets\chem_tree.json"
SVG = r"C:\myapp\化学总图.svg"

LINE = 24
PAD_L = 30
INDENT = 24
W = 1500
COLORS = ["#2563EB", "#0D9488", "#7C3AED", "#B45309", "#DC2626", "#0F766E"]

tree = json.load(io.open(TREE, encoding="utf-8"))


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


rows = []  # dict(idx, depth, kind, text, ci)


def emit(text, depth, kind, ci):
    rows.append({"depth": depth, "kind": kind, "text": str(text), "ci": ci,
                 "idx": len(rows), "start": len(rows), "end": len(rows)})


def walk(items, depth, ci):
    first = len(rows)
    for it in items:
        node = {"depth": depth, "kind": "pt", "text": it.get("title", ""), "ci": ci,
                "idx": len(rows), "start": len(rows), "end": len(rows)}
        rows.append(node)
        sub_start = len(rows)
        walk(it.get("sub") or [], depth + 1, ci)
        for f in it.get("facts") or []:
            emit(f, depth + 1, "fact", ci)
        node["end"] = len(rows) - 1
        node["has_child"] = len(rows) > sub_start


for bi, book in enumerate(tree["books"]):
    ci = bi % len(COLORS)
    emit(book["name"], 0, "book", ci)
    book_node = rows[-1]
    for chap in book["chapters"]:
        emit(chap["name"], 1, "chap", ci)
        chap_node = rows[-1]
        for sec in chap["sections"]:
            emit(sec["section"], 2, "sec", ci)
            sec_node = rows[-1]
            walk(sec["points"], 3, ci)
            sec_node["end"] = len(rows) - 1
        chap_node["end"] = len(rows) - 1
    book_node["end"] = len(rows) - 1

H = 96 + len(rows) * LINE + 40
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
       f'<text x="{PAD_L}" y="48" fill="#111827" font-size="24" font-weight="bold">'
       f'人教A版高中化学 · 章末知识体系</text>']


def y_of(i):
    return 92 + i * LINE


def x_of(d):
    return PAD_L + d * INDENT


def tw(s, fs):
    return sum(fs * (1.0 if ord(c) > 127 else 0.56) for c in str(s))


def fit(s, fs, maxw):
    s = str(s)
    if tw(s, fs) <= maxw:
        return s
    while s and tw(s + "…", fs) > maxw:
        s = s[:-1]
    return s + "…"


# 折线：每个父节点在子级缩进处画一条竖导轨，再横接到每个直接子节点
for n in rows:
    if n["end"] <= n["idx"]:
        continue
    col = COLORS[n["ci"]]
    rail = x_of(n["depth"] + 1) - 13
    kids = [m for m in rows[n["idx"] + 1:n["end"] + 1] if m["depth"] == n["depth"] + 1]
    if not kids:
        continue
    y0, y1 = y_of(kids[0]["idx"]), y_of(kids[-1]["idx"])
    out.append(f'<path d="M{rail},{y0} L{rail},{y1}" stroke="{col}" stroke-width="1.1" '
               f'opacity="0.5" fill="none"/>')
    for m in kids:
        cy = y_of(m["idx"])
        out.append(f'<path d="M{rail},{cy} L{x_of(n["depth"] + 1) - 3},{cy}" stroke="{col}" '
                   f'stroke-width="1.1" opacity="0.5" fill="none"/>')

for n in rows:
    y = y_of(n["idx"])
    x = x_of(n["depth"])
    col = COLORS[n["ci"]]
    if n["kind"] == "book":
        out.append(f'<rect x="{x - 8}" y="{y - 16}" width="{min(520, tw(n["text"], 17) + 22)}" '
                   f'height="24" rx="5" fill="{col}" opacity="0.14"/>')
        out.append(f'<text x="{x}" y="{y}" fill="{col}" font-size="17" font-weight="bold">'
                   f'{esc(n["text"])}</text>')
    elif n["kind"] == "chap":
        out.append(f'<text x="{x}" y="{y}" fill="#111827" font-size="15" font-weight="600">'
                   f'{esc(n["text"])}</text>')
    elif n["kind"] == "sec":
        out.append(f'<text x="{x}" y="{y}" fill="{col}" font-size="13.5" font-weight="600">'
                   f'{esc(n["text"])}</text>')
    elif n["kind"] == "fact":
        out.append(f'<text x="{x}" y="{y}" fill="#6B7280" font-size="12">'
                   f'{esc(fit(n["text"], 12, W - x - 30))}</text>')
    else:
        out.append(f'<text x="{x}" y="{y}" fill="#1F2937" font-size="13">'
                   f'{esc(fit(n["text"], 13, W - x - 30))}</text>')

out.append("</svg>")
io.open(SVG, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print(f"SVG {W}x{H} | 行数 {len(rows)}")
