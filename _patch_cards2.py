# -*- coding: utf-8 -*-
"""导出错题卡前先弹选项：每页题数 + 是否留演算空白。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 选项状态 + 弹窗函数（插在 on_export_cards 之前）
OLD = '''            def on_export_cards_week(e):'''
NEW = '''            _card_opts = {"per_page": 6, "blank": False}

            def open_card_options(week=False):
                _pp = ft.Dropdown(
                    label="每页题数",
                    options=[ft.dropdown.Option("4", "4 题（格子最大）"),
                             ft.dropdown.Option("6", "6 题（默认）"),
                             ft.dropdown.Option("5", "5 题（折中）")],
                    value=str(_card_opts["per_page"]), width=200, dense=True)
                _bk = ft.Switch(label="留出「演算空白区」", value=_card_opts["blank"])
                _hint = ft.Text("留白适合在纸上重做；不留白适合只写批注", size=11, color=C_TEXT2)

                def _go(ev):
                    _card_opts["per_page"] = int(_pp.value or 6)
                    _card_opts["blank"] = bool(_bk.value)
                    page.close(_dlg)
                    _fn = on_export_cards_week if week else on_export_cards
                    _use_picker(page, _fn).save_file(
                        dialog_title=("导出本周错题卡" if week else "导出 A4 错题卡"),
                        file_name=("本周错题卡.html" if week else "池鱼错题卡.html"),
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=["html"])

                _dlg = ft.AlertDialog(
                    title=ft.Text("错题卡设置"),
                    content=ft.Container(content=ft.Column([_pp, _bk, _hint], spacing=12),
                                         width=_dlg_w(page, 300)),
                    actions=[ft.TextButton("取消", on_click=lambda ev: page.close(_dlg)),
                             ft.ElevatedButton("导出", icon=ft.Icons.PRINT, on_click=_go)])
                page.open(_dlg)

            def on_export_cards_week(e):'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 两个 handler 带上选项
t = t.replace("_f.write(build_error_cards_html(days=7))",
              "_f.write(build_error_cards_html(days=7, per_page=_card_opts['per_page'], blank=_card_opts['blank']))", 1)
t = t.replace("_f.write(build_error_cards_html())",
              "_f.write(build_error_cards_html(per_page=_card_opts['per_page'], blank=_card_opts['blank']))", 1)

# 3) 按钮改为先弹选项
OLD_W = '''                ft.ElevatedButton("📅 导出本周错题卡", icon=ft.Icons.DATE_RANGE,
                                  on_click=lambda e: _use_picker(page, on_export_cards_week).save_file(
                                      dialog_title="导出本周错题卡",
                                      file_name="本周错题卡.html",
                                      file_type=ft.FilePickerFileType.CUSTOM,
                                      allowed_extensions=["html"])),'''
NEW_W = '''                ft.ElevatedButton("📅 导出本周错题卡", icon=ft.Icons.DATE_RANGE,
                                  on_click=lambda e: open_card_options(True)),'''
assert OLD_W in t
t = t.replace(OLD_W, NEW_W, 1)

OLD_A = '''                ft.ElevatedButton("🖨 导出 A4 错题卡", icon=ft.Icons.PRINT,
                                  on_click=lambda e: _use_picker(page, on_export_cards).save_file(
                                      dialog_title="导出 A4 错题卡",
                                      file_name="池鱼错题卡.html",
                                      file_type=ft.FilePickerFileType.CUSTOM,
                                      allowed_extensions=["html"])),'''
NEW_A = '''                ft.ElevatedButton("🖨 导出 A4 错题卡", icon=ft.Icons.PRINT,
                                  on_click=lambda e: open_card_options(False)),'''
assert OLD_A in t
t = t.replace(OLD_A, NEW_A, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("导出选项已接入")
