# -*- coding: utf-8 -*-
"""逻辑审计：找"定义了没人调用""按钮回调是空的""永远不可见的控件"等空壳。"""
import ast, io, re, collections

SRC = r"C:\myapp\main.py"
txt = io.open(SRC, encoding="utf-8").read()
tree = ast.parse(txt)

# ---------- 1) 定义但从未被引用（除定义行外一次都没出现） ----------
defs = {}
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        defs.setdefault(node.name, []).append(node.lineno)

unused = []
for name, lines in defs.items():
    if name.startswith("__"):
        continue
    # 统计标识符出现次数（粗略但够用）
    n = len(re.findall(r"\b" + re.escape(name) + r"\b", txt))
    if n <= len(lines):          # 只出现在 def 处
        unused.append((name, lines[0], n))
print("=== A. 定义了但没有任何调用 ===")
for name, ln, n in sorted(unused, key=lambda x: x[1]):
    print(f"  L{ln:<6} {name}  (出现 {n} 次)")

# ---------- 2) 空回调 ----------
print("\n=== B. 空回调 / 占位函数 ===")
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and len(node.body) == 1:
        b = node.body[0]
        if isinstance(b, ast.Pass):
            print(f"  L{node.lineno:<6} def {node.name}: 只有 pass")
        elif isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) and isinstance(b.value.value, str):
            print(f"  L{node.lineno:<6} def {node.name}: 只有 docstring")

for node in ast.walk(tree):
    if isinstance(node, ast.Lambda) and isinstance(node.body, ast.Constant) and node.body.value is None:
        print(f"  L{node.lineno:<6} lambda e: None")

# ---------- 3) visible=False 的控件，后面有没有被置 True ----------
print("\n=== C. visible=False 且从未被置 True 的变量 ===")
falses = collections.defaultdict(list)
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        for kw in node.keywords:
            if kw.arg == "visible" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                tgt = node.func
                if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name):
                    falses[tgt.value.id].append(node.lineno)
for var, lines in falses.items():
    if re.search(r"\b" + re.escape(var) + r"\s*\.\s*visible\s*=\s*True", txt):
        continue
    print(f"  L{lines[0]:<6} {var}.visible=False（全文件没有置 True）")

# ---------- 4) 疑似 TODO / 占位 ----------
print("\n=== D. TODO / 占位 / 未实现 ===")
for i, line in enumerate(txt.splitlines(), 1):
    if re.search(r"TODO|FIXME|占位|未实现|not implemented|pass  #", line):
        print(f"  L{i:<6} {line.strip()[:90]}")

# ---------- 5) 每个 IF 里只有 pass/空的 ----------
print("\n=== E. 只有 pass 的 except/if 分支（吞异常）统计 ===")
c = len(re.findall(r"except[^:]*:\s*\n\s*(?:#.*\n\s*)*pass", txt))
print(f"  except...pass 共 {c} 处（这些地方出错是静默的）")
