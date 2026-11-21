# -*- coding: utf-8 -*-
import ast
src = open(r'C:\myapp\main.py', encoding='utf-8', errors='replace').read()
tree = ast.parse(src)
print('OK parsed')
for child in ast.iter_child_nodes(tree):
    if isinstance(child, ast.FunctionDef):
        print('top:', child.name, child.lineno)
