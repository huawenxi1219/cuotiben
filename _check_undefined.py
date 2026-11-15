# -*- coding: utf-8 -*-
"""静态检查：用 symtable 精确找出「引用了但从未定义」的全局名（NameError 风险）。

上次的 bug：call_ai_stream 里调用 _cfg_thinking_off()，但该函数从未定义，
py_compile 通过、只有真正发消息时才抛 NameError —— 对话一个字都不回。
"""
import builtins
import io
import symtable
import sys

TARGET = sys.argv[1] if len(sys.argv) > 1 else r"C:\myapp\main.py"
src = io.open(TARGET, encoding="utf-8").read()
top = symtable.symtable(src, TARGET, "exec")

# 模块级定义的名字
module_names = set()
for s in top.get_symbols():
    if s.is_assigned() or s.is_imported() or s.is_namespace() or s.is_parameter():
        module_names.add(s.get_name())

BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__spec__", "__package__"}
problems = []


def walk(table, where):
    for s in table.get_symbols():
        n = s.get_name()
        if s.is_global() and not s.is_assigned() and not s.is_imported():
            if n not in module_names and n not in BUILTINS:
                problems.append((where, table.get_lineno(), n))
    for child in table.get_children():
        walk(child, child.get_name())


walk(top, "<module>")

seen = set()
uniq = []
for where, ln, name in problems:
    if (where, name) in seen:
        continue
    seen.add((where, name))
    uniq.append((where, ln, name))

if uniq:
    print(f"[FAIL] 未定义名称 {len(uniq)} 个（运行到才会 NameError）：")
    for where, ln, name in uniq[:30]:
        print(f"   {where}() 里引用了 '{name}'")
    sys.exit(1)
print("[OK]   未定义名称检查  未发现问题")
