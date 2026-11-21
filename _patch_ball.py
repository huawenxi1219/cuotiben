# -*- coding: utf-8 -*-
"""悬浮球改小、贴右边缘、半透明，尽量不挡内容。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 球体缩小到 44，更透明，文字小一号
OLD = '''            ball_inner = ft.Container(
                content=ft.Text("AI", size=20, color="white", weight=ft.FontWeight.BOLD),
                width=56,
                height=56,
                border_radius=28,
                bgcolor="#CC1C1C26",
                blur=16,
                border=ft.border.all(1, "#44FFFFFF"),
                shadow=ft.BoxShadow(blur_radius=24, color="#887AA2F7", spread_radius=1),'''
NEW = '''            ball_inner = ft.Container(
                content=ft.Text("AI", size=15, color="#E8EBF5", weight=ft.FontWeight.W_500),
                width=44,
                height=44,
                border_radius=22,
                bgcolor="#8C1C1C26",
                blur=10,
                border=ft.border.all(1, "#33FFFFFF"),
                shadow=ft.BoxShadow(blur_radius=12, color="#447AA2F7", spread_radius=0),'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 初始位置贴右边（原来 300,500 在窄屏上几乎贴边但会压住内容）
OLD2 = '''            ball_container = ft.Container(
                content=ai_ball,
                left=ball_state["ball_x"],
                top=ball_state["ball_y"],
            )'''
NEW2 = '''            try:
                _bw = page.width or (page.window.width if page.window else None) or 360
                _bh = page.height or (page.window.height if page.window else None) or 640
                ball_state["ball_x"] = max(8, _bw - 44 - 6)
                ball_state["ball_y"] = max(60, min(_bh * 0.62, _bh - 120))
            except BaseException:
                pass
            ball_container = ft.Container(
                content=ai_ball,
                left=ball_state["ball_x"],
                top=ball_state["ball_y"],
            )'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# 3) 拖动吸附阈值按新尺寸调整（28 -> 22）
t = t.replace('if ball_state["ball_x"] + 28 < w / 2:',
              'if ball_state["ball_x"] + 22 < w / 2:', 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("悬浮球已缩小并贴边")
