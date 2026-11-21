# -*- coding: utf-8 -*-
"""化学「教材导航」：读 chem_tree.json，册→章→节→知识点，可展开；支持导入新图。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 数据加载函数（模块级） ----------
ANCHOR = "def build_error_cards_html("
LOADER = '''CHEM_TREE_FILE = os.path.join(DATA_DIR, "chem_tree.json")


def load_chem_tree():
    """优先读数据目录里导入的版本，其次读打包内置的版本。"""
    for p in (CHEM_TREE_FILE, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "assets", "chem_tree.json")):
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
        except BaseException as _be:
            _diag_log(_be, "chem_tree")
    return None


'''
assert ANCHOR in t
if "def load_chem_tree" not in t:
    t = t.replace(ANCHOR, LOADER + ANCHOR, 1)

# ---------- 2) 知识页加「教材导航」视图 ----------
OLD_SEG = '''                if subject == "化学":
                    _seg_items.append(ft.ElevatedButton(
                        "🧪 三年总览", icon=ft.Icons.MAP,
                        on_click=lambda e: _switch_overview()))'''
NEW_SEG = '''                if subject == "化学":
                    _seg_items.append(ft.ElevatedButton(
                        "📚 教材导航", icon=ft.Icons.MENU_BOOK,
                        on_click=lambda e: _switch_nav()))
                    _seg_items.append(ft.ElevatedButton(
                        "🧪 三年总览", icon=ft.Icons.MAP,
                        on_click=lambda e: _switch_overview()))'''
assert OLD_SEG in t
t = t.replace(OLD_SEG, NEW_SEG, 1)

# ---------- 3) 导航视图构建 ----------
OLD_OV = '''                _overview_box = ft.Container(expand=True, visible=False,'''
NEW_OV = '''                _nav_box = ft.Container(expand=True, visible=False)

                def _render_nav():
                    tree = load_chem_tree()
                    if not tree:
                        _nav_box.content = ft.Container(
                            alignment=ft.alignment.center,
                            content=ft.Text("还没有知识图，点右上角「导入」", color="#8B93A7"))
                        return
                    _nav_box.content = _build_nav_column(tree)

                def _build_nav_column(tree):
                    cols = []
                    for book in tree.get("books", []):
                        book_tiles = []
                        for chap in book.get("chapters", []):
                            sec_tiles = []
                            for sec in chap.get("sections", []):
                                pt_col = []
                                for pt in sec.get("points", []):
                                    bg = "#221E1A"
                                    lines = [
                                        ft.Text(f"{pt.get('id','')}  {pt.get('title','')}",
                                                size=13, weight=ft.FontWeight.W_600, color="#E8EBF5"),
                                        ft.Text(pt.get("detail", ""), size=12, color="#B9C0D4",
                                                selectable=True),
                                    ]
                                    for fact in pt.get("facts", []) or []:
                                        lines.append(ft.Text("· " + str(fact), size=12, color="#9AA3B8"))
                                    for pf in pt.get("pitfalls", []) or []:
                                        lines.append(ft.Text("⚠ " + str(pf), size=12, color="#F7768E"))
                                    pt_col.append(ft.Container(
                                        content=ft.Column(lines, spacing=3),
                                        padding=8, border_radius=8, bgcolor=bg,
                                        margin=ft.margin.only(bottom=6)))
                                if sec.get("equations"):
                                    eq_txt = "　".join(e.get("eq", "") for e in sec["equations"])
                                    pt_col.append(ft.Text("方程式：" + eq_txt, size=11,
                                                          color="#7AA2F7", selectable=True))
                                sec_tiles.append(ft.ExpansionTile(
                                    title=ft.Text(f"{sec.get('section','')}", size=13, color="#D7DBEA"),
                                    controls=[ft.Container(ft.Column(pt_col, spacing=4), padding=ft.Padding(left=8, right=8, top=0, bottom=6))],
                                    tile_padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                                    controls_padding=ft.Padding(left=4, right=4, top=0, bottom=4)))
                            if sec_tiles:
                                book_tiles.append(ft.ExpansionTile(
                                    title=ft.Text(chap.get("name", ""), size=14,
                                                  weight=ft.FontWeight.W_600, color="#C9CFE0"),
                                    controls=sec_tiles,
                                    tile_padding=ft.Padding(left=10, right=10, top=6, bottom=6)))
                        if book_tiles:
                            cols.append(ft.ExpansionTile(
                                title=ft.Text(book.get("name", ""), size=15,
                                              weight=ft.FontWeight.BOLD, color="#E8EBF5"),
                                controls=book_tiles,
                                tile_padding=ft.Padding(left=10, right=10, top=8, bottom=8)))
                    if not cols:
                        return ft.Column([ft.Text("知识图为空", color="#8B93A7")])
                    return ft.Column(cols, spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

                def _switch_nav():
                    body.visible = False
                    _graph_box.visible = False
                    _overview_box.visible = False
                    _nav_box.visible = True
                    _render_nav()
                    page.update()

                _overview_box = ft.Container(expand=True, visible=False,'''
assert OLD_OV in t
t = t.replace(OLD_OV, NEW_OV, 1)

# 切回其它视图时关掉导航
OLD_SW = '''                def _switch_view(to_graph):
                    _view_state["graph"] = to_graph
                    _overview_box.visible = False'''
NEW_SW = '''                def _switch_view(to_graph):
                    _view_state["graph"] = to_graph
                    _overview_box.visible = False
                    _nav_box.visible = False'''
assert OLD_SW in t
t = t.replace(OLD_SW, NEW_SW, 1)

OLD_OV2 = '''                def _switch_overview():
                    body.visible = False
                    _graph_box.visible = False
                    _overview_box.visible = True'''
NEW_OV2 = '''                def _switch_overview():
                    body.visible = False
                    _graph_box.visible = False
                    _nav_box.visible = False
                    _overview_box.visible = True'''
assert OLD_OV2 in t
t = t.replace(OLD_OV2, NEW_OV2, 1)

# 页面里挂上导航容器
OLD_RET = '''                    body,
                    _graph_box,
                    _overview_box,
                ], spacing=10, expand=True)'''
NEW_RET = '''                    body,
                    _graph_box,
                    _nav_box,
                    _overview_box,
                ], spacing=10, expand=True)'''
assert OLD_RET in t
t = t.replace(OLD_RET, NEW_RET, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("教材导航视图已加入")
