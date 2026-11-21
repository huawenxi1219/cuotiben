# -*- coding: utf-8 -*-
"""把「化学知识总图」内置进 App：化学学科多一张卡，点开是可缩放的矢量级大图。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 化学多一张卡
OLD = '''                cards_config = all_cards if subject == "英语" else all_cards[:3]'''
NEW = '''                if subject == "英语":
                    cards_config = all_cards
                elif subject == "化学":
                    cards_config = all_cards[:3] + [("🧪", "化学总图", "#22303A")]
                else:
                    cards_config = all_cards[:3]'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 总图页面构造器
OLD2 = '''                    "思维导图": lambda: build_knowledge_page(subject),'''
NEW2 = '''                    "思维导图": lambda: build_knowledge_page(subject),
                    "化学总图": lambda: _build_chem_map_page(),'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# 3) 页面实现（插在 build_knowledge_page 之前）
ANCHOR = "            def build_knowledge_page(subject):"
PAGE = '''            def _build_chem_map_page():
                """人教版高中化学三年知识总图：整张可缩放拖动"""
                return ft.Column([
                    ft.Text("人教版高中化学 · 三年总图", size=18,
                            weight=ft.FontWeight.W_600, color="#E8EBF5"),
                    ft.Text("双指缩放、拖动查看；5 册 20 章 101 个要点", size=12, color=C_TEXT2),
                    ft.Container(
                        content=ft.InteractiveViewer(
                            content=ft.Image(src="assets/chem_map.png", fit=ft.ImageFit.CONTAIN),
                            min_scale=0.3, max_scale=8.0,
                            constrained=True, expand=True),
                        expand=True, bgcolor="#0F0F16", border_radius=12,
                        padding=4),
                ], spacing=10, expand=True)

'''
assert ANCHOR in t
t = t.replace(ANCHOR, PAGE + ANCHOR, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("化学总图已接入")
