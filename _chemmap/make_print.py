# -*- coding: utf-8 -*-
"""给背诵版加「紧凑版」：字号小一点、边距窄一点，页数更少。

用法：
  python make_print.py          → 标准版（11.5pt）
  python make_print.py compact  → 紧凑版（9.5pt）
"""
import html
import io
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from structures import STRUCTS as _STRUCTS
except BaseException:
    _STRUCTS = {}

TREE = r"C:\myapp\assets\chem_tree.json"
COMPACT = "compact" in sys.argv
HTML = (r"C:\myapp\化学背诵版-紧凑.html" if COMPACT else r"C:\myapp\化学背诵版.html")

tree = json.load(io.open(TREE, encoding="utf-8"))


def _render_sub(items, out, depth=1):
    if not items:
        return
    out.append(f"<ul class='sub d{depth}'>")
    for it in items:
        ttl = html.escape(it.get("title", ""))
        out.append(f"<li><b>{ttl}</b>")
        for f in (it.get("facts") or []):
            out.append(f"　{html.escape(str(f))}")
        out.append("</li>")
        _render_sub(it.get("sub") or [], out, depth + 1)
    out.append("</ul>")


if COMPACT:
    BASE, H1, SUB = "9.5pt", "16pt", "8pt"
    BOOK, CHAP, SEC = "12pt", "10.5pt", "9.2pt"
    PT, FACT, EQ = "9.5pt", "9.2pt", "8.8pt"
    MARGIN = "10mm 9mm"
    LEAD = "1.32"
else:
    BASE, H1, SUB = "11.5pt", "20pt", "9.5pt"
    BOOK, CHAP, SEC = "15pt", "12.5pt", "11pt"
    PT, FACT, EQ = "11.5pt", "10.5pt", "10.5pt"
    MARGIN = "14mm 12mm"
    LEAD = "1.5"

CSS = f"""
@page {{ size: A4; margin: {MARGIN}; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
       color: #1a1a1a; font-size: {BASE}; line-height: {LEAD}; margin: 0; }}
h1 {{ font-size: {H1}; margin: 0 0 3pt; }}
.sub {{ color: #666; font-size: {SUB}; margin-bottom: 10pt; }}
.book {{ font-size: {BOOK}; font-weight: 700; margin: 12pt 0 5pt;
        border-left: 5px solid #2b6cb0; padding-left: 8pt; page-break-after: avoid; }}
.chap {{ font-size: {CHAP}; font-weight: 700; margin: 9pt 0 4pt; color: #2b6cb0;
        page-break-after: avoid; }}
.sec  {{ font-size: {SEC}; font-weight: 600; margin: 7pt 0 3pt; color: #333;
        background: #eef2f7; padding: 2pt 5pt; page-break-after: avoid; }}
.pt   {{ margin: 0 0 5pt; page-break-inside: avoid; }}
.pt .t {{ font-weight: 700; }}
.pt .d {{ text-align: justify; }}
.facts {{ margin: 1pt 0 0 12pt; padding: 0; font-size: {FACT}; }}
.facts li {{ margin: 0; }}
.note {{ background: #eef7ff; border-left: 3px solid #3b82f6; padding: 2pt 6pt;
        margin: 2pt 0 0; font-size: {FACT}; color: #1e3a5f; }}
.sub {{ margin: 1pt 0 2pt 14pt; padding: 0; list-style: none; }}
.sub li {{ margin: 1pt 0; }}
.sub .d2 {{ margin-left: 14pt; }}
.sub .d3 {{ margin-left: 28pt; }}
.pit {{ color: #b03030; margin: 1pt 0 0 12pt; font-size: {FACT}; }}
.pit li {{ margin: 0; }}
.how {{ background: #fffbe6; border-left: 3px solid #d4a017; padding: 2pt 5pt;
       margin: 2pt 0 0; font-size: {FACT}; page-break-inside: avoid; }}
.mol {{ display: inline-block; margin: 2pt 6pt 2pt 0; border: 1px solid #e5e7eb;
       border-radius: 4pt; vertical-align: middle; }}
.eq {{ font-family: Consolas, "Courier New", monospace; font-size: {EQ};
      background: #f5f7fa; padding: 1pt 5pt; margin: 2pt 0 0; border-left: 3px solid #9ab;
      page-break-inside: avoid; }}
"""

out = [f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"]
out.append("<h1>人教A版高中化学 · 重点背诵版" + ("（紧凑版）" if COMPACT else "") + "</h1>")
tp = sum(len(s["points"]) for b in tree["books"] for c in b["chapters"] for s in c["sections"])
te = sum(len(s.get("equations", [])) for b in tree["books"] for c in b["chapters"] for s in c["sections"])
out.append(f"<div class='sub'>按教材顺序 · {tp} 个知识点 · {te} 个方程式 · 只含知识点，不含错题</div>")

for b in tree["books"]:
    out.append(f"<div class='book'>{html.escape(b['name'])}</div>")
    for c in b["chapters"]:
        out.append(f"<div class='chap'>{html.escape(c['name'])}</div>")
        for s in c["sections"]:
            out.append(f"<div class='sec'>{html.escape(s['section'])}</div>")
            if s.get("how"):
                out.append(f"<div class='how'><b>理解：</b>{html.escape(s['how'])}</div>")
            for p in s["points"]:
                out.append("<div class='pt'>")
                out.append(f"<div class='t'>{html.escape(p.get('id',''))}　{html.escape(p.get('title',''))}</div>")
                if p.get("detail"):
                    out.append(f"<div class='d'>{html.escape(p['detail'])}</div>")
                _ttl = p.get("title", "")
                _best = None
                for _k in _STRUCTS:
                    if _k in _ttl and (_best is None or len(_k) > len(_best)):
                        _best = _k
                if _best:
                    out.append("<div>" + _STRUCTS[_best] + "</div>")
                facts = p.get("facts") or []
                if facts:
                    out.append("<ul class='facts'>")
                    for f in facts:
                        out.append(f"<li>{html.escape(str(f))}</li>")
                    out.append("</ul>")
                pits = p.get("pitfalls") or []
                if pits:
                    out.append("<ul class='pit'>")
                    for f in pits:
                        out.append(f"<li>⚠ {html.escape(str(f))}</li>")
                    out.append("</ul>")
                if p.get("note"):
                    out.append(f"<div class='note'>💡 {html.escape(p['note'])}</div>")
                _render_sub(p.get("sub") or [], out)
                out.append("</div>")
            if s.get("equations"):
                for e in s["equations"]:
                    note = e.get("note", "")
                    out.append(f"<div class='eq'>{html.escape(e.get('eq',''))}"
                               + (f"　　// {html.escape(note)}" if note else "") + "</div>")
            if s.get("pitfalls"):
                out.append("<ul class='pit'>")
                for f in s["pitfalls"]:
                    out.append(f"<li>本节易错：{html.escape(str(f))}</li>")
                out.append("</ul>")

out.append("</body></html>")
io.open(HTML, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print(("紧凑版" if COMPACT else "标准版") + " HTML 生成:", HTML)
