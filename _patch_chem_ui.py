# -*- coding: utf-8 -*-
"""化学专用快捷指令：化学科目对话里多一排针对"记忆/推理/守恒"的按钮。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

OLD = '''                    ft.Container(
                        content=ft.Text("考考我", size=12, color="#CCCCCC"),
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                        border_radius=14, bgcolor="#24283B",
                        border=ft.border.all(1, "#414868"),
                        on_click=lambda e: ask_similar_q(),
                        ink=True),
                ], spacing=8, scroll=ft.ScrollMode.AUTO)'''

NEW = '''                    ft.Container(
                        content=ft.Text("考考我", size=12, color="#CCCCCC"),
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                        border_radius=14, bgcolor="#24283B",
                        border=ft.border.all(1, "#414868"),
                        on_click=lambda e: ask_similar_q(),
                        ink=True),
                    *([ft.Container(
                        content=ft.Text(_lbl, size=12, color="#CBD5E1"),
                        padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                        border_radius=14, bgcolor="#1F2A44",
                        border=ft.border.all(1, "#3B5BDB"),
                        on_click=lambda e, _q=_q: handle_send(_q),
                        ink=True)
                       for _lbl, _q in [
                           ("记忆还是推理？", "先告诉我这道题考的是要背的知识，还是要推的关系，再讲。"),
                           ("搭知识框架", "帮我把这一章的知识框架搭出来：物质性质 → 反应条件 → 反应 → 守恒，四层都给我。"),
                           ("用守恒解", "用守恒（电子/原子/电荷）来解这道题，一步步写。"),
                           ("关键条件", "这题的条件里，哪个是决定性的？漏了它会发生什么？"),
                       ]] if subject == "化学" else []),
                ], spacing=8, scroll=ft.ScrollMode.AUTO)'''

assert OLD in t, "快捷指令块未匹配"
t = t.replace(OLD, NEW, 1)

# 提示词补一段：学生问「化学怎么学」时怎么答
OLD_P = "如果学生说\"想用物理的方法学化学\"，先直接告诉他这条路错在哪，再给上面这套框架。"
NEW_P = (OLD_P + "\n"
         "  如果学生问\"化学到底怎么学\"，别讲空话，直接给三层结构：\n"
         "  ① 记忆层（绕不过）：元素性质、常见反应、实验现象——用卡片反复过；\n"
         "  ② 推理层：氧化还原/离子反应/平衡的判断规则；\n"
         "  ③ 计算层：守恒三件套（电子、原子、电荷）+ 过量判断。\n"
         "  再让他说出自己现在卡在哪一层，按那一层给具体练法。")
assert OLD_P in t
t = t.replace(OLD_P, NEW_P, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("化学快捷指令 + 提示词已加入")
