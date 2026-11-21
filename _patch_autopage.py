# -*- coding: utf-8 -*-
"""错题卡：按信息量自动决定卡片大小（1/3/6 题一页），并自动分页。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

OLD = '''    cards = []
    for e in errs:
        q = (e.get("original") or e.get("question") or "").strip()
        if not q:
            continue
        m = (e.get("mistake") or "").strip()
        a = (e.get("answer") or "").strip()
        tags = "、".join(str(x) for x in (e.get("tags") or [])[:4])
        subj = e.get("subject", "")
        _no = len(cards) + 1
        _blank = '<div class="work"></div>' if blank else ''
        cards.append(f"""
        <div class="card">
          <div class="head"><span class="no">#{_no:03d}</span><span class="subj">{esc(subj)}</span><span class="tags">{esc(tags)}</span></div>
          <div class="q">{esc(q[:420])}</div>
          {_blank}
          <div class="line"><b>错因</b>{esc(m[:160])}</div>
          <div class="line"><b>答案</b>{esc(a[:220])}</div>
          <div class="keyline">🔑 这题的钥匙：<span class="dots"></span></div>
          <div class="foot">□ 已会　□ 还需练</div>
        </div>""")

    pages = []
    for i in range(0, len(cards), per_page):
        pages.append("".join(cards[i:i + per_page]))

    body = "".join(f'<div class="page">{"".join(chunk)}</div>' for chunk in pages) if pages else \\
        '<div class="page"><div class="card"><div class="q">暂无错题</div></div></div>'
'''

NEW = '''    # 卡片尺寸按信息量自动决定：
    #   s  = 1 格（一页最多 6 道，选择题/小题）
    #   m  = 2 格（一页 3 道，中等题）
    #   l  = 6 格（半页，需推算的大题）
    #   xl = 12 格（整页，超长题/带图题）
    CELLS = {"s": 1, "m": 2, "l": 6, "xl": 12}
    PROFILE = {"s": 0, "m": 1, "l": 2, "xl": 3}
    BACK = {0: "s", 1: "m", 2: "l", 3: "xl"}

    def _size_of(q, has_img):
        n = len(q)
        if has_img:
            n += 260
        if n <= 110:
            lv = 0
        elif n <= 240:
            lv = 1
        elif n <= 520:
            lv = 2
        else:
            lv = 3
        if blank:            # 要留演算区时整体升一级
            lv = min(3, lv + 1)
        return BACK[lv]

    cards = []
    for e in errs:
        q = (e.get("original") or e.get("question") or "").strip()
        if not q:
            continue
        m = (e.get("mistake") or "").strip()
        a = (e.get("answer") or "").strip()
        tags = "、".join(str(x) for x in (e.get("tags") or [])[:4])
        subj = e.get("subject", "")
        media = e.get("media") or []
        has_img = bool(media)
        _no = len(cards) + 1
        _size = _size_of(q, has_img)
        _blank = '<div class="work"></div>' if blank else ''
        _img = '<div class="imgnote">［原题有图，见手机］</div>' if has_img else ''
        cards.append({
            "cells": CELLS[_size],
            "html": f"""
        <div class="card {_size}">
          <div class="head"><span class="no">#{_no:03d}</span><span class="subj">{esc(subj)}</span><span class="tags">{esc(tags)}</span></div>
          <div class="q">{esc(q[:900])}</div>
          {_img}
          {_blank}
          <div class="line"><b>错因</b>{esc(m[:200])}</div>
          <div class="line"><b>答案</b>{esc(a[:300])}</div>
          <div class="keyline">🔑 这题的钥匙：<span class="dots"></span></div>
          <div class="foot">□ 已会　□ 还需练</div>
        </div>""",
        })

    # 自动分页：每页 12 格，贪心装填，装不下就换页
    pages = []
    cur, used = [], 0
    for c in cards:
        if used + c["cells"] > 12 and cur:
            pages.append(cur)
            cur, used = [], 0
        cur.append(c["html"])
        used += c["cells"]
    if cur:
        pages.append(cur)

    body = "".join(f'<div class="page">{"".join(chunk)}</div>' for chunk in pages) if pages else \\
        '<div class="page"><div class="card"><div class="q">暂无错题</div></div></div>'
'''

assert OLD in t, "卡片生成段未匹配"
t = t.replace(OLD, NEW, 1)

# CSS：网格改为 6 行 x 2 列 + 卡片按尺寸跨格
OLD_CSS = '''  .page {{ width: 190mm; height: 277mm; display: grid; grid-template-columns: 1fr 1fr;
           grid-template-rows: repeat({_rows}, 1fr); gap: 4mm; page-break-after: always; }}'''
NEW_CSS = '''  .page {{ width: 190mm; height: 277mm; display: grid; grid-template-columns: 1fr 1fr;
           grid-template-rows: repeat(6, 1fr); grid-auto-flow: dense;
           gap: 3mm; page-break-after: always; }}
  .card.s {{ grid-column: span 1; grid-row: span 1; }}
  .card.m {{ grid-column: span 1; grid-row: span 2; }}
  .card.l {{ grid-column: span 2; grid-row: span 3; }}
  .card.xl {{ grid-column: span 2; grid-row: span 6; }}
  .card.l .q, .card.xl .q {{ font-size: 12pt; }}
  .imgnote {{ font-size: 7.5pt; color: #a60; margin-top: 1mm; }}'''
assert OLD_CSS in t, "页面 CSS 未匹配"
t = t.replace(OLD_CSS, NEW_CSS, 1)

# 移除不再使用的 _rows 变量
t = t.replace("    _rows = max(1, (int(per_page) + 1) // 2)\n", "", 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("自动分页已实现")
