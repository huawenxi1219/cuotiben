# -*- coding: utf-8 -*-
"""代码审计：找空壳功能、假实现、UI 承诺但没做的东西。"""
import ast, io, re, sys

SRC = r"C:\myapp\main.py"
src = io.open(SRC, encoding="utf-8").read()
lines = src.splitlines()
tree = ast.parse(src)

print("=== 1) 空函数（只有 pass / 只 return 常量）===")
for n in ast.walk(tree):
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        body = [x for x in n.body
                if not (isinstance(x, ast.Expr) and isinstance(x.value, ast.Constant))]
        if len(body) == 1 and isinstance(body[0], ast.Pass):
            print(f"  L{n.lineno}: {n.name}() -> pass")
        elif len(body) == 1 and isinstance(body[0], ast.Return) and body[0].value is None:
            print(f"  L{n.lineno}: {n.name}() -> return None")

print("\n=== 2) 空回调 / 占位文案 ===")
for m in re.finditer(r"on_(?:click|change|hover)=lambda e[^,)\n]*:\s*(?:None|pass)", src):
    ln = src[:m.start()].count("\n") + 1
    print(f"  L{ln}: {m.group(0)[:60]}")
for kw in ("开发中", "敬请期待", "暂未实现", "TODO", "FIXME", "占位"):
    for m in re.finditer(kw, src):
        ln = src[:m.start()].count("\n") + 1
        print(f"  L{ln}: 含「{kw}」")

print("\n=== 3) 界面文案承诺的能力，代码里是否存在 ===")
promises = {
    "AI 深度搜索": "ai_deep_search",
    "批量录题": "batch_import",
    "知识框架": "show_knowledge_framework",
    "学习画像": "show_learning_profile",
    "单词本设置": "show_vocab_settings_dialog",
    "批量重打标签": "batch_retag",
    "合并恢复": "on_merge_result",
    "回收站": "move_to_recycle",
    "手环": "band_",
}
for label, needle in promises.items():
    hit = needle in src
    print(f"  {'✅' if hit else '❌'} {label:12s} -> {needle}")

print("\n=== 4) 定义了但从未被调用的函数（可能是死功能）===")
defs = {}
for n in ast.walk(tree):
    if isinstance(n, ast.FunctionDef):
        defs.setdefault(n.name, n.lineno)
called = set()
for n in ast.walk(tree):
    if isinstance(n, ast.Call):
        f = n.func
        if isinstance(f, ast.Name):
            called.add(f.id)
        elif isinstance(f, ast.Attribute):
            called.add(f.attr)
never = [(name, ln) for name, ln in defs.items()
         if name not in called and not name.startswith("_") and name != "main"]
for name, ln in sorted(never, key=lambda x: x[1])[:25]:
    print(f"  L{ln}: {name}() 从未被调用")

print(f"\n总行数: {len(lines)}")
