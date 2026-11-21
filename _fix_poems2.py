# -*- coding: utf-8 -*-
"""按统编版教材订正：逐处替换 poem.ux 里的字词。"""
import io

SRC = r"C:\myapp\_poem\src\pages\poem\poem.ux"
t = io.open(SRC, encoding="utf-8").read()

FIXES = [
    # 谏太宗十思疏
    ("虽董之以严刑，震之以威怒", "虽董之以严刑，振之以威怒"),
    ("罚所及则思无以怒而滥刑", "罚所及则思无因怒而滥刑"),
    # 答司马谏议书
    ("于反复不宜卤莽", "于反覆不宜卤莽"),
    ("尤在名实", "尤在于名实"),
    ("某则以为受命于人主", "某则以谓受命于人主"),
    # 阿房宫赋
    ("嗟夫！使六国各爱其人", "嗟乎！使六国各爱其人"),
    # 登泰山记
    ("须臾成五彩", "须臾成五采"),
    # 离骚
    ("唯草木之零落兮", "惟草木之零落兮"),
    # 春江花月夜
    ("江月年年只相似", "江月年年望相似"),
    # 将进酒
    ("但愿长醉不复醒", "但愿长醉不愿醒"),
    # 燕歌行
    ("边庭飘摇那可度", "边庭飘飖那可度"),
    ("绝域苍茫无何有", "绝域苍茫无所有"),
    # 菩萨蛮
    ("新帖绣罗襦", "新贴绣罗襦"),
    # 陈情表
    ("既无叔伯", "既无伯叔"),
]

done, miss = [], []
for old, new in FIXES:
    if old in t:
        t = t.replace(old, new)
        done.append(new[:12])
    else:
        miss.append(old[:12])

io.open(SRC, "w", encoding="utf-8", newline="\n").write(t)
print("成功", len(done), "处")
for d in done:
    print("  ✓", d)
print("未命中", len(miss), miss)
