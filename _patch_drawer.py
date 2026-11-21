# -*- coding: utf-8 -*-
"""抽屉改造：长按后可选段落；抽屉里加「收进题目/错因/解答/笔记」分派按钮。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 新增 _field_append 工具 ----------
OLD = """                def _drawer_remove_item(idx):"""
NEW = """                def _field_append(field):
                    \"\"\"把已加入的片段追加到某个字段（题目/错因/解答/笔记）\"\"\"
                    _txt = "\\n".join(str(it).strip() for it in _drawer["items"] if str(it).strip())
                    if not _txt:
                        show_toast("先到对话里长按，把要用的段落加进来", "grey")
                        return
                    _cur = (field.value or "").strip()
                    field.value = (_cur + "\\n" + _txt).strip() if _cur else _txt
                    page.update()
                    show_toast("已收进去，可在框里继续改", "green")

                def _drawer_remove_item(idx):"""
assert OLD in t
t = t.replace(OLD, NEW, 1)

# ---------- 2) 抽屉里加分派按钮行 ----------
OLD2 = """                drawer_error_fields = ft.Column([drawer_q_input, drawer_m_input, drawer_a_input], spacing=8)
                drawer_note_fields = ft.Column([drawer_note_input], spacing=8)"""
NEW2 = """                drawer_error_fields = ft.Column([drawer_q_input, drawer_m_input, drawer_a_input], spacing=8)
                drawer_note_fields = ft.Column([drawer_note_input], spacing=8)

                # 分派按钮：把"已加入的片段"一键塞进指定字段
                drawer_assign_row = ft.Row([
                    ft.TextButton("⤵ 收进题目", on_click=lambda e: _field_append(drawer_q_input)),
                    ft.TextButton("⤵ 收进错因", on_click=lambda e: _field_append(drawer_m_input)),
                    ft.TextButton("⤵ 收进解答", on_click=lambda e: _field_append(drawer_a_input)),
                ], spacing=0, wrap=True)
                drawer_assign_note_row = ft.Row([
                    ft.TextButton("⤵ 收进笔记", on_click=lambda e: _field_append(drawer_note_input)),
                ], spacing=0)"""
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# ---------- 3) 切模式时显示对应按钮 ----------
OLD3 = """                    drawer_error_fields.visible = (mode == "error")
                    drawer_note_fields.visible = (mode == "note")"""
NEW3 = """                    drawer_error_fields.visible = (mode == "error")
                    drawer_note_fields.visible = (mode == "note")
                    drawer_assign_row.visible = (mode == "error")
                    drawer_assign_note_row.visible = (mode == "note")"""
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

# ---------- 4) 布局里插入按钮行 ----------
OLD4 = """                        drawer_error_fields,
                        drawer_note_fields,"""
NEW4 = """                        drawer_assign_row,
                        drawer_assign_note_row,
                        drawer_error_fields,
                        drawer_note_fields,"""
assert OLD4 in t
t = t.replace(OLD4, NEW4, 1)

# ---------- 5) 长按菜单：改成"选段落" ----------
OLD5 = """                def _ask_collect_menu(text, source="AI 解答"):
                    _t = (text or "").strip()
                    if not _t:
                        show_toast("这条消息还没有内容", "grey")
                        return
                    _q = _t if source == "我的提问" else str(last_user_msg.get("text", "") or "")
                    dlg = ft.AlertDialog(
                        title=ft.Text("收录到哪里？"),
                        content=ft.Text(f"来自「{source}」气泡 · {len(_t)} 字\\n将自动识别题目 / 错因 / 知识点", size=13, color="#888888"),
                        actions=[
                            ft.ElevatedButton("📕 收录错题", icon=ft.Icons.EDIT_NOTE,
                                              on_click=lambda e: (page.close(dlg), _drawer_open("error", _t, _q))),
                            ft.ElevatedButton("📓 收录笔记", icon=ft.Icons.BOOKMARK_ADD,
                                              on_click=lambda e: (page.close(dlg), _drawer_open("note", _t, _q))),
                            ft.TextButton("取消", on_click=lambda e: page.close(dlg)),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END)
                    page.open(dlg)
                    page.update()"""

NEW5 = """                def _ask_collect_menu(text, source="AI 解答"):
                    _t = (text or "").strip()
                    if not _t:
                        show_toast("这条消息还没有内容", "grey")
                        return
                    _q = _t if source == "我的提问" else str(last_user_msg.get("text", "") or "")
                    # 按空行/句号切段，让用户自己挑要收哪几段
                    _segs = [s.strip() for s in re.split(r"\\n{2,}|(?<=[。！？；])|(?<=[.!?] )", _t) if s.strip()]
                    if not _segs:
                        _segs = [_t]
                    _segs = _segs[:20]
                    _checks = []
                    _seg_col = ft.Column([], spacing=0, scroll=ft.ScrollMode.AUTO)
                    for _i, _s in enumerate(_segs):
                        _label = _s.replace("\\n", " ")
                        if len(_label) > 34:
                            _label = _label[:34] + "…"
                        _cb = ft.Checkbox(label=_label, value=True)
                        _checks.append((_cb, _s))
                        _seg_col.controls.append(_cb)

                    def _go(_mode):
                        _picked = [s for cb, s in _checks if cb.value]
                        page.close(dlg)
                        if not _picked:
                            show_toast("至少选一段", "red")
                            return
                        _drawer_open(_mode, "\\n\\n".join(_picked), _q)

                    dlg = ft.AlertDialog(
                        title=ft.Text("选要收哪几段？"),
                        content=ft.Column([
                            ft.Text(f"来自「{source}」· 勾选后收录，可再改", size=12, color="#888888"),
                            ft.Container(content=_seg_col, height=min(260, 30 * len(_segs) + 8),
                                         width=330, padding=2),
                        ], spacing=6),
                        actions=[
                            ft.ElevatedButton("📕 收错题", icon=ft.Icons.EDIT_NOTE,
                                              on_click=lambda e: _go("error")),
                            ft.ElevatedButton("📓 收笔记", icon=ft.Icons.BOOKMARK_ADD,
                                              on_click=lambda e: _go("note")),
                            ft.TextButton("取消", on_click=lambda e: page.close(dlg)),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END)
                    page.open(dlg)
                    page.update()"""
assert OLD5 in t, "长按菜单未匹配"
t = t.replace(OLD5, NEW5, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("抽屉/选段改造完成")
