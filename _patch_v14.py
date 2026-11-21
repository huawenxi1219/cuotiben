# -*- coding: utf-8 -*-
"""v1.4：修复「点了认识但不算掌握」；首页整体缩到 70%；背词字号缩到 50%。"""
import io, os, re

ROOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app"
SRC = os.path.join(ROOT, "src")
UX = os.path.join(SRC, "pages", "index", "index.ux")

t = io.open(UX, encoding="utf-8").read()

# ---------- 1) 判定：只要最近一次点了「认识」就算掌握 ----------
OLD = "				var ok = (e.a === 'know' && e.p >= 15) || e.p >= KNOWN_P"
NEW = "				// 只要最近一次点的是「认识」就算掌握（读得慢的人熟练度涨得少，不能因此判成没背会）\n				var ok = (e.a === 'know') || e.p >= KNOWN_P"
if OLD not in t:
    raise SystemExit("!! 判定语句未匹配")
t = t.replace(OLD, NEW)

# ---------- 2) 首页排版：整体缩到约 70% ----------
css = {
    ".appName": [("font-size: 40px", "font-size: 28px"), ("margin-top: 60px", "margin-top: 20px")],
    ".ver": [("font-size: 18px", "font-size: 13px")],
    ".pct": [("font-size: 64px", "font-size: 40px"), ("margin-top: 22px", "margin-top: 8px")],
    ".stat": [("font-size: 26px", "font-size: 19px"), ("margin-top: 18px", "margin-top: 8px")],
    ".stat2": [("font-size: 24px", "font-size: 16px"), ("margin-top: 6px", "margin-top: 3px")],
    ".btn": [("height: 56px", "height: 44px"), ("margin-top: 34px", "margin-top: 14px")],
    ".btnText": [("font-size: 26px", "font-size: 21px")],
    ".btnExit": [("height: 44px", "height: 36px"), ("margin-top: 16px", "margin-top: 8px")],
    ".btnExitText": [("font-size: 22px", "font-size: 18px")],
    ".home": [("height: 440px", "height: 470px"), ("margin-top: 60px", "margin-top: 26px")],
    ".homeCard": [("height: 440px", "height: 470px")],
    ".scope": [("height: 44px", "height: 36px"), ("margin-top: 14px", "margin-top: 8px"), ("width: 168px", "width: 150px")],
    ".scopeText": [("font-size: 20px", "font-size: 16px")],
    # ---------- 3) 背词字号缩到约 50% ----------
    ".word": [("font-size: 58px", "font-size: 28px")],
    ".mean": [("font-size: 26px", "font-size: 19px"), ("margin-top: 24px", "margin-top: 14px")],
    ".pos": [("font-size: 22px", "font-size: 16px"), ("margin-top: 14px", "margin-top: 8px")],
    ".hint": [("font-size: 20px", "font-size: 15px")],
    ".hint2": [("font-size: 20px", "font-size: 15px"), ("margin-top: 30px", "margin-top: 16px")],
    ".actText": [("font-size: 24px", "font-size: 18px"), ("margin-top: 18px", "margin-top: 8px")],
    ".tag": [("font-size: 20px", "font-size: 14px"), ("margin-top: 8px", "margin-top: 4px")],
    ".title2": [("font-size: 38px", "font-size: 26px"), ("margin-top: 40px", "margin-top: 20px")],
}

for sel, pairs in css.items():
    # 取出该选择器的规则块
    m = re.search(re.escape(sel) + r"\s*\{[^}]*\}", t)
    if not m:
        print("!! 未找到样式", sel)
        continue
    block = m.group(0)
    nb = block
    for a, b in pairs:
        nb = nb.replace(a, b)
    t = t[:m.start()] + nb + t[m.end():]

t = t.replace('<text class="ver">v1.1</text>', '<text class="ver">v1.4</text>')

io.open(UX, "w", encoding="utf-8", newline="\n").write(t)
print("index.ux -> v1.4", len(t))

mf = os.path.join(SRC, "manifest.json")
m = io.open(mf, encoding="utf-8").read()
m = m.replace('"versionName": "1.3.0"', '"versionName": "1.4.0"').replace('"versionCode": 130', '"versionCode": 140')
io.open(mf, "w", encoding="utf-8", newline="\n").write(m)
print("manifest -> 1.4.0")
