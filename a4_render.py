# -*- coding: utf-8 -*-
"""A4 错题卡 2.0：为「纸上做题」设计的交互。

核心思路：
1. 一次导出两份——「题目版」（留白重做）+「答案版」（对答案），先做后对
2. 每张卡带编号 + 复习打勾格（D1/D3/D7/D15），纸面就是复习进度表
3. 页脚印「批次 · 编号范围」，配合 App 里的编号搜索，纸和软件能对上
4. 卡上留「改状态」提示：在 App 搜编号 → 改成已解决
"""
import io
import os

from PIL import Image, ImageDraw, ImageFont

A4_W, A4_H = 2480, 3508
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


def render_error_pages(errors, per_page=6, blank=False, mode="question",
                       title="池鱼错题卡", start_no=1):
    """mode: question=只给题+留白（重做用）；answer=题+答案+错因（对答案用）。

    返回 [PIL.Image]。
    """
    if mode == "remind":
        return _render_remind_pages(errors, title=title, start_no=start_no)
    per_page = per_page if per_page in LAYOUT else 6
    cols, rows = LAYOUT[per_page]
    f_title = _font(58, True)
    f_meta = _font(34)
    f_no = _font(40, True)
    f_q = _font(46)
    f_small = _font(38)
    f_tiny = _font(32)

    items = list(errors) or [{"original": "（还没有错题）"}]
    total_pages = (len(items) + per_page - 1) // per_page
    pages = []
    extra = {"answer": "答案版", "question": "题目版"}.get(mode, "")

    for pi in range(total_pages):
        chunk = items[pi * per_page:(pi + 1) * per_page]
        img = Image.new("RGB", (A4_W, A4_H), (255, 255, 255))
        d = ImageDraw.Draw(img)

        d.text((MARGIN, 70), f"{title} · {extra}" if extra else title, font=f_title, fill=(20, 20, 20))
        first_no = start_no + pi * per_page
        last_no = first_no + len(chunk) - 1
        d.text((A4_W - MARGIN, 88), f"第 {pi + 1}/{total_pages} 页 · 编号 {first_no:03d}–{last_no:03d}",
               font=f_meta, fill=(120, 120, 120), anchor="ra")
        d.line([(MARGIN, 150), (A4_W - MARGIN, 150)], fill=(200, 200, 200), width=3)

        top = 190
        usable_h = A4_H - top - MARGIN - 60
        gap = 34
        cw = (A4_W - 2 * MARGIN - (cols - 1) * gap) // cols
        chh = (usable_h - (rows - 1) * gap) // rows

        for i, e in enumerate(chunk):
            r, c = divmod(i, cols)
            x = MARGIN + c * (cw + gap)
            y = top + r * (chh + gap)
            d.rounded_rectangle([x, y, x + cw, y + chh], radius=24, outline=(150, 150, 150), width=4)
            inner_x, inner_w = x + 30, cw - 60
            cur_y = y + 24

            _no = e.get("no")
            no = int(_no) if str(_no or "").isdigit() else (first_no + i)
            d.text((inner_x, cur_y), f"{no:03d}", font=f_no, fill=(180, 60, 60))
            meta = " ".join(str(v) for v in [e.get("subject") or "",
                                             (e.get("tags") or [""])[0] if e.get("tags") else "",
                                             e.get("mastery") or ""] if v)
            if meta:
                d.text((x + cw - 30, cur_y + 6), meta, font=f_tiny, fill=(120, 120, 120), anchor="ra")
            cur_y += 60

            for line in _wrap(d, _err_title(e), f_q, inner_w, max_lines=5 if mode == "answer" else 8):
                d.text((inner_x, cur_y), line, font=f_q, fill=(15, 15, 15))
                cur_y += 60
            cur_y += 8

            if mode == "answer":
                for label, val in (("我的思路", e.get("idea") or ""),
                                   ("错因", e.get("mistake") or ""),
                                   ("标准答案", e.get("answer") or "")):
                    if not str(val).strip():
                        continue
                    d.text((inner_x, cur_y), f"【{label}】", font=f_tiny, fill=(90, 90, 90))
                    cur_y += 42
                    for line in _wrap(d, val, f_small, inner_w, max_lines=5):
                        if cur_y > y + chh - 150:
                            break
                        d.text((inner_x + 8, cur_y), line, font=f_small, fill=(40, 40, 40))
                        cur_y += 48
                    cur_y += 4
            # 题目版：整块留白给演算
            if mode == "question" or blank:
                box_top = cur_y
                box_bot = y + chh - 96
                if box_bot - box_top > 60:
                    d.rounded_rectangle([inner_x, box_top, x + cw - 30, box_bot],
                                        radius=10, outline=(215, 215, 215), width=2)

            # 复习打勾 + 状态
            fy = y + chh - 62
            d.text((inner_x, fy), "复习：□D1   □D3   □D7   □D15", font=f_tiny, fill=(110, 110, 110))
            d.text((x + cw - 30, fy), "○对  △半对  ✗错", font=f_tiny, fill=(160, 160, 160), anchor="ra")

        # 页脚
        d.text((MARGIN, A4_H - 78),
               "改状态：在 App 错题本里按编号搜索 → 改成「已解决」／「待查」",
               font=f_tiny, fill=(150, 150, 150))
        pages.append(img)
    return pages



def _render_remind_pages(errors, title="池鱼错题卡", start_no=1, per_page=8):
    """提醒卡：一行错因 + 关键一步，不重做，只提醒。"""
    f_title = _font(54, True)
    f_meta = _font(32)
    f_no = _font(36, True)
    f_q = _font(40)
    f_txt = _font(34)
    f_tiny = _font(28)

    items = list(errors) or [{"original": "（还没有错题）"}]
    cols, rows = 2, 4
    per_page = cols * rows
    total_pages = (len(items) + per_page - 1) // per_page
    pages = []

    for pi in range(total_pages):
        chunk = items[pi * per_page:(pi + 1) * per_page]
        img = Image.new("RGB", (A4_W, A4_H), (255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((MARGIN, 70), f"{title} · 提醒卡", font=f_title, fill=(20, 20, 20))
        first_no = start_no + pi * per_page
        last = first_no + len(chunk) - 1
        d.text((A4_W - MARGIN, 88), f"第 {pi + 1}/{total_pages} 页 · {first_no:03d}–{last:03d}",
               font=f_meta, fill=(120, 120, 120), anchor="ra")
        d.line([(MARGIN, 148), (A4_W - MARGIN, 148)], fill=(200, 200, 200), width=3)

        top = 180
        gap = 26
        cw = (A4_W - 2 * MARGIN - gap) // cols
        usable = A4_H - top - MARGIN - 40
        chh = (usable - (rows - 1) * gap) // rows

        for i, e in enumerate(chunk):
            r, c = divmod(i, cols)
            x = MARGIN + c * (cw + gap)
            y = top + r * (chh + gap)
            d.rounded_rectangle([x, y, x + cw, y + chh], radius=18,
                                outline=(170, 170, 170), width=3)
            ix, iw = x + 24, cw - 48
            cy = y + 18
            _no = e.get("no")
            no = int(_no) if str(_no or "").isdigit() else (first_no + i)
            d.text((ix, cy), f"{no:03d}", font=f_no, fill=(180, 60, 60))
            tag = " ".join(str(v) for v in [e.get("subject") or "",
                                            (e.get("tags") or [""])[0] if e.get("tags") else ""] if v)
            if tag:
                d.text((x + cw - 24, cy + 6), tag, font=f_tiny, fill=(130, 130, 130), anchor="ra")
            cy += 52

            for line in _wrap(d, _err_title(e), f_q, iw, max_lines=2):
                d.text((ix, cy), line, font=f_q, fill=(20, 20, 20))
                cy += 50
            cy += 6

            _mis = (e.get("mistake") or "").strip()
            _key = (e.get("answer") or "").strip()
            if _mis:
                d.text((ix, cy), "错在：", font=f_tiny, fill=(150, 60, 60))
                lines = _wrap(d, _mis, f_txt, iw - 90, max_lines=2)
                d.text((ix + 92, cy), lines[0] if lines else "", font=f_txt, fill=(60, 60, 60))
                cy += 46
                for ln in lines[1:]:
                    d.text((ix + 92, cy), ln, font=f_txt, fill=(60, 60, 60))
                    cy += 46
            if _key and cy < y + chh - 40:
                d.text((ix, cy), "关键：", font=f_tiny, fill=(60, 110, 60))
                lines = _wrap(d, _key, f_txt, iw - 90, max_lines=2)
                d.text((ix + 92, cy), lines[0] if lines else "", font=f_txt, fill=(60, 60, 60))
            d.text((x + cw - 24, y + chh - 34), "□ 再看一遍", font=f_tiny,
                   fill=(150, 150, 150), anchor="ra")
        d.text((MARGIN, A4_H - 70), "提醒卡：只提醒错因与关键一步，不重做；看完打勾即可",
               font=f_tiny, fill=(150, 150, 150))
        pages.append(img)
    return pages


def pages_to_pdf(images, quality=82):
    jpegs = []
    for im in images:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=quality)
        jpegs.append(buf.getvalue())

    n = len(jpegs)
    objs = {}
    obj_nums = []
    next_num = 3
    for _ in range(n):
        obj_nums.append((next_num, next_num + 1, next_num + 2))
        next_num += 3

    kids = " ".join(f"{p[0]} 0 R" for p in obj_nums)
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode()

    for idx, jpg in enumerate(jpegs):
        pnum, cnum, inum = obj_nums[idx]
        objs[pnum] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                      f"/Resources << /XObject << /Im{idx} {inum} 0 R >> >> "
                      f"/Contents {cnum} 0 R >>").encode()
        content = f"q 595 0 0 842 0 0 cm /Im{idx} Do Q".encode()
        objs[cnum] = b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream"
        objs[inum] = (f"<< /Type /XObject /Subtype /Image /Width {A4_W} /Height {A4_H} "
                      f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                      f"/Length {len(jpg)} >>\nstream\n").encode() + jpg + b"\nendstream"

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
