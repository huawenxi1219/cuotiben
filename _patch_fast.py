# -*- coding: utf-8 -*-
"""对话提速：新增「快速模式」开关（关掉教材/错题/笔记检索、压缩上下文预算）。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 教材检索：快速模式下 top=0
OLD1 = "                        _tb = search_textbook(subject, _tq)"
NEW1 = ("                        _tb = search_textbook(subject, _tq,\n"
        "                                              top=0 if load_ai_config().get(\"fast_mode\") else 3)")
assert OLD1 in t
t = t.replace(OLD1, NEW1, 1)

# 2) 错题/笔记检索：快速模式下 limit=0
OLD2 = "                        rel = pick_relevant_errors(content, subject if subject != \"总AI\" else None, limit=5)"
NEW2 = ("                        rel = pick_relevant_errors(content, subject if subject != \"总AI\" else None,\n"
        "                                                    limit=0 if _fast else 5)")
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

OLD3 = "                        rel_notes = pick_relevant_notes(content, subject if subject != \"总AI\" else None, limit=3)"
NEW3 = ("                        rel_notes = pick_relevant_notes(content, subject if subject != \"总AI\" else None,\n"
        "                                                        limit=0 if _fast else 3)")
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

# 3) _send_internal 里定义 _fast + 收紧上下文预算
OLD4 = '''                def _send_internal(content, insert_user_bubble=True):
                    nonlocal generation_active, stop_flag'''
NEW4 = '''                def _send_internal(content, insert_user_bubble=True):
                    nonlocal generation_active, stop_flag
                    _fast = bool(load_ai_config().get("fast_mode"))'''
assert OLD4 in t
t = t.replace(OLD4, NEW4, 1)

OLD5 = "                context_messages = build_ctx(history, max_chars=20000)"
NEW5 = "                context_messages = build_ctx(history, max_chars=8000 if _fast else 20000)"
assert OLD5 in t
t = t.replace(OLD5, NEW5, 1)

# 4) 设置页开关
OLD6 = '            gaokao_date_input = ft.TextField('
NEW6 = '''            fast_mode_switch = ft.Switch(
                label="快速模式（关掉教材/错题检索，回答更快）",
                value=bool(ai_config.get("fast_mode")),
                tooltip="赶时间时打开：不注入教材原文、相关错题和笔记，响应更快但个性化变弱")

            gaokao_date_input = ft.TextField('''
assert OLD6 in t
t = t.replace(OLD6, NEW6, 1)

OLD7 = '                cfg["deepseek_reasoning"] = str(deepseek_reasoning_dropdown.value or "medium")'
NEW7 = ('                cfg["deepseek_reasoning"] = str(deepseek_reasoning_dropdown.value or "medium")\n'
        '                cfg["fast_mode"] = bool(fast_mode_switch.value)')
assert OLD7 in t
t = t.replace(OLD7, NEW7, 1)

# 5) 把开关放进设置界面（deepseek_thinking_switch 之后）
OLD8 = "                deepseek_thinking_switch,"
NEW8 = "                deepseek_thinking_switch,\n                fast_mode_switch,"
assert OLD8 in t
t = t.replace(OLD8, NEW8, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("快速模式已加入")
