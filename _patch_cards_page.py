# -*- coding: utf-8 -*-
"""App 内 A4 错题卡排版页：预览 + 翻页 + 导出 PDF/PNG。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 导入渲染模块
OLD_IMP = '''try:
    from mindmap_render import render_mindmap as _render_mindmap
except BaseException:
    _render_mindmap = None'''
NEW_IMP = '''try:
    from mindmap_render import render_mindmap as _render_mindmap
except BaseException:
    _render_mindmap = None
try:
    from a4_render import render_error_pages as _render_error_pages, pages_to_pdf as _pages_to_pdf
except BaseException:
    _render_error_pages = None
    _pages_to_pdf = None'''
assert OLD_IMP in t
t = t.replace(OLD_IMP, NEW_IMP, 1)

# 2) 页面构造器（插在 build_knowledge_page 之前）
ANCHOR = "            def build_knowledge_page(subject):"
PAGE = '''            def build_cards_page():
                """在 App 里直接排好 A4 错题卡，预览后导出 PDF/PNG 给打印机。"""
                import base64 as _b64

                st = {"per": 6, "blank": False, "days": "", "pages": [], "idx": 0}

                _head = ft.Text("🖨 错题卡排版", size=20, weight=ft.FontWeight.W_700, color="#E8EBF5")
                _info = ft.Text("", size=12, color=C_TEXT2)
                _prev = ft.Container(expand=True, bgcolor="#FFFFFF", border_radius=8,
                                     alignment=ft.alignment.center,
                                     content=ft.Text("正在排版…", color="#666"))
                _pp = ft.Dropdown(label="每页题数", width=150, dense=True,
                                  options=[ft.dropdown.Option("1", "1 题"),
                                           ft.dropdown.Option("4", "4 题"),
                                           ft.dropdown.Option("6", "6 题")],
                                  value="6")
                _dr = ft.Dropdown(label="范围", width=150, dense=True,
                                  options=[ft.dropdown.Option("", "全部"),
                                           ft.dropdown.Option("7", "最近7天"),
                                           ft.dropdown.Option("30", "最近30天")],
                                  value="")
                _bk = ft.Switch(label="演算留白", value=False)
                _busy = {"v": False}

                def _collect():
                    errs = load_jsonl(ERRORS_FILE)
                    d = str(_dr.value or "").strip()
                    if d.isdigit():
                        cutoff = time.time() * 1000 - int(d) * 86400000
                        errs = [e for e in errs if (e.get("timestamp") or 0) >= cutoff]
                    errs = sorted(errs, key=lambda e: e.get("timestamp") or 0, reverse=True)
                    return errs

                def _refresh(keep_idx=False):
                    if _render_error_pages is None:
                        _prev.content = ft.Text("缺少 Pillow，无法排版", color="#C33")
                        page.update()
                        return
                    errs = _collect()
                    st["pages"] = _render_error_pages(errs, per_page=int(_pp.value or 6),
                                                      blank=bool(_bk.value))
                    if not keep_idx:
                        st["idx"] = 0
                    st["idx"] = max(0, min(st["idx"], len(st["pages"]) - 1))
                    _show()

                def _show():
                    if not st["pages"]:
                        return
                    im = st["pages"][st["idx"]]
                    im2 = im.resize((im.width // 3, im.height // 3))
                    buf = io.BytesIO()
                    im2.save(buf, format="PNG", optimize=True)
                    _prev.content = ft.Image(src_base64=_b64.b64encode(buf.getvalue()).decode("ascii"),
                                             fit=ft.ImageFit.CONTAIN)
                    _info.value = f"第 {st['idx'] + 1} / {len(st['pages'])} 页 · {im.width}×{im.height}px（A4 300dpi）"
                    page.update()

                def _regen(e=None):
                    if _busy["v"]:
                        return
                    _busy["v"] = True
                    _prev.content = ft.Text("正在排版…", color="#666")
                    page.update()

                    def _job():
                        try:
                            _refresh()
                        except Exception as ex:
                            _prev.content = ft.Text(f"排版失败：{str(ex)[:60]}", color="#C33")
                            page.update()
                        finally:
                            _busy["v"] = False

                    threading.Thread(target=_job, daemon=True).start()

                def _nav(delta):
                    if not st["pages"]:
                        return
                    st["idx"] = max(0, min(st["idx"] + delta, len(st["pages"]) - 1))
                    _show()

                def _save_pdf(e):
                    if not getattr(e, "path", ""):
                        return
                    try:
                        p = e.path if str(e.path).lower().endswith(".pdf") else str(e.path) + ".pdf"
                        with open(p, "wb") as f:
                            f.write(_pages_to_pdf(st["pages"]))
                        show_toast(f"✅ 已导出 PDF：{os.path.basename(p)}", "green")
                    except Exception as ex:
                        show_toast(f"导出失败：{str(ex)[:50]}", "red")

                def _save_png(e):
                    if not getattr(e, "path", "") or not st["pages"]:
                        return
                    try:
                        p = e.path if str(e.path).lower().endswith(".png") else str(e.path) + ".png"
                        st["pages"][st["idx"]].save(p)
                        show_toast(f"✅ 已导出第 {st['idx'] + 1} 页", "green")
                    except Exception as ex:
                        show_toast(f"导出失败：{str(ex)[:50]}", "red")

                for w in (_pp, _dr):
                    w.on_change = _regen
                _bk.on_change = _regen

                return ft.Column([
                    _head,
                    ft.Text("排好后导出 PDF，直接发给打印机 App 即可", size=12, color=C_TEXT2),
                    ft.Row([_pp, _dr, _bk], spacing=10, wrap=True),
                    _info,
                    ft.Row([
                        ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda e: _nav(-1)),
                        ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: _nav(1)),
                        ft.ElevatedButton("📄 导出 PDF", icon=ft.Icons.PICTURE_AS_PDF,
                                          on_click=lambda e: _use_picker(page, _save_pdf).save_file(
                                              dialog_title="保存错题卡", file_name="池鱼错题卡.pdf",
                                              file_type=ft.FilePickerFileType.CUSTOM,
                                              allowed_extensions=["pdf"])),
                        ft.ElevatedButton("🖼 导出本页 PNG", icon=ft.Icons.IMAGE,
                                          on_click=lambda e: _use_picker(page, _save_png).save_file(
                                              dialog_title="保存图片", file_name="错题卡.png",
                                              file_type=ft.FilePickerFileType.CUSTOM,
                                              allowed_extensions=["png"])),
                    ], spacing=8, wrap=True),
                    ft.Container(content=_prev, expand=True, bgcolor="#FFFFFF", border_radius=8),
                ], spacing=10, expand=True)

'''
assert ANCHOR in t
t = t.replace(ANCHOR, PAGE + ANCHOR, 1)

# 3) 我的页按钮：换成进入排版页
OLD_BTN = '''                _row_btn(ft.ElevatedButton("🖨 导出 A4 错题卡", icon=ft.Icons.PRINT,
                                  on_click=lambda e: open_card_options(False))),'''
NEW_BTN = '''                _row_btn(ft.ElevatedButton("🖨 错题卡排版 / 导出", icon=ft.Icons.PRINT,
                                  on_click=lambda e: open_function_page(None, "错题卡排版"))),'''
assert OLD_BTN in t
t = t.replace(OLD_BTN, NEW_BTN, 1)

# 4) 注册页面
OLD_REG = '''                    "化学总图": lambda: _build_chem_map_page(),'''
NEW_REG = '''                    "化学总图": lambda: _build_chem_map_page(),
                    "错题卡排版": lambda: build_cards_page(),'''
assert OLD_REG in t
t = t.replace(OLD_REG, NEW_REG, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("错题卡排版页已接入")
