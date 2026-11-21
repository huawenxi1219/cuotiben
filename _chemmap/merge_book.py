# -*- coding: utf-8 -*-
"""把《红对勾》章末图并入主知识树，并生成背诵版。"""
import io
import json
import os
import sys

sys.path.insert(0, r"C:\myapp\_chemmap")
from book_maps import BOOK_MAPS
from book_maps2 import BOOK_MAPS_2

TREE = r"C:\myapp\assets\chem_tree.json"
tree = json.load(io.open(TREE, encoding="utf-8"))

# 建索引：册 → 章 → {"name","sections"}
index = {}
for b in tree["books"]:
    for c in b["chapters"]:
        index[(b["name"], c["name"])] = c

for book, chap, sec_name, pts in (BOOK_MAPS + BOOK_MAPS_2):
    c = index.get((book, chap))
    if c is None:
        # 新建
        new_book = None
        for b in tree["books"]:
            if b["name"] == book:
                new_book = b
                break
        if new_book is None:
            new_book = {"name": book, "chapters": []}
            tree["books"].append(new_book)
        c = {"name": chap, "sections": []}
        new_book["chapters"].append(c)
        index[(book, chap)] = c

    points = []
    for i, (title, detail, facts, pitfalls) in enumerate(pts, 1):
        points.append({
            "id": f"{i}",
            "title": title,
            "detail": detail,
            "facts": facts,
            "pitfalls": pitfalls,
        })
    # 同名节则替换，否则追加
    for s in c["sections"]:
        if s["section"] == sec_name:
            s["points"] = points
            break
    else:
        c["sections"].append({"section": sec_name, "points": points})

io.open(TREE, "w", encoding="utf-8", newline="\n").write(json.dumps(tree, ensure_ascii=False, indent=1))
io.open(r"C:\myapp\data\chem_tree.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps(tree, ensure_ascii=False, indent=1))

np = sum(len(s["points"]) for b in tree["books"] for c in b["chapters"] for s in c["sections"])
print("知识点总数:", np, "| 册", len(tree["books"]))
