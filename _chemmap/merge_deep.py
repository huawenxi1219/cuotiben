# -*- coding: utf-8 -*-
"""把深度版章末图并入主知识树（替换同名章节）。"""
import io
import json
import os
import sys

sys.path.insert(0, r"C:\myapp\_chemmap")
from deep_maps import DEEP
from deep_maps2 import DEEP2
from deep_maps3 import DEEP3

TREE = r"C:\myapp\assets\chem_tree.json"
tree = json.load(io.open(TREE, encoding="utf-8"))


def count_nodes(items):
    n = 0
    for it in items:
        n += 1 + count_nodes(it.get("sub") or [])
    return n


index = {(b["name"], c["name"]): c for b in tree["books"] for c in b["chapters"]}
books = {b["name"]: b for b in tree["books"]}

total = 0
for book, chap, sec_name, items in (DEEP + DEEP2 + DEEP3):
    c = index.get((book, chap))
    if c is None:
        b = books.get(book)
        if b is None:
            b = {"name": book, "chapters": []}
            tree["books"].append(b)
            books[book] = b
        c = {"name": chap, "sections": []}
        b["chapters"].append(c)
        index[(book, chap)] = c
    c["sections"] = [{"section": sec_name, "points": items}]
    total += count_nodes(items)

s = json.dumps(tree, ensure_ascii=False, indent=1)
io.open(TREE, "w", encoding="utf-8", newline="\n").write(s)
io.open(r"C:\myapp\data\chem_tree.json", "w", encoding="utf-8", newline="\n").write(s)
print("深度节点数（本次两章）:", total)


def walk(items, depth=0):
    n = 0
    for it in items:
        n += 1
        n += walk(it.get("sub") or [], depth + 1)
    return n


alln = 0
for b in tree["books"]:
    for c in b["chapters"]:
        for sec in c["sections"]:
            alln += walk(sec["points"])
print("全树节点总数:", alln)
