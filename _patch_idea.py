# -*- coding: utf-8 -*-
"""把"我的思路"做成显眼字段；补化学/数学的学科框架提示。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 录题表单：思路字段更醒目
OLD = '''            idea_input = ft.TextField(label="我的理解", multiline=True, min_lines=2,'''
NEW = '''            idea_input = ft.TextField(label="我的思路：当时怎么想的、卡在哪一步（很重要）",
                                      hint_text="例：我一开始想先求导找极值，但没想清楚端点要不要带进去",
                                      multiline=True, min_lines=3,'''
assert OLD in t, "idea_input 未匹配"
t = t.replace(OLD, NEW, 1)

# 2) 学科框架：补一条"化学不是物理那套"
OLD2 = "- 化学：先抓「有什么物质、什么条件」，再推「发生什么反应」，最后用守恒（电子/原子/电荷）算。禁止一上来堆公式。遇到实验题先说清装置和目的。"
NEW2 = """- 化学：**先说清"化学不是物理那套"**——物理有少数公理能推到底，化学是"物质性质 + 反应条件 + 守恒关系"织成的网，靠一条公式通吃必然崩。
  固定四步：① 有什么物质（状态、酸碱性、氧化性/还原性）→ ② 什么条件（浓度、温度、催化剂）→ ③ 发生什么反应（能不能发生、谁过量）→ ④ 用守恒算（电子守恒/原子守恒/电荷守恒）。
  如果学生说"想用物理的方法学化学"，先直接告诉他这条路错在哪，再给上面这套框架。禁止一上来堆方程式。"""
assert OLD2 in t, "化学规则未匹配"
t = t.replace(OLD2, NEW2, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("思路字段 + 化学框架 已更新")
