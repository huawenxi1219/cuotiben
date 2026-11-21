# -*- coding: utf-8 -*-
"""真正的思维导图渲染器（树状布局 + 贝塞尔连线）。

- 根在左中，向右逐级展开
- 每个节点是紧凑标签，不再是大方块塞文字
- 同级节点纵向堆叠，父节点垂直居中于子节点
- 输出 SVG（矢量），可再转 PNG
"""
import json
import math


class Node:
    __slots__ = ("title", "detail", "children", "depth", "x", "y", "w", "h", "nh", "color", "kind")

    def __init__(self, title, depth=0, kind="pt", color=None, detail=""):
        self.title = title
        self.detail = detail or ""
        self.children = []
        self.depth = depth
        self.x = self.y = 0
        self.w = self.h = self.nh = 0
        self.kind = kind
        self.color = color


FONT = 13
FONT_ROOT = 20
FONT_L1 = 15
V_GAP = 12
H_GAP = 46
PAD_X = 12
PAD_Y = 8


def text_w(s, size):
    """粗略估算：中文按 1 个字宽，英文/数字按 0.56 字宽。"""
    w = 0.0
    for ch in s:
        w += size * (1.0 if ord(ch) > 127 else 0.56)
    return w


def build(tree):
    root = Node("化学", 0, "root")
    for bi, book in enumerate(tree["books"]):
        b = Node(book["name"], 1, "book", bi)
        root.children.append(b)
        for chap in book["chapters"]:
            c = Node(chap["name"], 2, "chap", bi)
            b.children.append(c)
            for sec in chap["sections"]:
                s = Node(sec["section"], 3, "sec", bi)
                c.children.append(s)
                for pt in sec["points"]:
                    p = Node(pt.get("title", ""), 4, "pt", bi, pt.get("detail", ""))
                    s.children.append(p)
                    for sub in pt.get("sub") or []:
                        _add_sub(p, sub, 5, bi)

    return root


def _add_sub(parent, item, depth, bi):
    n = Node(item.get("title", ""), depth, "pt", bi, item.get("detail", ""))
    parent.children.append(n)
    for sub in item.get("sub") or []:
        _add_sub(n, sub, depth + 1, bi)



def size_node(n):
    size = FONT_ROOT if n.kind == "root" else (FONT_L1 if n.depth <= 2 else FONT)
    n.w = text_w(n.title, size) + PAD_X * 2
    n.nh = size + PAD_Y * 2
    n.h = n.nh


def measure(n):
    """后序遍历：算高度、每层最大宽度"""
    size_node(n)
    for c in n.children:
        measure(c)
    if n.children:
        ch = sum(c.h for c in n.children) + V_GAP * (len(n.children) - 1)
        n.h = max(n.h, ch)
    return n.h


def assign(n, x, y_top, maxw):
    n.x = x
    n.y = y_top + n.h / 2
    if not n.children:
        return
    total = sum(c.h for c in n.children) + V_GAP * (len(n.children) - 1)
    cy = n.y - total / 2
    nx = x + maxw[n.depth + 1] + H_GAP if n.depth + 1 < len(maxw) else x + n.w + H_GAP
    for c in n.children:
        assign(c, nx, cy, maxw)
        cy += c.h + V_GAP


def collect_maxw(n, maxw):
    if n.depth >= len(maxw):
        maxw.extend([0] * (n.depth - len(maxw) + 1))
    maxw[n.depth] = max(maxw[n.depth], n.w)
    for c in n.children:
        collect_maxw(c, maxw)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


PALETTE = ["#7AA2F7", "#4DB6AC", "#BB9AF7", "#E0AF68", "#F7768E", "#2AC3A2",
           "#89DDFF", "#FFB86C"]


def render(root, path):
    measure(root)
    maxw = []
    collect_maxw(root, maxw)
    assign(root, 40, 40, maxw)

    # 边界
    xs, ys = [], []
    def walk(n):
        xs.extend([n.x, n.x + n.w])
        ys.extend([n.y - n.h / 2, n.y + n.h / 2])
        for c in n.children:
            walk(c)
    walk(root)
    W = int(max(xs) + 60)
    H = int(max(ys) + 60)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
           f'<rect width="{W}" height="{H}" fill="#14151C"/>']

    def rgb(hexs):
        h = hexs.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def mix(c1, c2, t):
        a, b = rgb(c1), rgb(c2)
        return "#%02X%02X%02X" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    def draw_edges(n):
        col = PALETTE[n.color % len(PALETTE)] if isinstance(n.color, int) else "#5A6478"
        for c in n.children:
            x1, y1 = n.x + n.w, n.y
            x2, y2 = c.x, c.y
            cx = (x1 + x2) / 2
            width = max(1.2, 3.2 - n.depth * 0.45)
            out.append(f'<path d="M{x1:.1f},{y1:.1f} C{cx:.1f},{y1:.1f} {cx:.1f},{y2:.1f} '
                       f'{x2:.1f},{y2:.1f}" fill="none" stroke="{col}" stroke-width="{width:.1f}" '
                       f'opacity="{max(0.28, 0.85 - n.depth * 0.1):.2f}"/>')
            draw_edges(c)

    draw_edges(root)

    def draw_nodes(n):
        col = PALETTE[n.color % len(PALETTE)] if isinstance(n.color, int) else "#8892A6"
        if n.kind == "root":
            fill, stroke, tcol, fs = "#2B4C7E", "#9CC0FF", "#FFFFFF", FONT_ROOT
        elif n.kind == "book":
            fill, stroke, tcol, fs = col, col, "#0E1220", FONT_L1
        elif n.kind == "chap":
            fill, stroke, tcol, fs = "#1E2230", col, "#E6EAF5", FONT_L1
        elif n.kind == "sec":
            fill, stroke, tcol, fs = "#1B1F2E", mix(col, "#000000", 0.35), "#C7CEDE", FONT
        elif n.kind == "fact":
            fill, stroke, tcol, fs = "none", "none", "#8A93A8", FONT - 1
        else:
            fill, stroke, tcol, fs = "#20242F", mix(col, "#000000", 0.25), "#DDE2EE", FONT

        if n.kind == "fact":
            out.append(f'<text x="{n.x + 2}" y="{n.y + 4}" fill="{tcol}" font-size="{fs}">'
                       f'{esc(n.title)}</text>')
        else:
            r = 8 if n.kind != "book" else 14
            out.append(f'<rect x="{n.x}" y="{n.y - n.h / 2}" width="{n.w}" height="{n.h}" rx="{r}" '
                       f'fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
            out.append(f'<text x="{n.x + PAD_X}" y="{n.y + fs * 0.36}" fill="{tcol}" '
                       f'font-size="{fs}">{esc(n.title)}</text>')
        for c in n.children:
            draw_nodes(c)

    draw_nodes(root)
    out.append("</svg>")
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    return W, H, sum(1 for _ in walk_count(root))


def walk_count(n):
    yield n
    for c in n.children:
        yield from walk_count(c)


def render_books(tree, path):
    roots = []
    for bi, book in enumerate(tree["books"]):
        b = Node(book["name"], 0, "book", bi)
        for chap in book["chapters"]:
            c = Node(chap["name"], 1, "chap", bi)
            b.children.append(c)
            for sec in chap["sections"]:
                s = Node(sec["section"], 2, "sec", bi)
                c.children.append(s)
                for pt in sec["points"]:
                    p = Node(pt.get("title", ""), 3, "pt", bi)
                    s.children.append(p)
                    for sub in pt.get("sub") or []:
                        _add_sub(p, sub, 4, bi)
        roots.append(b)

    cur_x = 40
    max_h = 0
    for b in roots:
        measure(b)
        maxw = []
        collect_maxw(b, maxw)
        assign(b, cur_x, 40, maxw)
        # 宽度
        xs = []
        def w1(n):
            xs.append(n.x + n.w)
            for c in n.children:
                w1(c)
        w1(b)
        cur_x = max(xs) + 90
        max_h = max(max_h, max((n.y + n.h / 2 for n in _all(b)), default=0))

    W = int(cur_x + 40)
    H = int(max_h + 60)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif">',
           f'<rect width="{W}" height="{H}" fill="#14151C"/>']

    def rgb(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def mix(c1, c2, k):
        a, b2 = rgb(c1), rgb(c2)
        return "#%02X%02X%02X" % tuple(int(a[i] + (b2[i] - a[i]) * k) for i in range(3))

    def edges(n):
        col = PALETTE[n.color % len(PALETTE)]
        for c in n.children:
            x1, y1 = n.x + n.w, n.y
            x2, y2 = c.x, c.y
            cx = (x1 + x2) / 2
            wd = max(1.2, 3.0 - n.depth * 0.5)
            out.append(f'<path d="M{x1:.1f},{y1:.1f} C{cx:.1f},{y1:.1f} {cx:.1f},{y2:.1f} '
                       f'{x2:.1f},{y2:.1f}" fill="none" stroke="{col}" stroke-width="{wd:.1f}" '
                       f'opacity="{max(0.3, 0.9 - n.depth * 0.12):.2f}"/>')
            edges(c)

    for b in roots:
        edges(b)

    def nodes(n):
        col = PALETTE[n.color % len(PALETTE)]
        if n.kind == "book":
            fill, stroke, tcol, fs = col, col, "#0E1220", 18
        elif n.kind == "chap":
            fill, stroke, tcol, fs = "#1E2230", col, "#E6EAF5", 14
        elif n.kind == "sec":
            fill, stroke, tcol, fs = "#1A1E2B", mix(col, "#000000", 0.4), "#C7CEDE", 12.5
        else:
            fill, stroke, tcol, fs = "#20242F", mix(col, "#000000", 0.3), "#DDE2EE", 12
        r = 12 if n.kind == "book" else 7
        _h = n.nh or n.h
        out.append(f'<rect x="{n.x}" y="{n.y - _h / 2}" width="{n.w}" height="{_h}" rx="{r}" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>')
        out.append(f'<text x="{n.x + PAD_X}" y="{n.y + fs * 0.36}" fill="{tcol}" '
                   f'font-size="{fs}">{esc(n.title)}</text>')
        for c in n.children:
            nodes(c)

    for b in roots:
        nodes(b)

    out.append("</svg>")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    return W, H, sum(1 for b in roots for _ in _all(b))


def _all(n):
    yield n
    for c in n.children:
        yield from _all(c)
