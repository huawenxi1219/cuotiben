# -*- coding: utf-8 -*-
"""修正：选必2 应拆成三章，不能并成一章。"""
import io

P = r"C:\myapp\_chemmap\book_maps2.py"
t = io.open(P, encoding="utf-8").read()

OLD_START = '    ("选择性必修2", "第一章 原子结构与性质 / 第二章 分子结构 / 第三章 晶体结构", "6. 物质结构与性质（章末知识体系）", ['
assert OLD_START in t

i = t.index(OLD_START)
j = t.index('    ("选择性必修1", "第四章 化学反应与电能"', i)
block = t[i:j]

# 取出三组点
import re
def grab(start_kw, end_kw):
    a = block.index(start_kw)
    b = block.index(end_kw) if end_kw else len(block)
    return block[a:b]

seg1 = grab('("原子结构"', '("化学键"')
seg2 = grab('("化学键"', '("晶体结构与性质"')
seg3 = grab('("晶体结构与性质"', None)

new = ''
new += ('    ("选择性必修2", "第一章 原子结构与性质", "6.1 原子结构与元素周期律（章末知识体系）", [\n'
        + seg1 + '\n    ]),\n')
new += ('    ("选择性必修2", "第二章 分子结构与性质", "6.2 分子结构与性质（章末知识体系）", [\n'
        + seg2 + '\n    ]),\n')
new += ('    ("选择性必修2", "第三章 晶体结构与性质", "6.3 晶体结构与性质（章末知识体系）", [\n'
        + seg3 + '\n    ]),\n')

t = t[:i] + new + t[j:]
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("选必2 已拆成三章")
