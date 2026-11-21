# -*- coding: utf-8 -*-
"""修两件事：
1. 章末图并入时，若该章已有通用内容 → 清空后用它替换（避免重复）
2. 有机化学基础那一张图拆成五章
"""
import io

# ---------- 1) merge_book：替换而不是追加 ----------
P = r"C:\myapp\_chemmap\merge_book.py"
t = io.open(P, encoding="utf-8").read()
OLD = '''    # 同名节则替换，否则追加
    for s in c["sections"]:
        if s["section"] == sec_name:
            s["points"] = points
            break
    else:
        c["sections"].append({"section": sec_name, "points": points})'''
NEW = '''    # 章末图是更权威的版本：第一次遇到这一章时，清掉通用内容，只保留章末图
    key = (book, chap)
    if key not in _cleared:
        c["sections"] = []
        _cleared.add(key)
    c["sections"].append({"section": sec_name, "points": points})'''
assert OLD in t
t = t.replace(OLD, NEW, 1)
t = t.replace("for book, chap, sec_name, pts in (BOOK_MAPS + BOOK_MAPS_2 + BOOK_MAPS_3):",
              "_cleared = set()\nfor book, chap, sec_name, pts in (BOOK_MAPS + BOOK_MAPS_2 + BOOK_MAPS_3):", 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("merge_book 改为替换式合并")

# ---------- 2) 有机拆成五章 ----------
P2 = r"C:\myapp\_chemmap\book_maps3.py"
s = io.open(P2, encoding="utf-8").read()

OLD_HDR = '''    ("选择性必修3", "第一章 有机化合物的结构特点 / 第二章 烃 / 第三章 烃的衍生物 / 第四章 生物大分子 / 第五章 合成高分子", "10. 有机化学基础（章末知识体系）", ['''
assert OLD_HDR in s

i = s.index(OLD_HDR)
j = s.index("\n]\n", i) if "\n]\n" in s[i:] else len(s)
block = s[i:j]

def seg(start_kw, end_kw):
    a = block.index(start_kw)
    b = block.index(end_kw) if end_kw else len(block)
    return block[a:b]

p_struct = seg('("有机物的结构特点"', '("烃"')
p_naming = seg('("有机物的命名"', '("研究有机物的方法"')
p_research = seg('("研究有机物的方法"', '("烃"')
p_hydro = seg('("烃",', '("化石燃料的综合利用"')
p_fossil = seg('("化石燃料的综合利用"', '("烃的衍生物"')
p_deriv = seg('("烃的衍生物",', '("生物大分子"')
p_bio = seg('("生物大分子",', '("合成高分子"')
p_poly = seg('("合成高分子",', None)

new = ""
new += ('    ("选择性必修3", "第一章 有机化合物的结构特点与研究方法", "10.1 结构特点与研究方法（章末知识体系）", [\n'
        + p_struct + p_naming + p_research.rstrip().rstrip(',') + '\n    ]),\n')
new += ('    ("选择性必修3", "第二章 烃", "10.2 烃与化石燃料（章末知识体系）", [\n'
        + p_hydro + p_fossil.rstrip().rstrip(',') + '\n    ]),\n')
new += ('    ("选择性必修3", "第三章 烃的衍生物", "10.3 烃的衍生物（章末知识体系）", [\n'
        + p_deriv.rstrip().rstrip(',') + '\n    ]),\n')
new += ('    ("选择性必修3", "第四章 生物大分子", "10.4 生物大分子（章末知识体系）", [\n'
        + p_bio.rstrip().rstrip(',') + '\n    ]),\n')
new += ('    ("选择性必修3", "第五章 合成高分子", "10.5 合成高分子（章末知识体系）", [\n'
        + p_poly.rstrip().rstrip(',') + '\n    ]),\n')

s = s[:i] + new + s[j:]
io.open(P2, "w", encoding="utf-8", newline="\n").write(s)
print("有机已拆成五章")
