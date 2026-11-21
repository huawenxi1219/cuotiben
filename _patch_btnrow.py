# -*- coding: utf-8 -*-
"""「我的」页按钮改成整行宽，右侧不再空一大块。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

OLD = '''                u_card(ft.Column([
                ft.ElevatedButton("🎯 学习画像", on_click=lambda e: show_learning_profile(e),
                                  icon=ft.Icons.PERSON_OUTLINE),'''
NEW = '''                u_card(ft.Column([
                _row_btn(ft.ElevatedButton("🎯 学习画像", on_click=lambda e: show_learning_profile(e),
                                  icon=ft.Icons.PERSON_OUTLINE)),'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

pairs = [
    ('ft.ElevatedButton("📊 知识框架", on_click=lambda e: show_knowledge_framework(e),\n                                  icon=ft.Icons.INSIGHTS),',
     '_row_btn(ft.ElevatedButton("📊 知识框架", on_click=lambda e: show_knowledge_framework(e),\n                                  icon=ft.Icons.INSIGHTS)),'),
    ('ft.ElevatedButton("📅 导出本周错题卡", icon=ft.Icons.DATE_RANGE,\n                                  on_click=lambda e: open_card_options(True)),',
     '_row_btn(ft.ElevatedButton("📅 导出本周错题卡", icon=ft.Icons.DATE_RANGE,\n                                  on_click=lambda e: open_card_options(True))),'),
    ('ft.ElevatedButton("🖨 导出 A4 错题卡", icon=ft.Icons.PRINT,\n                                  on_click=lambda e: open_card_options(False)),',
     '_row_btn(ft.ElevatedButton("🖨 导出 A4 错题卡", icon=ft.Icons.PRINT,\n                                  on_click=lambda e: open_card_options(False))),'),
    ('ft.ElevatedButton("🏷️ 批量重打标签", on_click=lambda e: batch_retag(e),\n                                  icon=ft.Icons.LABEL),',
     '_row_btn(ft.ElevatedButton("🏷️ 批量重打标签", on_click=lambda e: batch_retag(e),\n                                  icon=ft.Icons.LABEL)),'),
    ('ft.ElevatedButton("⚙️ 单词本设置", on_click=lambda e: show_vocab_settings_dialog(e),\n                                  icon=ft.Icons.SETTINGS),',
     '_row_btn(ft.ElevatedButton("⚙️ 单词本设置", on_click=lambda e: show_vocab_settings_dialog(e),\n                                  icon=ft.Icons.SETTINGS)),'),
]
for old, new in pairs:
    assert old in t, old[:30]
    t = t.replace(old, new, 1)

# 定义 _row_btn（放在 u_card 之后定义处附近，这里插在 mode_switch_row 之前）
ANCHOR = "            mode_switch_row = ft.Row(["
HELPER = '''            def _row_btn(btn):
                """把按钮包成整行宽（Flet 里按钮本身不随列拉伸）"""
                btn.expand = True
                return ft.Row([btn], spacing=0)

'''
assert ANCHOR in t
t = t.replace(ANCHOR, HELPER + ANCHOR, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("按钮整行化完成")
