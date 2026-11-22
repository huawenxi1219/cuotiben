# -*- coding: utf-8 -*-
"""测试 _plain_ai 的清洗效果（用真实字符串，避免命令行转义干扰）。"""
import io
import sys

sys.path.insert(0, r"C:\myapp")
src = io.open(r"C:\myapp\main.py", encoding="utf-8").read()
i = src.index("def _plain_ai(")
j = src.index("def _install_deepseek_post_shim(")
ns = {}
exec(src[i:j], ns)
f = ns["_plain_ai"]

cases = [
    r"所以 $x^2 + 2x + 1 = 0$，得 $x = -1$",
    r"$\frac{a}{b}$ 与 $\sqrt{3}$",
    r"**重点**：$\Delta H < 0$",
    r"H$_2$SO$_4$ 与 CO$_3^{2-}$",
    r"\times \div \leq \rightarrow",
    r"\[ \text{速率} = \frac{\Delta c}{\Delta t} \]",
    "#### 小标题\n- 第一条\n- 第二条",
]

for c in cases:
    print("原文:", c)
    print("结果:", f(c))
    print("-" * 40)
