# -*- coding: utf-8 -*-
"""本轮修复：
1. 所有图片选择改为「图库」选择器（file_type=IMAGE），不再跳文件管理器
2. 我的页删除「今日学习计划」卡片
3. 删除「知识框架」入口（保留学习画像）
4. 「本周错题卡」与「A4 错题卡」合并：导出对话框里选时间范围
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 图片选择器 ----------
pairs = [
    ('''                def pick_files(e):
                    _use_picker(page, handle_picker_result).pick_files(
                        allow_multiple=True)''',
     '''                def pick_files(e):
                    _use_picker(page, handle_picker_result).pick_files(
                        allow_multiple=True,
                        file_type=ft.FilePickerFileType.IMAGE)'''),
    ('''                    # Android 上带 IMAGE 过滤的多选有时直接静默失败，改用 ANY 多选更稳
                    _use_picker(page, _on_files).pick_files(allow_multiple=True)''',
     '''                    _use_picker(page, _on_files).pick_files(
                        allow_multiple=True, file_type=ft.FilePickerFileType.IMAGE)'''),
    ('''                def pick_chat_image():
                    _use_picker(page, on_chat_img_picked).pick_files(
                        allow_multiple=True)''',
     '''                def pick_chat_image():
                    _use_picker(page, on_chat_img_picked).pick_files(
                        allow_multiple=True, file_type=ft.FilePickerFileType.IMAGE)'''),
]
for old, new in pairs:
    assert old in t, old[:50]
    t = t.replace(old, new, 1)

# ---------- 2) 删除今日学习计划卡片 ----------
OLD_PLAN = '''                ft.Text("我的", size=28, weight=ft.FontWeight.W_700, color=C_TEXT),
                today_plan_card,'''
NEW_PLAN = '''                ft.Text("我的", size=28, weight=ft.FontWeight.W_700, color=C_TEXT),'''
assert OLD_PLAN in t
t = t.replace(OLD_PLAN, NEW_PLAN, 1)

# ---------- 3) 删除知识框架入口 ----------
OLD_KF = '''                _row_btn(ft.ElevatedButton("📊 知识框架", on_click=lambda e: show_knowledge_framework(e),
                                  icon=ft.Icons.INSIGHTS)),
'''
assert OLD_KF in t
t = t.replace(OLD_KF, "", 1)

OLD_KF2 = '''                    ("知识框架", lambda: show_knowledge_framework(None)),
'''
t = t.replace(OLD_KF2, "", 1)

# ---------- 4) 合并本周错题卡 ----------
OLD_BTN = '''                _row_btn(ft.ElevatedButton("📅 导出本周错题卡", icon=ft.Icons.DATE_RANGE,
                                  on_click=lambda e: open_card_options(True))),
'''
assert OLD_BTN in t
t = t.replace(OLD_BTN, "", 1)

OLD_OPTS = '''            _card_opts = {"per_page": 6, "blank": False}

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
                                         width=_dlg_w(page, 300)),'''
NEW_OPTS = '''            _card_opts = {"per_page": 6, "blank": False, "days": ""}

            def open_card_options(week=False):
                _pp = ft.Dropdown(
                    label="每页题数",
                    options=[ft.dropdown.Option("4", "4 题（格子最大）"),
                             ft.dropdown.Option("6", "6 题（默认）"),
                             ft.dropdown.Option("5", "5 题（折中）")],
                    value=str(_card_opts["per_page"]), width=200, dense=True)
                _dr = ft.Dropdown(
                    label="时间范围",
                    options=[ft.dropdown.Option("", "全部错题"),
                             ft.dropdown.Option("7", "最近 7 天"),
                             ft.dropdown.Option("30", "最近 30 天")],
                    value=str(_card_opts.get("days") or ""), width=200, dense=True)
                _bk = ft.Switch(label="留出「演算空白区」", value=_card_opts["blank"])
                _hint = ft.Text("留白适合在纸上重做；不留白适合只写批注", size=11, color=C_TEXT2)

                def _go(ev):
                    _card_opts["per_page"] = int(_pp.value or 6)
                    _card_opts["blank"] = bool(_bk.value)
                    _card_opts["days"] = _dr.value or ""
                    page.close(_dlg)
                    _use_picker(page, on_export_cards).save_file(
                        dialog_title="导出 A4 错题卡",
                        file_name="池鱼错题卡.html",
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=["html"])

                _dlg = ft.AlertDialog(
                    title=ft.Text("错题卡设置"),
                    content=ft.Container(content=ft.Column([_pp, _dr, _bk, _hint], spacing=12),
                                         width=_dlg_w(page, 300)),'''
assert OLD_OPTS in t
t = t.replace(OLD_OPTS, NEW_OPTS, 1)

# 导出时带上天数
OLD_EXP = '''                        _f.write(build_error_cards_html(per_page=_card_opts['per_page'], blank=_card_opts['blank']))'''
NEW_EXP = '''                        _d = str(_card_opts.get("days") or "").strip()
                        _f.write(build_error_cards_html(
                            per_page=_card_opts['per_page'], blank=_card_opts['blank'],
                            days=int(_d) if _d.isdigit() else None))'''
assert OLD_EXP in t
t = t.replace(OLD_EXP, NEW_EXP, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("本轮修复完成")
