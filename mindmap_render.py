# -*- coding: utf-8 -*-
"""思维导图渲染器：把「科目 → 知识点 → 笔记/错题」画成一张带贝塞尔曲线的 PNG。

Flet 0.28 没有 canvas，所以图形在这里用 PIL 画好，App 里用 InteractiveViewer 显示。
"""
import io
import math
import os

from PIL import Image, ImageDraw, ImageFont

# ---------- 配色 ----------
BG = (22, 22, 30)
ROOT_BG = (58, 92, 160)
KP_BG = (32, 58, 58)
KP_BG_ERR = (74, 36, 44)
LEAF_BG = (30, 32, 42)
TEXT = (232, 235, 245)
TEXT_DIM = (150, 156, 175)
LINE = (96, 118, 178)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    "/system/fonts/NotoSansCJK-Regular.ttc",
    "/system/fonts/NotoSansSC-Regular.otf",
    "/system/fonts/DroidSansFallbackFull.ttf",
    "/system/fonts/DroidSansFallback.ttf",
]


def _font(size):
    for p in FONT_CANDIDATES:
        try:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_px):
    """按像素宽度折行（中文逐字）"""
    lines, cur = [], ""
    for ch in str(text):
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if draw.textlength(cur + ch, font=font) > max_px and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines[:2]


def _bezier(draw, p0, p1, p2, p3, color, width=3):
    """三次贝塞尔曲线，用多段直线逼近"""
    steps = 28
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = (mt ** 3) * p0[0] + 3 * (mt ** 2) * t * p1[0] + 3 * mt * (t ** 2) * p2[0] + (t ** 3) * p3[0]
        y = (mt ** 3) * p0[1] + 3 * (mt ** 2) * t * p1[1] + 3 * mt * (t ** 2) * p2[1] + (t ** 3) * p3[1]
        pts.append((x, y))
    draw.line(pts, fill=color, width=width, joint="curve")


def render_mindmap(subject, kps, width=1400):
    """kps: [{"name":..., "notes":[str], "errors":[str]}] → PNG bytes"""
    f_root = _font(34)
    f_kp = _font(28)
    f_leaf = _font(22)
    cnt_font = _font(17)

    root_w, root_h = 240, 84
    kp_w = 300
    leaf_w = 300
    leaf_gap = 52
    kp_gap = 34
    m = 40

    # 每个知识点的高度 = 叶子数×行距
    blocks = []
    total_h = 0
    for kp in kps:
        leaves = []
        for t in kp.get("notes", [])[:6]:
            leaves.append(("笔记  " + str(t)[:24], LEAF_BG, (77, 182, 172)))
        for t in kp.get("errors", [])[:6]:
            leaves.append(("错题  " + str(t)[:24], LEAF_BG, (247, 118, 142)))
        h = max(70, len(leaves) * leaf_gap + 20)
        blocks.append((kp, leaves, h))
        total_h += h + kp_gap
    total_h = max(360, total_h - kp_gap)

    H = total_h + m * 2
    W = m * 2 + root_w + 120 + kp_w + 110 + leaf_w + 20

    img = Image.new("RGB", (int(W), int(H)), BG)
    d = ImageDraw.Draw(img)

    # 根节点（左侧垂直居中）
    rx, ry = m, H / 2 - root_h / 2
    d.rounded_rectangle([rx, ry, rx + root_w, ry + root_h], radius=20, fill=ROOT_BG,
                        outline=(120, 160, 235), width=2)
    d.text((rx + root_w / 2, ry + root_h / 2), subject, font=f_root, fill=(255, 255, 255),
           anchor="mm")
    root_out = (rx + root_w, ry + root_h / 2)

    y = m
    for kp, leaves, bh in blocks:
        kx = m + root_w + 120
        ky = y + bh / 2 - 32
        has_err = bool(kp.get("errors"))
        bg = KP_BG_ERR if has_err else KP_BG

        # 连线：根 → 知识点（贝塞尔）
        _bezier(d, root_out,
                (root_out[0] + 60, root_out[1]),
                (kx - 60, ky + 32),
                (kx, ky + 32), LINE, 3)

        d.rounded_rectangle([kx, ky, kx + kp_w, ky + 64], radius=16, fill=bg,
                            outline=(90, 130, 160), width=2)
        name_lines = _wrap(d, kp["name"], f_kp, kp_w - 34)
        ny = ky + 32 - (len(name_lines) - 1) * 15
        for ln in name_lines:
            d.text((kx + 14, ny), ln, font=f_kp, fill=TEXT, anchor="lm")
            ny += 30

        cnt = f"记{len(kp.get('notes', []))} 错{len(kp.get('errors', []))}"
        d.text((kx + kp_w - 10, ky + 10), cnt, font=cnt_font, fill=TEXT_DIM, anchor="ra")

        kp_out = (kx + kp_w, ky + 32)

        # 叶子
        ly = y
        for text, lbg, dot in leaves:
            lx = kx + kp_w + 110
            _bezier(d, kp_out,
                    (kp_out[0] + 50, kp_out[1]),
                    (lx - 50, ly + 22),
                    (lx, ly + 22), (70, 88, 130), 2)
            d.rounded_rectangle([lx, ly, lx + leaf_w, ly + 44], radius=12, fill=lbg,
                                outline=(52, 56, 70), width=1)
            d.ellipse([lx + 12, ly + 22 - 6, lx + 24, ly + 22 + 6], fill=dot)
            _t = text
            while _t and d.textlength(_t, font=f_leaf) > leaf_w - 46:
                _t = _t[:-1]
            if _t != text:
                _t = _t[:-1] + "…"
            d.text((lx + 34, ly + 22), _t, font=f_leaf, fill=(200, 205, 220), anchor="lm")
            ly += leaf_gap

        y += bh + kp_gap

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
