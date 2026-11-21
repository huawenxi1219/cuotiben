# -*- coding: utf-8 -*-
"""把化学总图并进「思维导图」页（作为第三视图），取消单独卡片。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 去掉单独卡片
OLD = '''                if subject == "英语":
                    cards_config = all_cards
                elif subject == "化学":
                    cards_config = all_cards[:3] + [("🧪", "化学总图", "#22303A")]
                else:
                    cards_config = all_cards[:3]'''
NEW = '''                cards_config = all_cards if subject == "英语" else all_cards[:3]'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 知识页里加「总览」按钮（仅化学）
OLD2 = '''                _seg = ft.Row([
                    ft.ElevatedButton("🗺 图谱", icon=ft.Icons.ACCOUNT_TREE,
                                      on_click=lambda e: _switch_view(True)),
                    ft.ElevatedButton("📋 列表", icon=ft.Icons.LIST,
                                      on_click=lambda e: _switch_view(False)),
                ], spacing=8)'''
NEW2 = '''                _seg_items = [
                    ft.ElevatedButton("🗺 图谱", icon=ft.Icons.ACCOUNT_TREE,
                                      on_click=lambda e: _switch_view(True)),
                    ft.ElevatedButton("📋 列表", icon=ft.Icons.LIST,
                                      on_click=lambda e: _switch_view(False)),
                ]
                if subject == "化学":
                    _seg_items.append(ft.ElevatedButton(
                        "🧪 三年总览", icon=ft.Icons.MAP,
                        on_click=lambda e: _switch_overview()))
                _seg = ft.Row(_seg_items, spacing=8)'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# 3) 总览视图容器 + 切换函数
OLD3 = '''                _view_state = {"graph": True}'''
NEW3 = '''                _overview_box = ft.Container(expand=True, visible=False,
                                             bgcolor="#0F0F16", border_radius=12, padding=4,
                                             content=ft.InteractiveViewer(
                                                 content=ft.Image(src="assets/chem_map.png",
                                                                  fit=ft.ImageFit.CONTAIN),
                                                 min_scale=0.3, max_scale=8.0,
                                                 constrained=True, expand=True))

                def _switch_overview():
                    body.visible = False
                    _graph_box.visible = False
                    _overview_box.visible = True
                    page.update()

                _view_state = {"graph": True}'''
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

# 4) 切换回图谱/列表时要关掉总览
OLD4 = '''                def _switch_view(to_graph):
                    _view_state["graph"] = to_graph
                    body.visible = not to_graph
                    _graph_box.visible = to_graph'''
NEW4 = '''                def _switch_view(to_graph):
                    _view_state["graph"] = to_graph
                    _overview_box.visible = False
                    body.visible = not to_graph
                    _graph_box.visible = to_graph'''
assert OLD4 in t
t = t.replace(OLD4, NEW4, 1)

# 5) 页面返回里加入总览容器
OLD5 = '''                    body,
                    _graph_box,
                ], spacing=10, expand=True)'''
NEW5 = '''                    body,
                    _graph_box,
                    _overview_box,
                ], spacing=10, expand=True)'''
assert OLD5 in t
t = t.replace(OLD5, NEW5, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("总览已并入思维导图页")
