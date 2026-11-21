# -*- coding: utf-8 -*-
"""第32轮：运行逻辑模式审计
A) 循环内 lambda/def 引用循环变量（无默认参数绑定）→ 闭包陷阱
B) 全部 threading.Thread 启动点 + 是否 daemon
C) on_click/on_change 回调里引用循环变量的裸 lambda
D) 可疑的 裸 .start() 后无保护 模式
"""
import io, sys, ast, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
out = []
src = open(r'C:\myapp\main.py', encoding='utf-8', errors='replace').read()
tree = ast.parse(src)

# ---------- A) 循环体内定义的 lambda/def 引用循环目标 ----------
out.append('==== A) 循环内函数定义引用循环变量（无默认参数默认值绑定） ====')
for node in ast.walk(tree):
    if isinstance(node, (ast.For, ast.AsyncFor)):
        loop_vars = []
        # 目标名（支持 tuple 解包）
        def collect(n):
            if isinstance(n, ast.Name):
                loop_vars.append(n.id)
            elif isinstance(n, ast.Tuple):
                for e in n.elts:
                    collect(e)
        collect(node.target)
        if not loop_vars:
            continue
        for sub in ast.walk(node):
            if sub is node:
                continue
            if isinstance(sub, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef)):
                # 函数体内引用的名字
                used = set()
                for nn in ast.walk(sub):
                    if isinstance(nn, ast.Name) and isinstance(nn.ctx, ast.Load):
                        used.add(nn.id)
                hits = [v for v in loop_vars if v in used]
                # 检查该函数定义是否在默认参数中绑定了循环变量
                if hits:
                    # 找到该 sub 所在容器（Call 的 keyword 默认参数检查略复杂，直接输出让代码审阅）
                    bound = False
                    if isinstance(sub, ast.Lambda) and sub.args.defaults:
                        for d in sub.args.defaults:
                            for nn in ast.walk(d):
                                if isinstance(nn, ast.Name) and nn.id in hits:
                                    bound = True
                    out.append('  L%d %s 引用循环变量 %s（默认绑定=%s）'
                               % (sub.lineno, type(sub).__name__, hits, bound))

# ---------- B) 全部 Thread 启动点 ----------
out.append('\n==== B) threading.Thread 启动点 ====')
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'start':
        # 找外层 Thread(...) 构造是否 daemon
        line = node.lineno
        # 向上找最近包含该 call 的 FunctionDef/语句
        out.append('  L%d .start()' % line)

out.append('\n==== B2) Thread( ... daemon= 显式设置 ====')
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Thread':
        kws = [k.arg for k in node.keywords if k.arg]
        out.append('  L%d Thread kwargs=%s' % (node.lineno, kws))

# ---------- C) 裸 lambda 事件绑定里引用循环变量的点 ----------
out.append('\n==== C) 事件回调 lambda（含循环变量引用） ====')
for node in ast.walk(tree):
    if isinstance(node, ast.Lambda):
        pass  # 已在 A 覆盖

# ---------- D) 可疑全局可变容器 + sleep 循环（后台轮询线程数） ----------
out.append('\n==== D) while 循环内 sleep（后台轮询线程） ====')
for node in ast.walk(tree):
    if isinstance(node, ast.While):
        has_sleep = False
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in ('sleep', 'time.sleep'):
                has_sleep = True
                break
        if has_sleep:
            # 找所在函数
            out.append('  while@L%d 含 sleep（轮询循环）' % node.lineno)

# ---------- E) 可能的内存泄漏：chat_dialog 重建前旧线程引用 ----------
out.append('\n==== E) open_chat 里的生成状态清理 ====')
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'open_chat':
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign):
                for t in sub.targets:
                    if isinstance(t, ast.Name):
                        out.append('  open_chat 赋值: %s @L%d' % (t.id, sub.lineno))

open(r'C:\myapp\_audit6.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('审计完成，写入 _audit6.txt')
