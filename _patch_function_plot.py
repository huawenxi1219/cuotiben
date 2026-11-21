# -*- coding: utf-8 -*-
"""给对话加「函数图像」能力 + 学科解题策略提示词。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------------- 1) 函数图像渲染器 ----------------
FUNC = r'''
def _svg_function(title, exprs, xmin=-5.0, xmax=5.0, ymin=None, ymax=None,
                  xlabel="x", ylabel="y"):
    """把数学表达式画成坐标系曲线。exprs 可以是 ["x^2", ...] 或 [{"f":..,"label":..}]"""
    import math
    if not exprs:
        return ""
    if not isinstance(exprs, (list, tuple)):
        exprs = [exprs]

    ALLOW = {
        "x": 0.0, "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan,
        "sqrt": math.sqrt, "log": math.log10, "ln": math.log, "lg": math.log10,
        "exp": math.exp, "abs": abs, "pi": math.pi, "e": math.e,
        "floor": math.floor, "ceil": math.ceil,
    }

    def _ev(expr, x):
        s = str(expr).replace("^", "**").replace("×", "*").replace("÷", "/")
        s = s.replace("π", "pi")
        g = dict(ALLOW)
        g["x"] = x
        return eval(s, {"__builtins__": {}}, g)  # 只允许白名单里的名字

    series = []
    colors = ["#7AA2F7", "#9ECE6A", "#E0AF68", "#F7768E", "#BB9AF7"]
    for i, it in enumerate(exprs[:5]):
        if isinstance(it, dict):
            f, lb = it.get("f") or it.get("expr") or "", it.get("label") or it.get("f") or ""
            c = it.get("color") or colors[i % len(colors)]
        else:
            f, lb, c = it, str(it), colors[i % len(colors)]
        if not str(f).strip():
            continue
        pts = []
        N = 240
        for k in range(N + 1):
            x = float(xmin) + (float(xmax) - float(xmin)) * k / N
            try:
                y = float(_ev(f, x))
            except BaseException:
                pts.append(None)
                continue
            if math.isnan(y) or math.isinf(y):
                pts.append(None)
            else:
                pts.append((x, y))
        series.append((str(lb), c, pts))

    if not series:
        return ""

    ys = [p[1] for _l, _c, ps in series for p in ps if p]
    if not ys:
        return ""
    if ymin is None:
        ymin = min(ys)
    if ymax is None:
        ymax = max(ys)
    lo, hi = float(ymin), float(ymax)
    if hi - lo < 1e-9:
        hi, lo = hi + 1, lo - 1
    span = hi - lo
    hi += span * 0.08
    lo -= span * 0.08

    W, H = 660, 400
    pad_l, pad_r, pad_t, pad_b = 64, 36, 58, 58
    cw, ch = W - pad_l - pad_r, H - pad_t - pad_b

    def sx(x): return pad_l + (float(x) - float(xmin)) / (float(xmax) - float(xmin)) * cw
    def sy(y): return pad_t + (hi - float(y)) / (hi - lo) * ch

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#1A1B26" rx="16"/>',
         f'<text x="{W/2}" y="32" fill="#EEEEEE" font-size="17" font-weight="bold" text-anchor="middle">{title}</text>']

    # 网格 + 刻度
    for i in range(5):
        yv = lo + (hi - lo) * i / 4
        y = sy(yv)
        p.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W-pad_r}" y2="{y:.1f}" stroke="#24283B" stroke-width="1"/>')
        p.append(f'<text x="{pad_l-8}" y="{y+4:.1f}" fill="#777777" font-size="11" text-anchor="end">{yv:.2f}</text>')
        xv = float(xmin) + (float(xmax) - float(xmin)) * i / 4
        x = sx(xv)
        p.append(f'<line x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{H-pad_b}" stroke="#24283B" stroke-width="1"/>')
        p.append(f'<text x="{x:.1f}" y="{H-pad_b+20}" fill="#777777" font-size="11" text-anchor="middle">{xv:.2f}</text>')

    # 坐标轴（x=0 / y=0 在范围内时画出来）
    if float(xmin) <= 0 <= float(xmax):
        p.append(f'<line x1="{sx(0):.1f}" y1="{pad_t}" x2="{sx(0):.1f}" y2="{H-pad_b}" stroke="#565F89" stroke-width="1.5"/>')
    if lo <= 0 <= hi:
        p.append(f'<line x1="{pad_l}" y1="{sy(0):.1f}" x2="{W-pad_r}" y2="{sy(0):.1f}" stroke="#565F89" stroke-width="1.5"/>')

    # 曲线
    for lb, c, pts in series:
        seg, segs = [], []
        for pt in pts:
            if pt is None:
                if len(seg) > 1:
                    segs.append(seg)
                seg = []
            else:
                seg.append(pt)
        if len(seg) > 1:
            segs.append(seg)
        for s2 in segs:
            d = " ".join(("M" if i2 == 0 else "L") + f"{sx(x):.1f},{sy(min(max(y, lo), hi)):.1f}"
                         for i2, (x, y) in enumerate(s2))
            p.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>')

    # 图例
    lx = pad_l + 6
    for lb, c, _ps in series:
        p.append(f'<rect x="{lx}" y="{H-26}" width="12" height="12" rx="3" fill="{c}"/>')
        p.append(f'<text x="{lx+18}" y="{H-15}" fill="#CCCCCC" font-size="12">{lb[:22]}</text>')
        lx += 26 + min(len(lb), 22) * 8

    p.append(f'<text x="{W/2}" y="{H-4}" fill="#888888" font-size="11" text-anchor="middle">{xlabel} / {ylabel}</text>')
    p.append('</svg>')
    return "".join(p)


'''
ANCHOR = "def render_chart_from_spec(spec):"
assert ANCHOR in t
t = t.replace(ANCHOR, FUNC.lstrip("\n") + ANCHOR, 1)

# ---------------- 2) 注册 function 类型 ----------------
OLD = """        if t == "flow":
            return _svg_flow(title, spec.get("steps", []))"""
NEW = """        if t == "flow":
            return _svg_flow(title, spec.get("steps", []))
        if t == "function":
            return _svg_function(title,
                                 spec.get("exprs", []),
                                 spec.get("xmin", -5), spec.get("xmax", 5),
                                 spec.get("ymin"), spec.get("ymax"),
                                 spec.get("xlabel", "x"), spec.get("ylabel", "y"))"""
assert OLD in t
t = t.replace(OLD, NEW, 1)

# ---------------- 3) 提示词：图解法 + 学科策略 ----------------
OLD2 = """【可视化规则 - 必须遵守】
当回答涉及趋势、占比、比较、流程、机制、因果、架构、关系、时间线、状态机、算法步骤、参数变化时，在回复最末尾附一个 ```chart 代码块，内容必须是 JSON。"""
NEW2 = """【可视化规则 - 必须遵守】
当回答涉及趋势、占比、比较、流程、机制、因果、架构、关系、时间线、状态机、算法步骤、参数变化时，在回复最末尾附一个 ```chart 代码块，内容必须是 JSON。

【图解法优先】
只要题目涉及「函数形状、单调性、极值、交点、范围」，或物理的 v-t/s-t/F-x 关系、化学的滴定/反应进程、地理的剖面与分布，**先画图再讲**，用下面的 function 类型：

```chart
{"type":"function","title":"f(x)=x^2-4x+3","exprs":[{"f":"x^2-4*x+3","label":"f(x)"}],"xmin":-1,"xmax":5,"xlabel":"x","ylabel":"f(x)"}
```

要点：
- 表达式只能用这些名字：x, sin, cos, tan, sqrt, log(lg), ln, exp, abs, pi, e；乘方用 ^，乘除用 * /
- 多条曲线就写多个 exprs（最多 5 条），每条给 label
- 画完图，接下来的讲解必须指着图说（"看图，顶点在 x=2"），不要画完就丢一边

【按学科选讲法（必须遵守）】
- 化学：先抓「有什么物质、什么条件」，再推「发生什么反应」，最后用守恒（电子/原子/电荷）算。禁止一上来堆公式。遇到实验题先说清装置和目的。
- 地理：按「位置 → 地形/气候/水文 → 影响 → 结论」的因果链走，每一环都要说"为什么"，不许只给结论。选择题要把每个选项错在哪说清。
- 数学：先画图或举特例把"长什么样"讲明白，再谈解法；抽象函数先给一个具体满足条件的例子。
- 物理：先受力/过程分析（能画图就画），再列方程。
- **顺序固定**：先理解（图解/例子）→ 再一般方法（步骤）→ 最后才给"秒杀公式/结论"，并且必须补一句"这个公式只在什么条件下能用"。"""
assert OLD2 in t, "可视化规则未匹配"
t = t.replace(OLD2, NEW2, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("函数图像 + 学科策略 已加入")
