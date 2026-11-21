# -*- coding: utf-8 -*-
"""audit6b：精确甄别循环闭包陷阱
判定为真实陷阱：循环体内定义的 FunctionDef/Lambda，
体内（含默认值）Load 引用循环变量名，且该名字不是本函数参数名，
且未通过任何默认参数或外层参数绑定该变量。
"""
import io, sys, ast
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
src = open(r'C:\myapp\main.py', encoding='utf-8', errors='replace').read()
tree = ast.parse(src)
out = []

def fn_param_names(fn):
    names = set()
    for a in fn.args.args + fn.args.posonlyargs + fn.args.kwonlyargs:
        names.add(a.arg)
    if fn.args.vararg:
        names.add(fn.args.vararg.arg)
    if fn.args.kwarg:
        names.add(fn.args.kwarg.arg)
    return names

def fn_default_bound_names(fn):
    bound = set()
    for d in (fn.args.defaults + fn.args.kw_defaults):
        if d is None:
            continue
        for nn in ast.walk(d):
            if isinstance(nn, ast.Name):
                bound.add(nn.id)
    return bound

for node in ast.walk(tree):
    if not isinstance(node, (ast.For, ast.AsyncFor)):
        continue
    loop_vars = []
    def collect(n):
        if isinstance(n, ast.Name):
            loop_vars.append(n.id)
        elif isinstance(n, (ast.Tuple, ast.List)):
            for e in n.elts:
                collect(e)
    collect(node.target)
    if not loop_vars:
        continue
    for sub in ast.walk(node):
        if sub is node or not isinstance(sub, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        params = fn_param_names(sub)
        defaults = fn_default_bound_names(sub)
        used = set()
        for nn in ast.walk(sub):
            if isinstance(nn, ast.Name) and isinstance(nn.ctx, ast.Load):
                used.add(nn.id)
        for v in loop_vars:
            if v in used and v not in params and v not in defaults:
                # 还要排除：该 def 若在循环内被立即调用（show 之类）且无延迟引用
                out.append('  L%d %s %s 引用循环变量 %s（未绑定，需人工判定是否延迟执行）'
                           % (sub.lineno, type(sub).__name__, sub.name if isinstance(sub, ast.FunctionDef) else '<lambda>', v))

print('\n'.join(out) if out else '未发现真实陷阱（全部已默认绑定）')
open(r'C:\myapp\_audit6b.txt', 'w', encoding='utf-8').write('\n'.join(out))
