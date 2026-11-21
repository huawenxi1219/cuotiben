# -*- coding: utf-8 -*-
"""按你的要求清理：
1. 删除学科页「单词本」卡片（手表上已有）
2. 删除「学习画像」入口（功能并进思维导图）
3. 删除手环同步的界面代码块（本来就未挂载，纯死代码）
4. 错题本新增「结合我的错题问 AI」——只有这里能把错题喂给 AI
"""
import io
import re

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 单词本卡片 ----------
OLD = '''                    ("📖", "单词本", "#3A2F22"),
'''
assert OLD in t
t = t.replace(OLD, "", 1)
t = t.replace('                cards_config = all_cards if subject == "英语" else all_cards[:3]',
              '                cards_config = all_cards[:3]', 1)

# ---------- 2) 学习画像按钮 ----------
OLD2 = '''                _row_btn(ft.ElevatedButton("🎯 学习画像", on_click=lambda e: show_learning_profile(e),
                                  icon=ft.Icons.PERSON_OUTLINE)),
'''
assert OLD2 in t
t = t.replace(OLD2, "", 1)

# ---------- 3) 手环 UI 代码块 ----------
start = t.find("            # ---------- 手环背单词 操控中心 ----------")
if start > 0:
    # 找到该块结束：下一个同缩进的注释块或函数定义
    nxt = t.find("\n            # ----------", start + 10)
    if nxt < 0:
        nxt = t.find("\n            def ", start + 10)
    assert nxt > start
    t = t[:start] + t[nxt:]

# ---------- 4) 错题本：结合错题问 AI ----------
OLD4 = '''                search_input = ft.TextField(
                    label="🔍 搜索错题",'''
NEW4 = '''                def _ask_with_errors(e=None):
                    """把最近 8 道错题作为上下文，直接问 AI。"""
                    try:
                        _recent = subject_items[:8]
                        if not _recent:
                            show_toast("这个科目还没有错题", "orange")
                            return
                        parts = []
                        for n, it in enumerate(_recent, 1):
                            parts.append(
                                f"{n}. [{it.get('status') or '未解决'}] "
                                + (it.get("original") or "（无题干）")[:120]
                                + (f"｜错因：{it.get('mistake')}" if it.get("mistake") else ""))
                        _msg = ("下面是我最近的错题，请先看整体：我主要错在哪几类？"
                                "按出现频率排序，并指出我该优先补哪个知识点。\\n\\n"
                                + "\\n".join(parts))
                        open_chat(subject, initial_message=_msg, auto_send=True)
                    except BaseException as _be:
                        _diag_log(_be, "ask_with_errors")
                        show_toast("打开失败，稍后再试", "red")

                search_input = ft.TextField(
                    label="🔍 搜索错题",'''
assert OLD4 in t
t = t.replace(OLD4, NEW4, 1)

OLD5 = '''                search_row = ft.Row([search_input, local_search_btn, ai_search_btn], spacing=10)'''
NEW5 = '''                search_row = ft.Row([search_input, local_search_btn, ai_search_btn], spacing=10)
                ask_ai_btn = ft.ElevatedButton("🤖 结合我的错题问 AI", icon=ft.Icons.PSYCHOLOGY,
                                               on_click=_ask_with_errors)'''
assert OLD5 in t
t = t.replace(OLD5, NEW5, 1)

OLD6 = '''                    search_row,
                    _chips_row,'''
NEW6 = '''                    search_row,
                    ask_ai_btn,
                    _chips_row,'''
assert OLD6 in t
t = t.replace(OLD6, NEW6, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("清理与错题AI入口完成")
