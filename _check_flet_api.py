# -*- coding: utf-8 -*-
"""Flet API 静态校验器：
1) 检查 ft.X(...) 的关键字参数是否存在于该控件的构造签名
2) 检查 ft.X.Y 这类属性访问是否真的存在
3) 检查 ft.xxx 模块式调用是否存在
不用跑 App 就能发现 "unexpected keyword argument" 这类崩溃。
"""
import ast, inspect, io, sys
import flet as ft

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\myapp\main.py"
src = io.open(SRC, encoding="utf-8").read()
tree = ast.parse(src)

problems = []

def sig_kwargs(cls):
    try:
        sig = inspect.signature(cls.__init__)
    except (ValueError, TypeError):
        return None, False
    params = list(sig.parameters.values())
    has_kwargs = any(p.kind == p.VAR_KEYWORD for p in params)
    names = {p.name for p in params if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)}
    return names, has_kwargs

for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    f = node.func
    # ft.X(...)
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "ft":
        cls = getattr(ft, f.attr, None)
        if cls is None:
            problems.append((node.lineno, f"ft.{f.attr} 不存在"))
            continue
        names, has_kwargs = sig_kwargs(cls)
        if names is None or has_kwargs:
            continue
        for kw in node.keywords:
            if kw.arg and kw.arg not in names:
                problems.append((node.lineno, f"ft.{f.attr}(...) 不支持参数 '{kw.arg}'"))
        # 位置参数个数
        try:
            sig = inspect.signature(cls.__init__)
            max_pos = sum(1 for p in sig.parameters.values()
                          if p.kind == p.POSITIONAL_ONLY or p.kind == p.POSITIONAL_OR_KEYWORD) - 1
            if len(node.args) > max_pos and not any(
                    p.kind == p.VAR_POSITIONAL for p in sig.parameters.values()):
                problems.append((node.lineno, f"ft.{f.attr}(...) 位置参数过多（{len(node.args)} > {max_pos}）"))
        except (ValueError, TypeError):
            pass

    # ft.X.Y （属性链）
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute) \
            and isinstance(f.value.value, ast.Name) and f.value.value.id == "ft":
        base = getattr(ft, f.value.attr, None)
        if base is not None and not hasattr(base, f.attr):
            problems.append((node.lineno, f"ft.{f.value.attr}.{f.attr} 不存在"))

# 单独扫 ft.X.Y 属性的读取（非调用）
for node in ast.walk(tree):
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) \
            and isinstance(node.value.value, ast.Name) and node.value.value.id == "ft":
        base = getattr(ft, node.value.attr, None)
        if base is not None and not hasattr(base, node.attr):
            problems.append((node.lineno, f"ft.{node.value.attr}.{node.attr} 不存在"))

seen = set()
uniq = []
for ln, msg in sorted(problems):
    if (ln, msg) in seen:
        continue
    seen.add((ln, msg))
    uniq.append((ln, msg))

print(f"共发现 {len(uniq)} 个 API 问题\n")
for ln, msg in uniq[:60]:
    print(f"  L{ln}: {msg}")
