# -*- coding: utf-8 -*-
"""批量录题：让 AI 自动判断科目，逐条可改；入库按各自科目。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 识别提示词加 subject 字段
OLD = '''  "knowledge_point": "该题涉及的知识点（如：三角函数、力学、非谓语动词等）",'''
NEW = '''  "subject": "这道题属于哪一科，只能从这些里选一个：语文、数学、英语、物理、化学、生物、历史、政治、地理",
  "knowledge_point": "该题涉及的知识点（如：三角函数、力学、非谓语动词等）",'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 结果带上科目
OLD2 = '''                                    "kp": str(r.get("knowledge_point") or "").strip(),
                                    "media": rel,
                                })'''
NEW2 = '''                                    "kp": str(r.get("knowledge_point") or "").strip(),
                                    "subj": str(r.get("subject") or "").strip(),
                                    "media": rel,
                                })'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

# 3) 确认页：每条一个科目下拉，默认用 AI 识别的
OLD3 = '''                checks = []
                col = ft.Column([], spacing=2, scroll=ft.ScrollMode.AUTO)
                for i, r in enumerate(results):
                    cb = ft.Checkbox(value=True)
                    checks.append((cb, r))
                    col.controls.append(ft.Row([
                        cb,
                        ft.Column([
                            ft.Text(r["q"][:46].replace("\\n", " "), size=13, color=C_TEXT),
                            ft.Text((r["kp"] or "未识别知识点"), size=11, color=C_TEXT2),
                        ], spacing=1, expand=True),
                    ], spacing=6))'''
NEW3 = '''                _SUBJ_LIST = ["数学", "语文", "英语", "物理", "化学", "生物", "历史", "政治", "地理"]
                checks = []
                col = ft.Column([], spacing=2, scroll=ft.ScrollMode.AUTO)
                for i, r in enumerate(results):
                    cb = ft.Checkbox(value=True)
                    _guess = r.get("subj") or ""
                    if _guess not in _SUBJ_LIST:
                        _guess = subj_batch.value if subj_batch.value in _SUBJ_LIST else "数学"
                    sd = ft.Dropdown(options=[ft.dropdown.Option(x) for x in _SUBJ_LIST],
                                     value=_guess, width=96, dense=True, text_size=12)
                    checks.append((cb, r, sd))
                    col.controls.append(ft.Row([
                        cb,
                        ft.Column([
                            ft.Text(r["q"][:40].replace("\\n", " "), size=13, color=C_TEXT),
                            ft.Text((r["kp"] or "未识别知识点"), size=11, color=C_TEXT2),
                        ], spacing=1, expand=True),
                        sd,
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER))'''
assert OLD3 in t, "确认页列表未匹配"
t = t.replace(OLD3, NEW3, 1)

# 4) 入库按各自科目
OLD4 = '''                def do_save(ev):
                    picked = [r for cb, r in checks if cb.value]
                    if not picked:
                        show_toast("一道都没选", "red")
                        return
                    subj = subj_batch.value or "数学"
                    n = 0
                    for r in picked:
                        try:
                            save_error(subj, r["q"], [r["media"]] if r["media"] else [],
                                       r["a"], [], r["et"], "", [], r["kp"])
                            n += 1
                        except BaseException:
                            pass
                    page.close(dlg2)
                    show_toast(f"✅ 已入库 {n} 道（{subj}）", "green")'''
NEW4 = '''                def do_save(ev):
                    picked = [(r, sd) for cb, r, sd in checks if cb.value]
                    if not picked:
                        show_toast("一道都没选", "red")
                        return
                    n = 0
                    by_subj = {}
                    for r, sd in picked:
                        subj = (sd.value or subj_batch.value or "数学")
                        try:
                            save_error(subj, r["q"], [r["media"]] if r["media"] else [],
                                       r["a"], [], r["et"], "", [], r["kp"])
                            n += 1
                            by_subj[subj] = by_subj.get(subj, 0) + 1
                        except BaseException:
                            pass
                    page.close(dlg2)
                    detail = "、".join(f"{k}{v}道" for k, v in by_subj.items())
                    show_toast(f"✅ 已入库 {n} 道：{detail}", "green")'''
assert OLD4 in t, "do_save 未匹配"
t = t.replace(OLD4, NEW4, 1)

# 5) 说明文字
OLD5 = '''                        ft.Text("勾掉不要的，确认后按这个科目入库", size=12, color=C_TEXT2),'''
NEW5 = '''                        ft.Text("勾掉不要的；科目是 AI 猜的，可逐条改", size=12, color=C_TEXT2),'''
assert OLD5 in t
t = t.replace(OLD5, NEW5, 1)

# 6) 1M 上下文：回答上限提到 4096
t = t.replace('"temperature": 0.7, "max_tokens": 2048, "stream": True',
              '"temperature": 0.7, "max_tokens": 4096, "stream": True', 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("批量录题：自动分科 + 逐条可改 已加入")
