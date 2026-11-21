# -*- coding: utf-8 -*-
"""1) 错题详情加「重做这道」 2) 删掉历史死函数"""
import ast, io, re

MAIN = r"C:\myapp\main.py"
src = io.open(MAIN, encoding="utf-8").read()

# ---------------- 1) 重做按钮 ----------------
OLD = """                                    action_row = ft.Row([
                                        ft.ElevatedButton("🎓 问老师", on_click=open_ask_teacher,
                                                          icon=ft.Icons.SCHOOL, bgcolor="#7AA2F7",
                                                          color=ft.Colors.WHITE),"""
NEW = """                                    def open_redo(e):
                                        \"\"\"重做：把题丢回对话，让 AI 先别给答案，自己再做一遍\"\"\"
                                        page.close(detail_dlg)
                                        subj_redo = item_data.get("subject", "总AI")
                                        q_redo = item_data.get("original", "") or item_data.get("question", "")
                                        prompt = f\"\"\"这道题我之前做错过，现在想自己重做一遍。请你**先不要给答案**：

📝 题目：{q_redo}

请按这个节奏来：
1. 先问我「你打算从哪入手」，让我自己说思路
2. 我说不出来时，只给一句提示，不要直接讲解法
3. 我写出答案后，你再判对错、讲清楚关键那一步
4. 最后出一道同类型的变式题，让我当场练\"\"\"
                                        try:
                                            log_learning_event("redo", subj_redo,
                                                               kp=(item_data.get("tags") or [""])[0],
                                                               detail=f"重做：{q_redo[:60]}")
                                        except BaseException:
                                            pass
                                        open_chat(subj_redo, initial_message=prompt, auto_send=True)

                                    action_row = ft.Row([
                                        ft.ElevatedButton("🔄 重做", on_click=open_redo,
                                                          icon=ft.Icons.REPLAY,
                                                          bgcolor="#E0AF68", color="#1A1B26"),
                                        ft.ElevatedButton("🎓 问老师", on_click=open_ask_teacher,
                                                          icon=ft.Icons.SCHOOL, bgcolor="#7AA2F7",
                                                          color=ft.Colors.WHITE),"""
assert OLD in src, "详情按钮区未匹配"
src = src.replace(OLD, NEW, 1)

# ---------------- 2) 删除死函数 ----------------
DEAD = ["schedule_next_review", "get_today_new_words",
        "convert_chemical_formula", "load_content_lib", "show_message"]

tree = ast.parse(src)
lines = src.split("\n")
drop = set()
for node in tree.body:                      # 只看模块级
    if isinstance(node, ast.FunctionDef) and node.name in DEAD:
        start = node.lineno - 1
        for d in getattr(node, "decorator_list", []):
            start = min(start, d.lineno - 1)
        end = node.end_lineno - 1
        for i in range(start, end + 1):
            drop.add(i)
        # 顺带删掉后面的空行
        j = end + 1
        while j < len(lines) and lines[j].strip() == "":
            drop.add(j)
            j += 1

kept = [ln for i, ln in enumerate(lines) if i not in drop]
src = "\n".join(kept)
io.open(MAIN, "w", encoding="utf-8", newline="\n").write(src)
print("已删除死函数:", ", ".join(DEAD))
print("新行数:", len(src.split("\n")))
