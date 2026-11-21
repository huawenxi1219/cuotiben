# -*- coding: utf-8 -*-
"""B/D/E：页面大标题、空状态、动效时长统一。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 空状态组件 ----------
HELPER = '''
            def u_empty(icon, title, hint=""):
                """统一的空状态：图标 + 一句话 + 补充说明"""
                _kids = [ft.Text(icon, size=38, opacity=0.55),
                         ft.Text(title, size=15, color=C_TEXT2, weight=ft.FontWeight.W_500)]
                if hint:
                    _kids.append(ft.Text(hint, size=12, color=C_TEXT2, opacity=0.7))
                return ft.Container(
                    content=ft.Column(_kids, spacing=8,
                                      horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center, padding=36)

'''
anchor = "            def u_primary_btn(text, on_click, icon=None, color=\"#7AA2F7\"):"
assert anchor in t
t = t.replace(anchor, HELPER.lstrip("\n") + anchor, 1)

# ---------- 空状态替换 ----------
t = t.replace('content=ft.Text("  暂无错题", size=16, color=ft.Colors.GREY_500),',
              'content=u_empty("📕", "还没有错题", "回首页拍一张，AI 会帮你录进来"),', 1)
t = t.replace('content=ft.Text("  暂无笔记", size=16, color=ft.Colors.GREY_500),',
              'content=u_empty("📓", "还没有笔记", "点右上角「+」写第一条"),', 1)
t = t.replace('task_list.controls.append(ft.Text("  暂无任务", size=16))',
              'task_list.controls.append(u_empty("✅", "还没有任务", "写下今天要做的第一件事"))', 1)

# ---------- 页面大标题 ----------
t = t.replace('ft.Text("📚 学科浏览", size=24, weight=ft.FontWeight.BOLD),',
              'ft.Text("学科", size=28, weight=ft.FontWeight.W_700, color=C_TEXT),', 1)
t = t.replace('ft.Text("⚙️ 个人中心", size=24, weight=ft.FontWeight.BOLD),',
              'ft.Text("我的", size=28, weight=ft.FontWeight.W_700, color=C_TEXT),', 1)

# ---------- 动效时长统一：页面 260ms / 元素 160ms ----------
for old, new in [("animate_opacity=ft.Animation(240, ft.AnimationCurve.EASE_OUT)",
                  "animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT)"),
                 ("animate_scale=ft.Animation(260, ft.AnimationCurve.EASE_OUT)",
                  "animate_scale=ft.Animation(260, ft.AnimationCurve.EASE_OUT_BACK)")]:
    t = t.replace(old, new)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("大标题 / 空状态 / 动效 已统一")
