# -*- coding: utf-8 -*-
"""背诵版内容体检：空条目、重复、层级错位、计数。"""
import io
import json
import re

TREE = r"C:\myapp\assets\chem_tree.json"
tree = json.load(io.open(TREE, encoding="utf-8"))

issues = []


def walk(items, depth=0):
    n = 0
    for it in items:
        n += 1
        t = str(it.get("title", "")).strip()
        if not t:
            issues.append("空标题")
        if not (it.get("detail") or "").strip() and not it.get("facts") and not it.get("sub"):
            issues.append(f"空内容：{t}")
        n += walk(it.get("sub") or [], depth + 1)
    return n


total = 0
top = 0
titles_all = []
for b in tree["books"]:
    for c in b["chapters"]:
        # 章名重复检查
        for s in c["sections"]:
            seen = set()
            for p in s["points"]:
                t = p.get("title", "")
                if t in seen:
                    issues.append(f"同一节重复：{c['name']} / {s['section']} / {t}")
                seen.add(t)
            top += len(s["points"])
            total += walk(s["points"])

print(f"【规模】册 {len(tree['books'])} | 章 {sum(len(b['chapters']) for b in tree['books'])} | "
      f"顶级知识点 {top} | 含子级节点 {total}")

print("\n【册—章结构】")
for b in tree["books"]:
    print(f"  {b['name']}: " + " / ".join(c["name"] for c in b["chapters"]))

print("\n【问题】")
if issues:
    for i in issues[:20]:
        print("  ✗", i)
else:
    print("  无")

# 方程式粗检：括号是否配对、箭头格式
print("\n【方程式抽检】")
bad_eq = 0
for b in tree["books"]:
    for c in b["chapters"]:
        for s in c["sections"]:
            for e in s.get("equations", []):
                eq = e.get("eq", "")
                if eq.count("（") != eq.count("）") or eq.count("(") != eq.count(")"):
                    print("  ✗ 括号不配对:", eq)
                    bad_eq += 1
print("  括号问题:", bad_eq)
