# -*- coding: utf-8 -*-
"""错题卡页升级：题目版 / 答案版 / 两份都导；编号可查。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 状态里加 mode
OLD = '''                st = {"per": 6, "blank": False, "days": "", "pages": [], "idx": 0}'''
NEW = '''                st = {"per": 6, "blank": False, "days": "", "pages": [], "idx": 0, "mode": "question"}'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 版本下拉 + 编号查询
OLD2 = '''                _bk = ft.Switch(label="演算留白", value=False)
                _busy = {"v": False}'''
NEW2 = '''                _bk = ft.Switch(label="演算留白", value=False)
                _md = ft.Dropdown(label="版本", width=160, dense=True,
                                  options=[ft.dropdown.Option("question", "题目版（重做）"),
                                           ft.dropdown.Option("answer", "答案版（对答案）"),
                                           ft.dropdown.Option("both", "两份都导")],
                                  value="question")
                _lookup = ft.TextField(label="按编号查（如 001）", width=170, dense=True)
                _lookup_txt = ft.Text("", size=12, color=C_TEXT2)
                _busy = {"v": False}'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# 3) 生成时带上 mode
OLD3 = '''                    st["pages"] = _render_error_pages(errs, per_page=int(_pp.value or 6),
                                                      blank=bool(_bk.value))'''
NEW3 = '''                    st["errs"] = errs
                    st["mode"] = _md.value or "question"
                    _mode = "question" if st["mode"] == "both" else st["mode"]
                    st["pages"] = _render_error_pages(errs, per_page=int(_pp.value or 6),
                                                      blank=bool(_bk.value), mode=_mode)'''
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

# 4) 导出 PDF：两份时拼在一起
OLD4 = '''                        with open(p, "wb") as f:
                            f.write(_pages_to_pdf(st["pages"]))'''
NEW4 = '''                        _all = list(st["pages"])
                        if st.get("mode") == "both":
                            _all += _render_error_pages(st.get("errs") or [],
                                                        per_page=int(_pp.value or 6),
                                                        blank=False, mode="answer")
                        with open(p, "wb") as f:
                            f.write(_pages_to_pdf(_all))'''
assert OLD4 in t
t = t.replace(OLD4, NEW4, 1)

# 5) 事件绑定 + 编号查询
OLD5 = '''                for w in (_pp, _dr):
                    w.on_change = _regen
                _bk.on_change = _regen'''
NEW5 = '''                for w in (_pp, _dr, _md):
                    w.on_change = _regen
                _bk.on_change = _regen

                def _do_lookup(e=None):
                    q = (_lookup.value or "").strip()
                    if not q.isdigit():
                        _lookup_txt.value = ""
                        page.update()
                        return
                    idx = int(q) - 1
                    errs = st.get("errs") or _collect()
                    if 0 <= idx < len(errs):
                        _lookup_txt.value = f"{int(q):03d} → " + _err_title(errs[idx])[:60]
                    else:
                        _lookup_txt.value = f"没有 {int(q):03d} 号（共 {len(errs)} 道）"
                    page.update()

                _lookup.on_submit = _do_lookup'''
assert OLD5 in t
t = t.replace(OLD5, NEW5, 1)

# 6) 界面里插入
OLD6 = '''                    ft.Row([_pp, _dr, _bk], spacing=10, wrap=True),
                    _info,'''
NEW6 = '''                    ft.Row([_pp, _dr, _md, _bk], spacing=10, wrap=True),
                    ft.Row([_lookup, _lookup_txt], spacing=10, wrap=True),
                    _info,'''
assert OLD6 in t
t = t.replace(OLD6, NEW6, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("错题卡：版本 + 编号查询已加入")
