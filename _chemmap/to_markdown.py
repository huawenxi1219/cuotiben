# -*- coding: utf-8 -*-
"""把 chem_tree.json 转成 markdown（给 markmap 渲染标准思维导图）。"""
import io
import json

TREE = r"C:\myapp\assets\chem_tree.json"
MD = r"C:\myapp\化学总图.md"

tree = json.load(io.open(TREE, encoding="utf-8"))


def clean(s):
    return str(s).replace("\n", " ").strip()


out = ["---", "markmap:", "  colorFreezeLevel: 2", "  maxWidth: 320\n  initialExpandLevel: -1", "---", "",
       "# 高中化学 · 章末知识体系", ""]

for book in tree["books"]:
    out.append(f"## {clean(book['name'])}")
    for chap in book["chapters"]:
        out.append(f"### {clean(chap['name'])}")
        for sec in chap["sections"]:
            out.append(f"#### {clean(sec['section'])}")
            for pt in sec["points"]:
                out.append(f"- {clean(pt.get('title',''))}")
                for f in pt.get("facts") or []:
                    out.append(f"  - {clean(f)}")

                def walk(items, ind):
                    for it in items:
                        out.append(" " * ind + f"- {clean(it.get('title',''))}")
                        for f in it.get("facts") or []:
                            out.append(" " * (ind + 2) + f"- {clean(f)}")
                        walk(it.get("sub") or [], ind + 2)

                walk(pt.get("sub") or [], 2)

io.open(MD, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("markdown 行数:", len(out))
