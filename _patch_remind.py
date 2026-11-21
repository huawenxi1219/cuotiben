# -*- coding: utf-8 -*-
"""加入「提醒卡」模式：不重做，只印一行错因 + 关键一步，30 秒看完。

适用：物理（基本都会，只有粗心/难题）、数学里考场没写出来的题。
"""
import io
import os

# ---------- 在 a4_render 里加 remind 模式 ----------
A4 = r"C:\myapp\a4_render.py"
t = io.open(A4, encoding="utf-8").read()

OLD = '''    per_page = per_page if per_page in LAYOUT else 6
    cols, rows = LAYOUT[per_page]'''
NEW = '''    if mode == "remind":
        return _render_remind_pages(errors, title=title, start_no=start_no)
    per_page = per_page if per_page in LAYOUT else 6
    cols, rows = LAYOUT[per_page]'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

REMIND = '''

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
            d.text((ix, cy), f"{first_no + i:03d}", font=f_no, fill=(180, 60, 60))
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

'''
idx = t.index("\ndef pages_to_pdf(")
t = t[:idx] + REMIND + t[idx:]
io.open(A4, "w", encoding="utf-8", newline="\n").write(t)
print("提醒卡模式已加入 a4_render")
