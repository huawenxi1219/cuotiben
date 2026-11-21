# -*- coding: utf-8 -*-
"""错题录入增强（按真实使用场景）：
1. 状态：未解决 / 已解决 / 待查
2. 掌握程度：能独立写 / 需提示 / 不会
3. 手写过程照片（自己写的过程）
4. 数学符号快捷栏（打不出特殊符号时点一下）
5. 学科页去掉「金句」入口
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) save_error 支持新字段 ----------
OLD_SIG = '''def save_error(subject, original="", original_media=None, answer="", answer_media=None,
               mistake="", idea="", idea_media=None, manual_tags=""):'''
NEW_SIG = '''def save_error(subject, original="", original_media=None, answer="", answer_media=None,
               mistake="", idea="", idea_media=None, manual_tags="",
               status="未解决", mastery="", solution_media=None):'''
assert OLD_SIG in t
t = t.replace(OLD_SIG, NEW_SIG, 1)

OLD_ENTRY = '''        "deep_analysis": "", "status": "未看",'''
NEW_ENTRY = '''        "deep_analysis": "", "status": status or "未解决",
        "mastery": mastery or "", "solution_media": solution_media or [],'''
assert OLD_ENTRY in t
t = t.replace(OLD_ENTRY, NEW_ENTRY, 1)

# ---------- 2) 表单控件 ----------
OLD_FLD = '''            tags_input = ft.TextField(label="手动标签（逗号分隔）", multiline=False,
                                      border_radius=14, filled=True, fill_color="#1F1F26",
                                      border_color="#414868", focused_border_color="#7AA2F7")'''
NEW_FLD = OLD_FLD + '''
            status_dd = ft.Dropdown(
                label="这道题现在什么状态",
                options=[ft.dropdown.Option("未解决"), ft.dropdown.Option("待查"),
                         ft.dropdown.Option("已解决")],
                value="未解决", width=190, dense=True)
            mastery_dd = ft.Dropdown(
                label="掌握程度",
                options=[ft.dropdown.Option("不会"), ft.dropdown.Option("需提示"),
                         ft.dropdown.Option("能独立写")],
                value="需提示", width=170, dense=True)

            _sym_target = {"f": None}
            SYMBOLS = ["²", "³", "⁻", "⁺", "₁", "₂", "₃", "√", "≤", "≥", "≠", "≈",
                       "∵", "∴", "α", "β", "θ", "π", "Δ", "Σ", "∫", "→", "⇌", "↑",
                       "↓", "±", "×", "÷", "∞", "∠", "⊥", "∥", "°"]

            def _sym_insert(ch):
                f = _sym_target["f"]
                if f is None:
                    show_toast("先点一下要输入的位置", "orange")
                    return
                f.value = (f.value or "") + ch
                page.update()

            def _mk_sym_bar():
                return ft.Container(
                    content=ft.Row(
                        [ft.TextButton(s, on_click=lambda e, c=s: _sym_insert(c),
                                       style=ft.ButtonStyle(padding=ft.Padding(4, 2, 4, 2)))
                         for s in SYMBOLS],
                        scroll=ft.ScrollMode.AUTO, spacing=0),
                    bgcolor="#171A24", border_radius=10, padding=2)'''
assert OLD_FLD in t
t = t.replace(OLD_FLD, NEW_FLD, 1)

# 记录最后聚焦的输入框
OLD_FOCUS = '''            def on_picker_complete(selected_files):'''
NEW_FOCUS = '''            for _f in (original_input, mistake_input, answer_input, idea_input):
                _f.on_focus = (lambda e, f=_f: _sym_target.update({"f": f}))

            def on_picker_complete(selected_files):'''
assert OLD_FOCUS in t
t = t.replace(OLD_FOCUS, NEW_FOCUS, 1)

# 4 号图片选择器：手写过程
OLD_PICK = '''            picker_col3, idea_files, reset_picker3 = make_file_picker_button(
                "📷 笔记图片（错题补充）", "image", on_complete=None)'''
NEW_PICK = OLD_PICK + '''
            picker_col4, solution_files, reset_picker4 = make_file_picker_button(
                "✍️ 我自己的解题过程（拍照）", "image", on_complete=None)'''
assert OLD_PICK in t
t = t.replace(OLD_PICK, NEW_PICK, 1)

# ---------- 3) 布局：状态 + 符号栏 + 手写图片 ----------
OLD_LAYOUT = '''                u_card(ft.Column([
                    ft.Row([subj_dd], spacing=15) if not is_mobile else ft.Column([subj_dd]),
                    original_input,
                    mistake_input,
                ], spacing=12)),'''
NEW_LAYOUT = '''                u_card(ft.Column([
                    ft.Row([subj_dd, status_dd, mastery_dd], spacing=12, wrap=True)
                    if not is_mobile else ft.Column([subj_dd, status_dd, mastery_dd], spacing=8),
                    original_input,
                    _mk_sym_bar(),
                    mistake_input,
                ], spacing=12)),'''
assert OLD_LAYOUT in t
t = t.replace(OLD_LAYOUT, NEW_LAYOUT, 1)

OLD_LAYOUT2 = '''                u_card(ft.Column([
                    picker_col1,
                    picker_col2,
                    picker_col3,
                    progress_row,
                ], spacing=10)),'''
NEW_LAYOUT2 = '''                u_card(ft.Column([
                    picker_col1,
                    picker_col2,
                    picker_col3,
                    picker_col4,
                    progress_row,
                ], spacing=10)),'''
assert OLD_LAYOUT2 in t
t = t.replace(OLD_LAYOUT2, NEW_LAYOUT2, 1)

# ---------- 4) 提交 ----------
OLD_SUB = '''                save_error(subj, orig, list(original_files), ans, list(answer_files), mis, idea, list(idea_files), tags)'''
NEW_SUB = '''                save_error(subj, orig, list(original_files), ans, list(answer_files), mis, idea,
                           list(idea_files), tags,
                           status=(status_dd.value or "未解决"),
                           mastery=(mastery_dd.value or ""),
                           solution_media=list(solution_files))'''
assert OLD_SUB in t
t = t.replace(OLD_SUB, NEW_SUB, 1)

OLD_RESET = '''                reset_picker3(keep=True)'''
NEW_RESET = '''                reset_picker3(keep=True)
                reset_picker4(keep=True)'''
assert OLD_RESET in t
t = t.replace(OLD_RESET, NEW_RESET, 1)

# ---------- 5) 学科页去掉金句 ----------
OLD_CARDS = '''                    ("📖", "单词本", "#3A2F22"),
                    ("💬", "金句", "#3A2233"),'''
NEW_CARDS = '''                    ("📖", "单词本", "#3A2F22"),'''
assert OLD_CARDS in t
t = t.replace(OLD_CARDS, NEW_CARDS, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("错题录入增强完成")
