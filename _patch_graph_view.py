# -*- coding: utf-8 -*-
"""知识页加入「图谱/列表」切换，图谱用 mindmap_render 生成的 PNG + InteractiveViewer。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 顶部导入渲染器（失败则降级为无图）
OLD_IMPORTS = "import flet as ft"
NEW_IMPORTS = """import flet as ft
try:
    from mindmap_render import render_mindmap as _render_mindmap
except BaseException:
    _render_mindmap = None"""
assert OLD_IMPORTS in t
t = t.replace(OLD_IMPORTS, NEW_IMPORTS, 1)

# 2) 在 build_knowledge_page 里加图谱视图
OLD_HEAD = '''                search = ft.TextField(label="搜索知识点 / 笔记内容", dense=True, expand=True)
                body = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)'''
NEW_HEAD = '''                search = ft.TextField(label="搜索知识点 / 笔记内容", dense=True, expand=True)
                body = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

                # —— 图谱视图：渲染成 PNG，可缩放拖动 ——
                _graph_box = ft.Container(expand=True, visible=False,
                                          content=ft.Container(alignment=ft.alignment.center,
                                                               content=ft.Text("生成中…", color="#8B93A7")))

                def _render_graph():
                    if _render_mindmap is None:
                        _graph_box.content = ft.Container(
                            alignment=ft.alignment.center,
                            content=ft.Text("图谱需要 Pillow，当前环境不可用", color="#F7768E"))
                        return
                    kps = []
                    for name, data in sorted(buckets.items()):
                        kps.append({
                            "name": name,
                            "notes": [(n.get("content") or "（空笔记）").strip() for n in data["note"]],
                            "errors": [(e.get("original") or e.get("question") or "（无题目）").strip()
                                       for e in data["err"]],
                        })
                    if not kps:
                        kps = [{"name": "还没有知识点", "notes": [], "errors": []}]
                    try:
                        png = _render_mindmap(subject, kps)
                        b64 = base64.b64encode(png).decode("ascii")
                        _graph_box.content = ft.InteractiveViewer(
                            content=ft.Image(src_base64=b64, fit=ft.ImageFit.CONTAIN),
                            min_scale=0.3, max_scale=6.0,
                            constrained=True, expand=True)
                    except Exception as _ex:
                        _graph_box.content = ft.Container(
                            alignment=ft.alignment.center,
                            content=ft.Text(f"图谱生成失败：{str(_ex)[:60]}", color="#F7768E"))

                _view_state = {"graph": True}

                def _switch_view(to_graph):
                    _view_state["graph"] = to_graph
                    body.visible = not to_graph
                    _graph_box.visible = to_graph
                    if to_graph:
                        _render_graph()
                    page.update()

                _seg = ft.Row([
                    ft.ElevatedButton("🗺 图谱", icon=ft.Icons.ACCOUNT_TREE,
                                      on_click=lambda e: _switch_view(True)),
                    ft.ElevatedButton("📋 列表", icon=ft.Icons.LIST,
                                      on_click=lambda e: _switch_view(False)),
                ], spacing=8)'''
assert OLD_HEAD in t
t = t.replace(OLD_HEAD, NEW_HEAD, 1)

# 3) 页面返回里加入切换与图谱容器
OLD_RET = '''                    search,
                    ft.Divider(height=1, color="#262B3D"),
                    body,
                ], spacing=10, expand=True)'''
NEW_RET = '''                    search,
                    _seg,
                    ft.Divider(height=1, color="#262B3D"),
                    body,
                    _graph_box,
                ], spacing=10, expand=True)'''
assert OLD_RET in t
t = t.replace(OLD_RET, NEW_RET, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("知识页已加图谱视图")
