# -*- coding: utf-8 -*-
"""把 std_content.STD 转成 chem_tree_std.json（完整人教 A 版，按教材顺序）。"""
import io
import json
import os
import sys

sys.path.insert(0, r"C:\myapp\_chemmap")
from std_content import STD

books = {}
order = []
for book, chap, sec, pts in STD:
    if book not in books:
        books[book] = {}
        order.append(book)
    books[book].setdefault(chap, [])
    points = []
    for i, item in enumerate(pts, 1):
        title, detail, facts, pitfalls = item
        points.append({
            "id": f"{len(points) + 1}",
            "title": title,
            "detail": detail,
            "facts": facts,
            "pitfalls": pitfalls,
        })
    books[book][chap].append({"section": sec, "points": points})

tree = {"version": 3, "subject": "化学", "source": "人教版（2019）A版 教材目录",
        "note": "按教材顺序整理的重点知识，非某个学生的笔记",
        "books": [
            {"name": b, "chapters": [{"name": c, "sections": s} for c, s in chaps.items()]}
            for b, chaps in books.items()
        ]}

s = json.dumps(tree, ensure_ascii=False, indent=1)
os.makedirs(r"C:\myapp\_chemmap", exist_ok=True)
io.open(r"C:\myapp\_chemmap\chem_tree_std.json", "w", encoding="utf-8", newline="\n").write(s)

np = sum(len(sec["points"]) for b in tree["books"] for c in b["chapters"] for sec in c["sections"])
print(f"册 {len(tree['books'])} | 章 {sum(len(b['chapters']) for b in tree['books'])} | "
      f"节 {sum(len(c['sections']) for b in tree['books'] for c in b['chapters'])} | 知识点 {np}")
