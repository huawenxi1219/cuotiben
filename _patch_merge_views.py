# -*- coding: utf-8 -*-
"""合并「三年总览(PNG)」与「教材导航」：只保留一张可展开的导图。

- 去掉 PNG 总览按钮
- 导图上给每章标「错 N / 记 M」（按关键词匹配你的错题和笔记）
- 保留「导出总图」按钮，把 PNG 存到手机（分享/打印用）
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 去掉「三年总览」按钮
OLD = '''                    _seg_items.append(ft.ElevatedButton(
                        "🧪 三年总览", icon=ft.Icons.MAP,
                        on_click=lambda e: _switch_overview()))
'''
assert OLD in t
t = t.replace(OLD, "", 1)

# 2) 页面里去掉总览容器
OLD2 = '''                    _nav_box,
                    _recite_box,
                    _overview_box,
                ], spacing=10, expand=True)'''
NEW2 = '''                    _nav_box,
                    _recite_box,
                ], spacing=10, expand=True)'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# 3) 章节标题加「错 N / 记 M」
OLD3 = '''                            if sec_tiles:
                                book_tiles.append(ft.ExpansionTile(
                                    title=ft.Text(chap.get("name", ""), size=14,
                                                  weight=ft.FontWeight.W_600, color="#C9CFE0"),'''
NEW3 = '''                            if sec_tiles:
                                _kw = [chap.get("name", "")] + [s.get("section", "") for s in chap["sections"]]
                                _kws = []
                                for _k in _kw:
                                    for _p in str(_k).replace("（", " ").replace("）", " ").split():
                                        if len(_p) >= 2:
                                            _kws.append(_p)

                                def _hit(rec):
                                    blob = " ".join(str(rec.get(x, "")) for x in
                                                    ("original", "mistake", "idea", "answer", "content"))
                                    blob += " " + " ".join(str(x) for x in (rec.get("tags") or []))
                                    return any(k in blob for k in _kws if len(k) >= 3)

                                _ne = sum(1 for e2 in errs if _hit(e2))
                                _nn = sum(1 for n2 in notes if _hit(n2))
                                _badge = (f"   📕{_ne}" if _ne else "") + (f"  📓{_nn}" if _nn else "")
                                book_tiles.append(ft.ExpansionTile(
                                    title=ft.Text(chap.get("name", "") + _badge, size=14,
                                                  weight=ft.FontWeight.W_600, color="#C9CFE0"),'''
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

# 4) 加「导出总图」按钮（保存 PNG）
OLD4 = '''                _expand_row = ft.Row(['''
NEW4 = '''                def _save_map(e):
                    try:
                        if not getattr(e, "path", ""):
                            return
                        _src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "assets", "chem_map.png")
                        p2 = e.path if str(e.path).lower().endswith(".png") else str(e.path) + ".png"
                        shutil.copyfile(_src, p2)
                        show_toast("✅ 总图已保存，可分享或打印", "green")
                    except Exception as ex:
                        show_toast(f"保存失败：{str(ex)[:40]}", "red")

                _expand_row = ft.Row([
                    ft.ElevatedButton("🖼 导出总图", icon=ft.Icons.IMAGE,
                                      on_click=lambda e: _use_picker(page, _save_map).save_file(
                                          dialog_title="保存化学总图", file_name="化学总图.png",
                                          file_type=ft.FilePickerFileType.CUSTOM,
                                          allowed_extensions=["png"])),'''
assert OLD4 in t
t = t.replace(OLD4, NEW4, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("已合并为单张导图")
