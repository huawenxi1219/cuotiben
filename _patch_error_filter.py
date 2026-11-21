# -*- coding: utf-8 -*-
"""错题本：加状态筛选（全部/未解决/待查/已解决）+ 显示掌握程度。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 颜色映射补新状态
OLD = '''                            status_color = {"未看": "#9E9E9E", "已看": "#4CAF50",
                                            "重要": "#F44336", "已掌握": "#2196F3"}.get(status, "#9E9E9E")'''
NEW = '''                            status_color = {"未看": "#9E9E9E", "已看": "#4CAF50",
                                            "重要": "#F44336", "已掌握": "#2196F3",
                                            "未解决": "#F7768E", "待查": "#E0AF68",
                                            "已解决": "#4DB6AC"}.get(status, "#9E9E9E")'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 筛选行
OLD2 = '''                search_status = ft.Text("", size=13, color=ft.Colors.GREY_500)
                search_row = ft.Row([search_input, local_search_btn, ai_search_btn], spacing=10)'''
NEW2 = '''                search_status = ft.Text("", size=13, color=ft.Colors.GREY_500)
                search_row = ft.Row([search_input, local_search_btn, ai_search_btn], spacing=10)

                _flt = {"v": "全部"}
                _chips_row = ft.Row(spacing=8, wrap=True)

                def _render_chips():
                    _chips_row.controls.clear()
                    for name, color in (("全部", "#7AA2F7"), ("未解决", "#F7768E"),
                                        ("待查", "#E0AF68"), ("已解决", "#4DB6AC")):
                        active = _flt["v"] == name
                        _chips_row.controls.append(ft.Container(
                            content=ft.Text(name, size=12,
                                            color="#0B0D14" if active else "#C9CFE0"),
                            padding=ft.Padding(12, 6, 12, 6), border_radius=14,
                            bgcolor=color if active else "#24283B",
                            on_click=lambda e, n=name: _pick(n), ink=True))

                def _pick(name):
                    _flt["v"] = name
                    _render_chips()
                    if name == "全部":
                        render_list()
                    else:
                        render_list([(it, None) for it in subject_items
                                     if (it.get("status") or "未解决") == name])

                _render_chips()'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# 3) 插到页面
OLD3 = '''                    search_row,
                    search_status,'''
NEW3 = '''                    search_row,
                    _chips_row,
                    search_status,'''
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

# 4) 卡片里显示掌握程度（跟在状态点后面）
OLD4 = '''                            status_dot = ft.Container(width=12, height=12, border_radius=6,
                                                      bgcolor=status_color, tooltip=status)'''
NEW4 = '''                            status_dot = ft.Container(width=12, height=12, border_radius=6,
                                                      bgcolor=status_color, tooltip=status)
                            _mastery = item.get("mastery") or ""
                            _sol_imgs = item.get("solution_media") or []'''
assert OLD4 in t
t = t.replace(OLD4, NEW4, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("错题本筛选已加入")
