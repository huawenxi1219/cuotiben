# -*- coding: utf-8 -*-
"""收尾三件事：笔记兜底挂导图 / 气泡入场动画 / 抽屉状态收口。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 笔记：知识点为空就退回科目名，保证导图里一定有节点 ----------
OLD = """                        save_note(_subj, content, media=[], tags=[_kp] if _kp else None)
                        show_toast(f"✅ 已收录笔记{(' · 已挂知识树：' + _kp) if _kp else ''}", "green")"""
NEW = """                        # 知识点为空时用科目名兜底，保证思维导图里一定能长出节点
                        _tags_final = [_kp] if _kp else [_subj]
                        save_note(_subj, content, media=[], tags=_tags_final)
                        try:
                            build_mindmap(_subj)   # 立刻并入知识树，不用等下次打开导图
                        except BaseException as _be:
                            _diag_log(_be, "L4001")
                        show_toast(f"✅ 已收录笔记 · 已挂到「{_tags_final[0]}」", "green")"""
assert OLD in t, "笔记保存段落未匹配"
t = t.replace(OLD, NEW, 1)

# ---------- 2) 气泡入场动画（淡入 + 轻微上浮），线程只跑 30ms ----------
OLD2 = """                def make_user_bubble(text):"""
NEW2 = """                def _pop_in(ctl):
                    \"\"\"气泡入场：从下方 8% 处淡入，30ms 后触发，只跑一次线程\"\"\"
                    def _run():
                        time.sleep(0.03)
                        try:
                            ctl.opacity = 1.0
                            ctl.offset = ft.Offset(0, 0)
                            page.update()
                        except BaseException:
                            pass
                    threading.Thread(target=_run, daemon=True).start()

                def make_user_bubble(text):"""
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# 用户气泡容器加动画属性
OLD3 = """                            shadow=ft.BoxShadow(blur_radius=10, color="#44000000"),
                            width=300,
                        ),
                    ], alignment=ft.MainAxisAlignment.END)"""
NEW3 = """                            shadow=ft.BoxShadow(blur_radius=10, color="#44000000"),
                            width=300,
                            opacity=0,
                            offset=ft.Offset(0, 0.08),
                            animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                            animate_offset=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
                        ),
                    ], alignment=ft.MainAxisAlignment.END)"""
assert OLD3 in t, "用户气泡未匹配"
t = t.replace(OLD3, NEW3, 1)

# 用户气泡 return 处触发动画
OLD4 = """                    return ft.GestureDetector(
                        content=_row,
                        on_long_press=lambda e: _ask_collect_menu(_bubble_text, "我的提问"))"""
NEW4 = """                    _pop_in(_row.controls[-1])
                    return ft.GestureDetector(
                        content=_row,
                        on_long_press=lambda e: _ask_collect_menu(_bubble_text, "我的提问"))"""
assert OLD4 in t, "用户气泡返回处未匹配"
t = t.replace(OLD4, NEW4, 1)

# AI 气泡容器加动画
OLD5 = """                        border=ft.border.all(1, "#55414868"),
                        shadow=ft.BoxShadow(blur_radius=10, color="#33000000"),
                        width=300,
                    )
                    avatar = ft.Container("""
NEW5 = """                        border=ft.border.all(1, "#55414868"),
                        shadow=ft.BoxShadow(blur_radius=10, color="#33000000"),
                        width=300,
                        opacity=0,
                        offset=ft.Offset(0, 0.08),
                        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                        animate_offset=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
                    )
                    _pop_in(bubble)
                    avatar = ft.Container("""
assert OLD5 in t, "AI 气泡未匹配"
t = t.replace(OLD5, NEW5, 1)

# ---------- 3) 关闭聊天时把抽屉状态收掉 ----------
OLD6 = """                try:
                    chat_dialog.visible = False
                    ball_container.visible = True
                except BaseException as _be:"""
NEW6 = """                try:
                    chat_dialog.visible = False
                    ball_container.visible = True
                    _drawer["open"] = False          # 切页时收掉抽屉，避免残留半开状态
                    drawer_container.right = -330
                except BaseException as _be:"""
assert OLD6 in t, "开关闭未匹配"
t = t.replace(OLD6, NEW6, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("收尾改造完成")
