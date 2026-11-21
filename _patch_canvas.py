# -*- coding: utf-8 -*-
"""修思维导图崩溃：flet 0.28.3 没有 ft.canvas，改用旋转的细 Container 画连线。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 两根连线
OLD1 = '''                            shapes.append(ft.canvas.Line(
                                p[0] + NODE_W, p[1] + NODE_H / 2,
                                c[0] - 8, c[1] + NODE_H / 2,
                                paint=ft.canvas.Paint(stroke_width=2, color="#414868")))'''
NEW1 = '''                            shapes.append(_conn(p[0] + NODE_W, p[1] + NODE_H / 2,
                                                c[0] - 8, c[1] + NODE_H / 2, "#414868"))'''
assert OLD1 in t
t = t.replace(OLD1, NEW1, 1)

OLD2 = '''                                shapes.append(ft.canvas.Line(
                                    cp[0] + NODE_W, cp[1] + NODE_H / 2,
                                    cc[0] - 8, cc[1] + NODE_H / 2,
                                    paint=ft.canvas.Paint(stroke_width=2, color="#33364D")))'''
NEW2 = '''                                shapes.append(_conn(cp[0] + NODE_W, cp[1] + NODE_H / 2,
                                                    cc[0] - 8, cc[1] + NODE_H / 2, "#33364D"))'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# 2) Canvas → 直接用 shapes 列表
OLD3 = '''                    canvas = ft.canvas.Canvas(width=LAYOUT_W, height=LAYOUT_H, shapes=shapes)'''
NEW3 = '''                    # flet 0.28 没有 canvas 组件：连线就是一堆旋转的细 Container'''
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

t = t.replace("ft.Stack([canvas] + nodes, width=LAYOUT_W, height=LAYOUT_H)",
              "ft.Stack(shapes + nodes, width=LAYOUT_W, height=LAYOUT_H)", 1)

# 3) 连线构造函数（放在 rebuild_mindmap_view 之前）
HELPER = '''
                def _conn(x1, y1, x2, y2, color):
                    """两点之间的一条细线：用旋转的 2px 高 Container 顶替 canvas"""
                    import math as _m
                    dx, dy = float(x2) - float(x1), float(y2) - float(y1)
                    L = max(2.0, _m.hypot(dx, dy))
                    ang = _m.atan2(dy, dx)
                    return ft.Container(
                        left=(x1 + x2) / 2.0 - L / 2.0, top=(y1 + y2) / 2.0 - 1,
                        width=L, height=2, bgcolor=color, rotate=ang,
                        border_radius=1)

'''
anchor = "                def rebuild_mindmap_view(force=False):"
assert anchor in t
t = t.replace(anchor, HELPER.lstrip("\n") + anchor, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("思维导图连线已改为 Container")
