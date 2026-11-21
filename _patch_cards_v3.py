# -*- coding: utf-8 -*-
"""错题卡页：加「学科筛选」与「提醒卡」类型。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 类型选项加提醒卡 + 学科筛选控件
OLD = '''                _md = ft.Dropdown(label="版本", width=160, dense=True,
                                  options=[ft.dropdown.Option("question", "题目版（重做）"),
                                           ft.dropdown.Option("answer", "答案版（对答案）"),
                                           ft.dropdown.Option("both", "两份都导")],
                                  value="question")'''
NEW = '''                _md = ft.Dropdown(label="版本", width=170, dense=True,
                                  options=[ft.dropdown.Option("remind", "提醒卡（不重做）"),
                                           ft.dropdown.Option("question", "题目版（重做）"),
                                           ft.dropdown.Option("answer", "答案版（对答案）"),
                                           ft.dropdown.Option("both", "两份都导")],
                                  value="remind")
                _subj = ft.Dropdown(label="学科", width=130, dense=True,
                                    options=[ft.dropdown.Option(x) for x in
                                             ["全部", "数学", "语文", "英语", "物理", "化学",
                                              "生物", "历史", "政治", "地理"]],
                                    value="全部")'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 取数据时按学科过滤
OLD2 = '''                def _collect():
                    errs = load_jsonl(ERRORS_FILE)'''
NEW2 = '''                def _collect():
                    errs = load_jsonl(ERRORS_FILE)
                    s = str(_subj.value or "全部")
                    if s != "全部":
                        errs = [e for e in errs if e.get("subject") == s]'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# 3) 生成时按类型
OLD3 = '''                    _mode = "question" if st["mode"] == "both" else st["mode"]'''
NEW3 = '''                    _mode = "question" if st["mode"] == "both" else st["mode"]
                    if _mode == "remind":
                        st["pages"] = _render_error_pages(errs, mode="remind")
                        _show()
                        return'''
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

# 4) 事件绑定 + 界面
OLD4 = '''                for w in (_pp, _dr, _md):'''
NEW4 = '''                for w in (_pp, _dr, _md, _subj):'''
assert OLD4 in t
t = t.replace(OLD4, NEW4, 1)

OLD5 = '''                    ft.Row([_pp, _dr, _md, _bk], spacing=10, wrap=True),'''
NEW5 = '''                    ft.Row([_subj, _md, _pp, _dr, _bk], spacing=10, wrap=True),'''
assert OLD5 in t
t = t.replace(OLD5, NEW5, 1)

# 5) 导出「两份都导」时保持题目+答案
OLD6 = '''                        if st.get("mode") == "both":'''
NEW6 = '''                        if st.get("mode") == "both":'''
t = t.replace(OLD6, NEW6, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("学科筛选与提醒卡已加入")
