# -*- coding: utf-8 -*-
"""静态检查：调用本地函数时，必需参数是否都给齐了（位置 + 关键字一起算）。"""
import ast, io, sys
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\myapp\main.py"
src = io.open(SRC, encoding="utf-8").read()
tree = ast.parse(src)

defs = defaultdict(list)
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = node.args
        pos = [a.arg for a in args.args if a.arg not in ("self", "cls")]
        ndef = len(args.defaults)
        required_pos = pos[:len(pos) - ndef] if ndef else pos[:]
        required_kw = [a.arg for a, d in zip(args.kwonlyargs, args.kw_defaults) if d is None]
        defs[node.name].append({
            "pos": pos,
            "required_pos": required_pos,
            "required_kw": required_kw,
            "vararg": args.vararg is not None,
            "kwargs": args.kwarg is not None,
            "line": node.lineno,
        })

problems = []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        continue
    name = node.func.id
    if name not in defs or len(defs[name]) != 1:
        continue
    d = defs[name][0]
    if d["kwargs"]:
        continue
    provided = set()
    for i, a in enumerate(node.args):
        if isinstance(a, ast.Starred):
            provided |= set(d["pos"])          # *args 展开，放弃精确判断
            break
        if i < len(d["pos"]):
            provided.add(d["pos"][i])
        else:
            if not d["vararg"]:
                problems.append((node.lineno, name, f"位置参数过多（第 {i+1} 个）", d["line"]))
    for kw in node.keywords:
        if kw.arg is None:
            provided |= set(d["pos"]) | set(d["required_kw"])
        else:
            provided.add(kw.arg)
    missing = [p for p in d["required_pos"] + d["required_kw"] if p not in provided]
    if missing:
        problems.append((node.lineno, name, f"缺少参数 {missing}", d["line"]))

seen = set()
print(f"参数问题: {len({(p[0], p[1]) for p in problems})}")
for ln, name, msg, dln in problems:
    if (ln, name, msg) in seen:
        continue
    seen.add((ln, name, msg))
    print(f"  L{ln}: {name}() {msg}   （定义在 L{dln}）")
