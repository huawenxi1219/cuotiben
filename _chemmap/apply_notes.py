# -*- coding: utf-8 -*-
"""把「人话备注」写进 chem_tree，并在背诵版里渲染。"""
import io
import json
import os
import sys

sys.path.insert(0, r"C:\myapp\_chemmap")
from notes import NOTES

TREE = r"C:\myapp\assets\chem_tree.json"
tree = json.load(io.open(TREE, encoding="utf-8"))

keys = sorted(NOTES, key=len, reverse=True)
hit = 0


def apply(items):
    global hit
    for it in items:
        t = str(it.get("title", ""))
        if it.get("note"):
            pass
        else:
            for k in keys:
                if k in t:
                    it["note"] = NOTES[k]
                    hit += 1
                    break
        apply(it.get("sub") or [])


for b in tree["books"]:
    for c in b["chapters"]:
        for s in c["sections"]:
            apply(s["points"])

s = json.dumps(tree, ensure_ascii=False, indent=1)
for p in (TREE, r"C:\myapp\data\chem_tree.json"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("已加备注:", hit, "条")
