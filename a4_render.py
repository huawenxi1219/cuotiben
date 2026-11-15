# -*- coding: utf-8 -*-
"""A4 错题卡排版：在 App 里直接排好一整张 A4，导出 PNG / PDF 给打印机用。

- render_error_pages(): 把错题排成若干张 A4（300dpi = 2480×3508）
- pages_to_pdf(): 把排好的页面打包成 PDF（纯标准库，不依赖第三方 PDF 库）
"""
import io
import os

from PIL import Image, ImageDraw, ImageFont

A4_W, A4_H = 2480, 3508          # 300 dpi
MARGIN = 110

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    "/system/fonts/NotoSansCJK-Regular.ttc",
    "/system/fonts/NotoSansSC-Regular.otf",
    "/system/fonts/DroidSansFallbackFull.ttf",
    "/system/fonts/DroidSansFallback.ttf",
]

LAYOUT = {1: (1, 1), 2: (1, 2), 3: (1, 3), 4: (2, 2), 5: (2, 3), 6: (2, 3)}


def _font(size, bold=False):
    idx = 1 if bold else 0
    cands = FONT_CANDIDATES if not bold else [FONT_CANDIDATES[1], FONT_CANDIDATES[0]] + FONT_CANDIDATES[2:]
    for p in cands:
        try:
            if os.path.exists(p):
                return ImageFont.truetype(p, int(size))
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w, max_lines=None):
    lines, cur = [], ""
    for ch in str(text).replace("\r", ""):
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if draw.textlength(cur + ch, font=font) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = lines[-1][:-1] + "…"
    return lines


def _err_title(e):
    for k in ("original", "question", "title", "q", "content", "text", "stem"):
        v = e.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    tags = [str(x).strip() for x in (e.get("tags") or []) if str(x).strip()]
    return ("（%s）" % tags[0]) if tags else "（未填题干）"


def render_error_pages(errors, per_page=6, blank=False, title="池鱼错题卡"):
    """返回 [PIL.Image] 列表，每个元素是一张 A4。"""
    per_page = per_page if per_page in LAYOUT else 6
    cols, rows = LAYOUT[per_page]
    f_title = _font(58, True)
    f_meta = _font(34)
    f_no = _font(40, True)
    f_q = _font(46)
    f_small = _font(38)
    f_tiny = _font(32)

    pages = []
    items = list(errors)
    if not items:
        items = [{"original": "（还没有错题）", "subject": ""}]
    total_pages = (len(items) + per_page - 1) // per_page

    for pi in range(total_pages):
        chunk = items[pi * per_page:(pi + 1) * per_page]
        img = Image.new("RGB", (A4_W, A4_H), (255, 255, 255))
        d = ImageDraw.Draw(img)

        d.text((MARGIN, 70), title, font=f_title, fill=(20, 20, 20))
        d.text((A4_W - MARGIN, 88), f"第 {pi + 1} / {total_pages} 页", font=f_meta,
               fill=(120, 120, 120), anchor="ra")
        d.line([(MARGIN, 150), (A4_W - MARGIN, 150)], fill=(200, 200, 200), width=3)

        top = 190
        usable_h = A4_H - top - MARGIN
        gap = 34
        cw = (A4_W - 2 * MARGIN - (cols - 1) * gap) // cols
        chh = (usable_h - (rows - 1) * gap) // rows

        for i, e in enumerate(chunk):
            r, c = divmod(i, cols)
            x = MARGIN + c * (cw + gap)
            y = top + r * (chh + gap)
            # 卡片边框
            d.rounded_rectangle([x, y, x + cw, y + chh], radius=24, outline=(150, 150, 150), width=4)

            inner_x = x + 30
            inner_w = cw - 60
            cur_y = y + 26

            # 编号 + 科目
            no = e.get("_no") or (pi * per_page + i + 1)
            d.text((inner_x, cur_y), f"{no:03d}", font=f_no, fill=(180, 60, 60))
            meta = " ".join(x for x in [str(e.get("subject") or ""),
                                        str((e.get("tags") or [""])[0] if e.get("tags") else "")] if x)
            if meta:
                d.text((x + cw - 30, cur_y + 6), meta, font=f_tiny, fill=(120, 120, 120), anchor="ra")
            cur_y += 64

            # 题目
            for line in _wrap(d, _err_title(e), f_q, inner_w, max_lines=6):
                d.text((inner_x, cur_y), line, font=f_q, fill=(15, 15, 15))
                cur_y += 62
            cur_y += 10

            # 我的思路 / 错因 / 答案
            blocks = [
                ("我的思路", e.get("idea") or e.get("my_thought") or ""),
                ("错因", e.get("mistake") or e.get("reason") or ""),
                ("标准答案", e.get("answer") or ""),
            ]
            for label, val in blocks:
                if not str(val).strip():
                    continue
                d.text((inner_x, cur_y), f"【{label}】", font=f_tiny, fill=(90, 90, 90))
                cur_y += 44
                for line in _wrap(d, val, f_small, inner_w, max_lines=4):
                    if cur_y > y + chh - 120:
                        break
                    d.text((inner_x + 8, cur_y), line, font=f_small, fill=(40, 40, 40))
                    cur_y += 50
                cur_y += 6

            # 演算留白
            if blank and cur_y < y + chh - 140:
                d.rounded_rectangle([inner_x, cur_y, x + cw - 30, y + chh - 70],
                                    radius=10, outline=(210, 210, 210), width=2)
                d.text((inner_x + 10, cur_y + 8), "演算区", font=f_tiny, fill=(200, 200, 200))
                cur_y = y + chh - 70

            # 底部勾选
            d.text((inner_x, y + chh - 52), "□ 已会    □ 还需练", font=f_tiny, fill=(120, 120, 120))

        pages.append(img)
    return pages


def pages_to_pdf(images, quality=82):
    """把 PIL 图片打包成 PDF（JPEG 嵌入，纯标准库实现）。"""
    jpegs = []
    for im in images:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=quality)
        jpegs.append(buf.getvalue())

    n = len(jpegs)
    objs = {}

    def add(num, data):
        objs[num] = data

    obj_nums = []
    next_num = 3
    for _ in range(n):
        obj_nums.append((next_num, next_num + 1, next_num + 2))
        next_num += 3

    kids = " ".join(f"{p[0]} 0 R" for p in obj_nums)
    add(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    add(2, f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode())

    for idx, jpg in enumerate(jpegs):
        pnum, cnum, inum = obj_nums[idx]
        add(pnum, (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                   f"/Resources << /XObject << /Im{idx} {inum} 0 R >> >> "
                   f"/Contents {cnum} 0 R >>").encode())
        content = (f"q 595 0 0 842 0 0 cm /Im{idx} Do Q").encode()
        add(cnum, b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")
        add(inum, (f"<< /Type /XObject /Subtype /Image /Width {A4_W} /Height {A4_H} "
                   f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                   f"/Length {len(jpg)} >>\nstream\n").encode() + jpg + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + objs[num] + b"\nendobj\n"
    xref_pos = len(out)
    max_num = max(objs) + 1
    out += f"xref\n0 {max_num}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, max_num):
        if num in offsets:
            out += f"{offsets[num]:010d} 00000 n \n".encode()
        else:
            out += b"0000000000 65535 f \n"
    out += (f"trailer\n<< /Size {max_num} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n").encode()
    return bytes(out)
