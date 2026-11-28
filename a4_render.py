# -*- coding: utf-8 -*-
"""错题卡：装订边 + 省墨模式。

- bind_left_mm：左侧留出打孔/装订的空白（默认 0）
- ink_saver：纯黑字 + 细灰线，不要底色块（省墨、也更清楚）
"""
import io
import os

from PIL import Image, ImageDraw, ImageFont

A4_W, A4_H = 2480, 3508
MARGIN = 110
MM = 300 / 25.4  # 1mm ≈ 11.8px

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
                       title="池鱼错题卡", start_no=1, bind_left_mm=0, ink_saver=True):
    if mode == "remind":
        return _render_remind_pages(errors, title=title, start_no=start_no,
                                    bind_left_mm=bind_left_mm, ink_saver=ink_saver)

    per_page = per_page if per_page in LAYOUT else 6
    cols, rows = LAYOUT[per_page]
    f_title = _font(52, True)
    f_meta = _font(30)
    f_no = _font(38, True)
    f_q = _font(42)
    f_small = _font(34)
    f_tiny = _font(28)

    left = MARGIN + int(bind_left_mm * MM)
    ink_line = (170, 170, 170) if ink_saver else (150, 150, 150)
    ink_text = (0, 0, 0) if ink_saver else (20, 20, 20)

    items = list(errors) or [{"original": "（还没有错题）"}]
    total_pages = (len(items) + per_page - 1) // per_page
    pages = []
    extra = {"answer": "答案版", "question": "题目版"}.get(mode, "")

    for pi in range(total_pages):
        chunk = items[pi * per_page:(pi + 1) * per_page]
        img = Image.new("RGB", (A4_W, A4_H), (255, 255, 255))
        d = ImageDraw.Draw(img)

        d.text((left, 66), f"{title} · {extra}" if extra else title, font=f_title, fill=ink_text)
        first_no = start_no + pi * per_page
        last_no = first_no + len(chunk) - 1
        d.text((A4_W - MARGIN, 84), f"第 {pi + 1}/{total_pages} 页 · 编号 {first_no:03d}–{last_no:03d}",
               font=f_meta, fill=(110, 110, 110), anchor="ra")
        d.line([(left, 146), (A4_W - MARGIN, 146)], fill=ink_line, width=2)

        # 装订线提示（很淡的虚线）
        if bind_left_mm > 0:
            bx = left - int(6 * MM)
            for yy in range(160, A4_H - 60, 46):
                d.line([(bx, yy), (bx, yy + 18)], fill=(215, 215, 215), width=1)

        top = 180
        usable_h = A4_H - top - MARGIN - 50
        gap = 30
        cw = (A4_W - left - MARGIN - (cols - 1) * gap) // cols
        chh = (usable_h - (rows - 1) * gap) // rows

        for i, e in enumerate(chunk):
            r, c = divmod(i, cols)
            x = left + c * (cw + gap)
            y = top + r * (chh + gap)
            d.rounded_rectangle([x, y, x + cw, y + chh], radius=18,
                                outline=ink_line, width=3)
            inner_x, inner_w = x + 24, cw - 48
            cur_y = y + 22

            _no = e.get("no")
            no = int(_no) if str(_no or "").isdigit() else (first_no + i)
            d.text((inner_x, cur_y), f"{no:03d}", font=f_no, fill=(150, 40, 40))
            meta = " ".join(str(v) for v in [e.get("subject") or "",
                                             (e.get("tags") or [""])[0] if e.get("tags") else "",
                                             e.get("mastery") or ""] if v)
            if meta:
                d.text((x + cw - 24, cur_y + 6), meta, font=f_tiny, fill=(120, 120, 120), anchor="ra")
            cur_y += 56

            for line in _wrap(d, _err_title(e), f_q, inner_w, max_lines=5 if mode == "answer" else 8):
                d.text((inner_x, cur_y), line, font=f_q, fill=ink_text)
                cur_y += 56
            cur_y += 6

            if mode == "answer":
                for label, val in (("我的思路", e.get("idea") or ""),
                                   ("错因", e.get("mistake") or ""),
                                   ("标准答案", e.get("answer") or "")):
                    if not str(val).strip():
                        continue
                    d.text((inner_x, cur_y), f"【{label}】", font=f_tiny, fill=(80, 80, 80))
                    cur_y += 38
                    for line in _wrap(d, val, f_small, inner_w, max_lines=5):
                        if cur_y > y + chh - 130:
                            break
                        d.text((inner_x + 6, cur_y), line, font=f_small, fill=ink_text)
                        cur_y += 44
                    cur_y += 4
            else:
                box_top = cur_y
                box_bot = y + chh - 86
                if box_bot - box_top > 50:
                    d.rounded_rectangle([inner_x, box_top, x + cw - 24, box_bot],
                                        radius=8, outline=(210, 210, 210), width=2)

            fy = y + chh - 56
            d.text((inner_x, fy), "复习：□D1   □D3   □D7   □D15", font=f_tiny, fill=(110, 110, 110))
            d.text((x + cw - 24, fy), "○对  △半对  ✗错", font=f_tiny, fill=(150, 150, 150),
                   anchor="ra")

        d.text((left, A4_H - 70),
               "改状态：在 App 错题本里按编号搜索 → 改成「已解决」／「待查」",
               font=f_tiny, fill=(150, 150, 150))
        pages.append(img)
    return pages


def _render_remind_pages(errors, title="池鱼错题卡", start_no=1, per_page=8,
                         bind_left_mm=0, ink_saver=True):
    f_title = _font(50, True)
    f_meta = _font(30)
    f_no = _font(34, True)
    f_q = _font(38)
    f_txt = _font(32)
    f_tiny = _font(26)

    left = MARGIN + int(bind_left_mm * MM)
    ink_line = (170, 170, 170)
    ink_text = (0, 0, 0) if ink_saver else (20, 20, 20)

    items = list(errors) or [{"original": "（还没有错题）"}]
    cols, rows = 2, 4
    per_page = cols * rows
    total_pages = (len(items) + per_page - 1) // per_page
    pages = []

    for pi in range(total_pages):
        chunk = items[pi * per_page:(pi + 1) * per_page]
        img = Image.new("RGB", (A4_W, A4_H), (255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((left, 66), f"{title} · 提醒卡", font=f_title, fill=ink_text)
        first_no = start_no + pi * per_page
        last = first_no + len(chunk) - 1
        d.text((A4_W - MARGIN, 84), f"第 {pi + 1}/{total_pages} 页 · {first_no:03d}–{last:03d}",
               font=f_meta, fill=(110, 110, 110), anchor="ra")
        d.line([(left, 144), (A4_W - MARGIN, 144)], fill=ink_line, width=2)

        if bind_left_mm > 0:
            bx = left - int(6 * MM)
            for yy in range(160, A4_H - 60, 46):
                d.line([(bx, yy), (bx, yy + 18)], fill=(215, 215, 215), width=1)

        top = 176
        gap = 24
        cw = (A4_W - left - MARGIN - gap) // cols
        usable = A4_H - top - MARGIN - 30
        chh = (usable - (rows - 1) * gap) // rows

        for i, e in enumerate(chunk):
            r, c = divmod(i, cols)
            x = left + c * (cw + gap)
            y = top + r * (chh + gap)
            d.rounded_rectangle([x, y, x + cw, y + chh], radius=14, outline=ink_line, width=2)
            ix, iw = x + 20, cw - 40
            cy = y + 16
            _no = e.get("no")
            no = int(_no) if str(_no or "").isdigit() else (first_no + i)
            d.text((ix, cy), f"{no:03d}", font=f_no, fill=(150, 40, 40))
            tag = " ".join(str(v) for v in [e.get("subject") or "",
                                            (e.get("tags") or [""])[0] if e.get("tags") else ""] if v)
            if tag:
                d.text((x + cw - 20, cy + 4), tag, font=f_tiny, fill=(120, 120, 120), anchor="ra")
            cy += 46
            for line in _wrap(d, _err_title(e), f_q, iw, max_lines=2):
                d.text((ix, cy), line, font=f_q, fill=ink_text)
                cy += 44
            cy += 4
            _mis = (e.get("mistake") or "").strip()
            if _mis:
                d.text((ix, cy), "错在：", font=f_tiny, fill=(140, 60, 60))
                lines = _wrap(d, _mis, f_txt, iw - 84, max_lines=2)
                if lines:
                    d.text((ix + 84, cy), lines[0], font=f_txt, fill=(40, 40, 40))
                    cy += 42
                    for ln in lines[1:]:
                        d.text((ix + 84, cy), ln, font=f_txt, fill=(40, 40, 40))
                        cy += 42
            _key = (e.get("answer") or "").strip()
            if _key and cy < y + chh - 34:
                d.text((ix, cy), "关键：", font=f_tiny, fill=(50, 100, 50))
                lines = _wrap(d, _key, f_txt, iw - 84, max_lines=1)
                if lines:
                    d.text((ix + 84, cy), lines[0], font=f_txt, fill=(40, 40, 40))
            d.text((x + cw - 20, y + chh - 28), "□ 再看一遍", font=f_tiny,
                   fill=(150, 150, 150), anchor="ra")
        d.text((left, A4_H - 62), "提醒卡：只提醒错因与关键一步，不重做；看完打勾即可",
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
