# -*- coding: utf-8 -*-
"""全项目自检：数据完整性、资源缺失、功能入口是否落空、死代码、依赖缺失。

跑法：python _audit_app.py
退出码 0 = 没发现致命问题。
"""
import ast
import io
import json
import os
import re
import sys

ROOT = r"C:\myapp"
MAIN = os.path.join(ROOT, "main.py")
DATA = os.path.join(ROOT, "data")
ASSETS = os.path.join(ROOT, "assets")

problems = []
notes = []


def bad(msg):
    problems.append(msg)


# ---------- 1) 数据文件 ----------
def check_jsonl(path):
    if not os.path.exists(path):
        return 0
    n = 0
    ids = set()
    for i, line in enumerate(io.open(path, encoding="utf-8"), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception as ex:
            bad(f"{os.path.basename(path)} 第 {i} 行不是合法 JSON：{ex}")
            continue
        if not isinstance(obj, dict):
            bad(f"{os.path.basename(path)} 第 {i} 行不是对象")
            continue
        n += 1
        eid = obj.get("event_id")
        if eid:
            if eid in ids:
                bad(f"{os.path.basename(path)} 重复 event_id：{eid}")
            ids.add(eid)
    return n


for name in ("errors.jsonl", "notes.jsonl", "vocabulary.jsonl", "sentences.jsonl"):
    p = os.path.join(DATA, name)
    if os.path.exists(p):
        notes.append(f"  {name}: {check_jsonl(p)} 条")

# ---------- 2) 资源文件 ----------
for rel in ("assets/chem_map.png", "assets/chem_tree.json", "assets/splash.png"):
    if not os.path.exists(os.path.join(ROOT, rel)):
        bad(f"缺少资源：{rel}")

# ---------- 3) 入口与页面映射 ----------
src = io.open(MAIN, encoding="utf-8").read()
tree = ast.parse(src)

# 所有 def 的函数名
defs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

# 页面分发表里出现的 builder 名（形如 "xxx": lambda: build_yyy(...)）
for m in re.finditer(r'"([^"]{2,12})":\s*lambda:\s*(?:[a-zA-Z_][\w]*\.)?([a-zA-Z_]\w*)\s*\(', src):
    key, fn = m.group(1), m.group(2)
    if fn not in defs and fn not in ("ft",):
        bad(f"页面「{key}」指向未定义的 {fn}()")

# ---------- 4) 空回调 ----------
for m in re.finditer(r"on_(?:click|change)\s*=\s*lambda\s+e[^:\n]*:\s*(None|pass)\b", src):
    ln = src[:m.start()].count("\n") + 1
    bad(f"第 {ln} 行有空回调（点了没反应）")

# ---------- 5) 依赖 ----------
req = os.path.join(ROOT, "requirements.txt")
req_txt = io.open(req, encoding="utf-8").read().lower() if os.path.exists(req) else ""
imports = set()
for n in ast.walk(tree):
    if isinstance(n, ast.Import):
        for a in n.names:
            imports.add(a.name.split(".")[0])
    elif isinstance(n, ast.ImportFrom) and n.module:
        imports.add(n.module.split(".")[0])
local = {"mindmap_render", "a4_render", "flet", "os", "sys", "json", "re", "time", "io", "random",
         "threading", "zipfile", "shutil", "base64", "math", "traceback", "subprocess", "datetime",
         "string", "html", "collections", "itertools", "urllib", "http", "typing", "csv", "hashlib", "uuid"}
third = {i for i in imports if i not in local and not i.startswith("_")}
for mod in sorted(third):
    pkg = {"PIL": "pillow", "requests": "requests"}.get(mod, mod)
    if pkg.lower() not in req_txt:
        bad(f"requirements.txt 缺少依赖：{pkg}（代码用到了 {mod}）")

# ---------- 6) 知识树结构 ----------
tree_p = os.path.join(ASSETS, "chem_tree.json")
if os.path.exists(tree_p):
    try:
        t = json.load(io.open(tree_p, encoding="utf-8"))
        books = t.get("books", [])
        if not books:
            bad("chem_tree.json 没有任何册")
        for b in books:
            if not b.get("chapters"):
                bad(f"册「{b.get('name')}」没有章节")
            for c in b.get("chapters", []):
                if not c.get("sections"):
                    bad(f"章「{c.get('name')}」没有小节")
                for s in c.get("sections", []):
                    if not s.get("points"):
                        bad(f"节「{s.get('section')}」没有知识点")
        notes.append(f"  化学知识图：{len(books)} 册 / "
                     f"{sum(len(b['chapters']) for b in books)} 章 / "
                     f"{sum(len(s['points']) for b in books for c in b['chapters'] for s in c['sections'])} 知识点")
    except Exception as ex:
        bad(f"chem_tree.json 解析失败：{ex}")

# ---------- 7) 死代码（仅提示） ----------
called = set()
for n in ast.walk(tree):
    if isinstance(n, ast.Call):
        f = n.func
        if isinstance(f, ast.Name):
            called.add(f.id)
        elif isinstance(f, ast.Attribute):
            called.add(f.attr)
    elif isinstance(n, ast.Name):
        called.add(n.id)
unused = sorted(d for d in defs if d not in called and not d.startswith("__")
                and d not in ("main", "on_message"))
if unused:
    notes.append("  疑似未调用函数：" + ", ".join(unused[:12]) + ("…" if len(unused) > 12 else ""))

print("=== 数据 ===")
for n in notes:
    print(n)
print("\n=== 问题 ===")
if problems:
    for p in problems:
        print(" [X]", p)
    sys.exit(1)
print(" 没发现问题")
