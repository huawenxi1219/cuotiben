# -*- coding: utf-8 -*-
"""布局修复（真机截图确认的问题）：
   1) 三个主页面 Column 加 STRETCH，让卡片/按钮占满屏宽
   2) 顶部留出状态栏高度，标题不再被切
   3) 悬浮球移到右下角（悬浮在导航栏上方），减少压内容
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 三个页面 Column 加 STRETCH
OLD_HOME = "            ], spacing=14, scroll=ft.ScrollMode.AUTO)"
NEW_HOME = ("            ], spacing=14, scroll=ft.ScrollMode.AUTO,\n"
            "               horizontal_alignment=ft.CrossAxisAlignment.STRETCH)")
assert OLD_HOME in t
t = t.replace(OLD_HOME, NEW_HOME, 1)

OLD_MINE = "], spacing=20, scroll=ft.ScrollMode.AUTO)"
NEW_MINE = ("], spacing=20, scroll=ft.ScrollMode.AUTO,\n"
            "               horizontal_alignment=ft.CrossAxisAlignment.STRETCH)")
assert OLD_MINE in t
t = t.replace(OLD_MINE, NEW_MINE, 1)

# subject_page 已经是 expand 的 Row 容器，给外层 Column 也加 STRETCH
OLD_SUB = ("            ], spacing=15, expand=True)   # 有 expand 子控件时不能再开 scroll，否则撑不满、底部留白")
NEW_SUB = ("            ], spacing=15, expand=True,\n"
           "               horizontal_alignment=ft.CrossAxisAlignment.STRETCH)   # 撑满宽度，别留右侧黑边")
assert OLD_SUB in t
t = t.replace(OLD_SUB, NEW_SUB, 1)

# 2) 顶部状态栏留白：三处 height=10/6 的占位加高
t = t.replace("            home_page = ft.Column([\n                ft.Container(height=6),",
              "            home_page = ft.Column([\n                ft.Container(height=26),", 1)
t = t.replace("            subject_page = ft.Column([\n                ft.Container(height=10),",
              "            subject_page = ft.Column([\n                ft.Container(height=26),", 1)
t = t.replace("            mine_page = ft.Column([\n                ft.Container(height=10),",
              "            mine_page = ft.Column([\n                ft.Container(height=26),", 1)

# 3) 悬浮球初始位置：右下角（导航栏上方），不再压中部内容
OLD_BALL = '''                ball_state["ball_x"] = max(8, _bw - 44 - 6)
                ball_state["ball_y"] = max(60, min(_bh * 0.62, _bh - 120))'''
NEW_BALL = '''                ball_state["ball_x"] = max(8, _bw - 44 - 8)
                ball_state["ball_y"] = max(80, _bh - 150)'''
assert OLD_BALL in t
t = t.replace(OLD_BALL, NEW_BALL, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("布局修复已应用")
