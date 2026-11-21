# -*- coding: utf-8 -*-
"""两处改进：
1. 把「化学实验基础」「化学综合实验」从册里拿出来，单独成「专题」
2. 背诵版头部统计改成「顶级知识点 + 明细条数」，避免看着像只有 100 条
"""
import io
import json
import os

TREE = r"C:\myapp\assets\chem_tree.json"
tree = json.load(io.open(TREE, encoding="utf-8"))

SPECIAL = ("化学实验基础", "化学综合实验")

moved = []
for b in tree["books"]:
    keep = []
    for c in b["chapters"]:
        if c["name"] in SPECIAL:
            moved.append(c)
        else:
            keep.append(c)
    b["chapters"] = keep

tree["books"] = [b for b in tree["books"] if b["chapters"]]

if moved:
    tree["books"].append({"name": "专题（实验）", "chapters": moved})

s = json.dumps(tree, ensure_ascii=False, indent=1)
for p in (TREE, r"C:\myapp\data\chem_tree.json"):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("已移动专题章:", [c["name"] for c in moved])

# 改打印头部
P = r"C:\myapp\_chemmap\make_print.py"
t = io.open(P, encoding="utf-8").read()
OLD = '''tp = sum(len(s["points"]) for b in tree["books"] for c in b["chapters"] for s in c["sections"])
te = sum(len(s.get("equations", [])) for b in tree["books"] for c in b["chapters"] for s in c["sections"])
out.append(f"<div class='sub'>按教材顺序 · {tp} 个知识点 · {te} 个方程式 · 只含知识点，不含错题</div>")'''
NEW = '''def _cnt(items):
    n = 0
    for it in items:
        n += 1 + _cnt(it.get("sub") or [])
    return n


tp = sum(len(s["points"]) for b in tree["books"] for c in b["chapters"] for s in c["sections"])
ta = sum(_cnt(s["points"]) for b in tree["books"] for c in b["chapters"] for s in c["sections"])
out.append(f"<div class='sub'>按教材顺序 · {tp} 个知识点 / {ta} 条明细 · 只含知识点，不含错题</div>")'''
assert OLD in t
t = t.replace(OLD, NEW, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("头部统计已更新")
