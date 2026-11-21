# -*- coding: utf-8 -*-
"""① 移除坚果云 WebDAV 界面（用户不需要）② 知识页加「📖 背诵版」阅读视图。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- ① 去掉 WebDAV 卡片 ----------
OLD_DAV = '''                ft.Divider(),
                ft.Text("☁️ 坚果云同步（WebDAV）", size=16, weight=ft.FontWeight.W_600),
                ft.Text("坚果云「账户信息 → 安全选项 → 添加应用」生成应用密码，别用登录密码",
                        size=11, color=C_TEXT2),
                dav_url_input, dav_user_input, dav_pass_input,
                ft.Row([
                    ft.ElevatedButton("☁️ 上传到网盘", icon=ft.Icons.CLOUD_UPLOAD,
                                      on_click=lambda e: dav_do_upload(e)),
                    ft.ElevatedButton("⬇️ 从网盘拉取", icon=ft.Icons.CLOUD_DOWNLOAD,
                                      on_click=lambda e: dav_do_download(e)),
                ], spacing=10, wrap=True),
                dav_status,
'''
assert OLD_DAV in t, "WebDAV 卡片未匹配"
t = t.replace(OLD_DAV, "", 1)

# ---------- ② 背诵版视图 ----------
OLD_SEG = '''                    _seg_items.append(ft.ElevatedButton(
                        "🧪 三年总览", icon=ft.Icons.MAP,
                        on_click=lambda e: _switch_overview()))'''
NEW_SEG = '''                    _seg_items.append(ft.ElevatedButton(
                        "📖 背诵版", icon=ft.Icons.MENU_BOOK,
                        on_click=lambda e: _switch_recite()))
                    _seg_items.append(ft.ElevatedButton(
                        "🧪 三年总览", icon=ft.Icons.MAP,
                        on_click=lambda e: _switch_overview()))'''
assert OLD_SEG in t
t = t.replace(OLD_SEG, NEW_SEG, 1)

OLD_NAV = '''                def _switch_nav():'''
NEW_NAV = '''                _recite_box = ft.Container(expand=True, visible=False)

                def _render_recite():
                    tree = load_chem_tree()
                    if not tree:
                        _recite_box.content = ft.Container(
                            alignment=ft.alignment.center,
                            content=ft.Text("还没有知识图", color="#8B93A7"))
                        return
                    blocks = []
                    for book in tree.get("books", []):
                        blocks.append(ft.Text(book.get("name", ""), size=17,
                                              weight=ft.FontWeight.BOLD, color="#7AA2F7"))
                        for chap in book.get("chapters", []):
                            blocks.append(ft.Text(chap.get("name", ""), size=14,
                                                  weight=ft.FontWeight.W_600, color="#E8EBF5"))
                            for sec in chap.get("sections", []):
                                blocks.append(ft.Container(
                                    content=ft.Text(sec.get("section", ""), size=13,
                                                    color="#4DB6AC", weight=ft.FontWeight.W_600),
                                    padding=ft.Padding(left=2, right=0, top=6, bottom=2)))
                                for pt in sec.get("points", []):
                                    row = [ft.Text(f"{pt.get('id','')}  {pt.get('title','')}",
                                                   size=13, weight=ft.FontWeight.BOLD, color="#F0F2FA")]
                                    if pt.get("detail"):
                                        row.append(ft.Text(pt["detail"], size=12.5,
                                                         color="#C9CFE0", selectable=True))
                                    for fa in (pt.get("facts") or []):
                                        row.append(ft.Text("· " + str(fa), size=12, color="#A8B0C4"))
                                    for pf in (pt.get("pitfalls") or []):
                                        row.append(ft.Text("⚠ " + str(pf), size=12, color="#F7768E"))
                                    blocks.append(ft.Container(
                                        content=ft.Column(row, spacing=2),
                                        padding=ft.Padding(left=10, right=10, top=8, bottom=8),
                                        border_radius=8, bgcolor="#1A1E2B",
                                        margin=ft.margin.only(bottom=6)))
                                if sec.get("equations"):
                                    blocks.append(ft.Container(
                                        content=ft.Column([
                                            ft.Text("　" + e.get("eq", ""), size=12,
                                                    color="#9DBBF8", selectable=True)
                                            for e in sec["equations"]]),
                                        padding=ft.Padding(left=10, right=10, top=4, bottom=8),
                                        bgcolor="#141926", border_radius=6))
                    _recite_box.content = ft.Column(blocks, spacing=4,
                                                    scroll=ft.ScrollMode.AUTO, expand=True)

                def _switch_recite():
                    body.visible = False
                    _graph_box.visible = False
                    _overview_box.visible = False
                    _nav_box.visible = False
                    _recite_box.visible = True
                    _render_recite()
                    page.update()

                def _switch_nav():'''
assert OLD_NAV in t
t = t.replace(OLD_NAV, NEW_NAV, 1)

# 其它切换里关掉背诵版
for old, new in [
    ('''                    _overview_box.visible = False
                    _nav_box.visible = False
                    body.visible = not to_graph''',
     '''                    _overview_box.visible = False
                    _nav_box.visible = False
                    _recite_box.visible = False
                    body.visible = not to_graph'''),
    ('''                    _nav_box.visible = False
                    _overview_box.visible = True''',
     '''                    _nav_box.visible = False
                    _recite_box.visible = False
                    _overview_box.visible = True'''),
    ('''                    _overview_box.visible = False
                    _nav_box.visible = True''',
     '''                    _overview_box.visible = False
                    _recite_box.visible = False
                    _nav_box.visible = True'''),
]:
    assert old in t, old[:40]
    t = t.replace(old, new, 1)

# 挂到页面
OLD_RET = '''                    _nav_box,
                    _overview_box,
                ], spacing=10, expand=True)'''
NEW_RET = '''                    _nav_box,
                    _recite_box,
                    _overview_box,
                ], spacing=10, expand=True)'''
assert OLD_RET in t
t = t.replace(OLD_RET, NEW_RET, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("WebDAV 已移除；背诵版视图已加入")
