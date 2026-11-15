# -*- coding: utf-8 -*-
"""思维导图渲染器（支持超采样：scale=2 时按 2 倍像素绘制，放大不糊）。

Flet 0.28 没有 canvas，所以图形在这里用 PIL 画好，App 里用 InteractiveViewer 显示。
"""
import io
import os

from PIL import Image, ImageDraw, ImageFont

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
                return ImageFont.truetype(p, int(size))
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_px):
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
    steps = 28
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = (mt ** 3) * p0[0] + 3 * (mt ** 2) * t * p1[0] + 3 * mt * (t ** 2) * p2[0] + (t ** 3) * p3[0]
        y = (mt ** 3) * p0[1] + 3 * (mt ** 2) * t * p1[1] + 3 * mt * (t ** 2) * p2[1] + (t ** 3) * p3[1]
        pts.append((x, y))
    draw.line(pts, fill=color, width=width, joint="curve")


def render_mindmap(subject, kps, width=1400, scale=2):
    """kps: [{"name","notes":[...],"errors":[...]}] → PNG bytes（按 scale 超采样）"""
    S = max(1, int(scale))
    f_root = _font(34 * S)
    f_kp = _font(28 * S)
    f_leaf = _font(22 * S)
    cnt_font = _font(17 * S)

    root_w, root_h = 240 * S, 84 * S
    kp_w = 300 * S
    leaf_w = 300 * S
    leaf_gap = 52 * S
    kp_gap = 34 * S
    m = 40 * S
    gap1, gap2 = 120 * S, 110 * S
    rad = 20 * S
    kp_h = 64 * S
    leaf_h = 44 * S

    blocks = []
    total_h = 0
    for kp in kps:
        leaves = []
        for t in (kp.get("notes") or [])[:6]:
            leaves.append(("笔记  " + str(t)[:24], LEAF_BG, (77, 182, 172)))
        for t in (kp.get("errors") or [])[:6]:
            leaves.append(("错题  " + str(t)[:24], LEAF_BG, (247, 118, 142)))
        h = max(70 * S, len(leaves) * leaf_gap + 20 * S)
        blocks.append((kp, leaves, h))
        total_h += h + kp_gap
    total_h = max(360 * S, total_h - kp_gap)

    H = total_h + m * 2
    W = m * 2 + root_w + gap1 + kp_w + gap2 + leaf_w + 20 * S

    img = Image.new("RGB", (int(W), int(H)), BG)
    d = ImageDraw.Draw(img)

    rx, ry = m, H / 2 - root_h / 2
    d.rounded_rectangle([rx, ry, rx + root_w, ry + root_h], radius=rad, fill=ROOT_BG,
                        outline=(120, 160, 235), width=2 * S)
    d.text((rx + root_w / 2, ry + root_h / 2), subject, font=f_root, fill=(255, 255, 255),
           anchor="mm")
    root_out = (rx + root_w, ry + root_h / 2)

    y = m
    for kp, leaves, bh in blocks:
        kx = m + root_w + gap1
        ky = y + bh / 2 - kp_h / 2
        has_err = bool(kp.get("errors"))
        bg = KP_BG_ERR if has_err else KP_BG

        _bezier(d, root_out,
                (root_out[0] + 60 * S, root_out[1]),
                (kx - 60 * S, ky + kp_h / 2),
                (kx, ky + kp_h / 2), LINE, 3 * S)

        d.rounded_rectangle([kx, ky, kx + kp_w, ky + kp_h], radius=16 * S, fill=bg,
                            outline=(90, 130, 160), width=2 * S)
        name_lines = _wrap(d, kp["name"], f_kp, kp_w - 34 * S)
        ny = ky + kp_h / 2 - (len(name_lines) - 1) * 15 * S
        for ln in name_lines:
            d.text((kx + 14 * S, ny), ln, font=f_kp, fill=TEXT, anchor="lm")
            ny += 30 * S

        cnt = f"记{len(kp.get('notes', []))} 错{len(kp.get('errors', []))}"
        d.text((kx + kp_w - 10 * S, ky + 10 * S), cnt, font=cnt_font, fill=TEXT_DIM, anchor="ra")

        kp_out = (kx + kp_w, ky + kp_h / 2)

        ly = y
        for text, lbg, dot in leaves:
            lx = kx + kp_w + gap2
            _bezier(d, kp_out,
                    (kp_out[0] + 50 * S, kp_out[1]),
                    (lx - 50 * S, ly + leaf_h / 2),
                    (lx, ly + leaf_h / 2), (70, 88, 130), 2 * S)
            d.rounded_rectangle([lx, ly, lx + leaf_w, ly + leaf_h], radius=12 * S, fill=lbg,
                                outline=(52, 56, 70), width=S)
            d.ellipse([lx + 12 * S, ly + leaf_h / 2 - 6 * S, lx + 24 * S, ly + leaf_h / 2 + 6 * S],
                      fill=dot)
            _t = text
            while _t and d.textlength(_t, font=f_leaf) > leaf_w - 46 * S:
                _t = _t[:-1]
            if _t != text:
                _t = _t[:-1] + "…"
            d.text((lx + 34 * S, ly + leaf_h / 2), _t, font=f_leaf, fill=(200, 205, 220), anchor="lm")
            ly += leaf_gap

        y += bh + kp_gap

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
