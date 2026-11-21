# -*- coding: utf-8 -*-
"""教材导航：支持「全部展开 / 全部收起」，并显示子级知识点。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 收集所有 ExpansionTile，供一键展开
OLD = '''                def _build_nav_column(tree):
                    cols = []'''
NEW = '''                _nav_tiles = []

                def _toggle_all(expand):
                    for _t in _nav_tiles:
                        try:
                            _t.expanded = bool(expand)
                        except BaseException:
                            pass
                    page.update()

                def _build_nav_column(tree):
                    _nav_tiles.clear()
                    cols = []'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 每个 ExpansionTile 建好后登记
t = t.replace('''                            sec_tiles.append(ft.ExpansionTile(''',
              '''                            _t1 = ft.ExpansionTile(''', 1)
t = t.replace('''                                    tile_padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                                    controls_padding=ft.Padding(left=4, right=4, top=0, bottom=4)))''',
              '''                                    tile_padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                                    controls_padding=ft.Padding(left=4, right=4, top=0, bottom=4))
                            _nav_tiles.append(_t1)
                            sec_tiles.append(_t1)''', 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("导航一键展开骨架已加")
