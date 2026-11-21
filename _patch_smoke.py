# -*- coding: utf-8 -*-
"""把单点自测钩子升级成"巡检"：一次跑完主要页面与对话构建，逐个报 OK/FAIL。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

OLD = '''            if os.environ.get("DSH_OPEN_TEST") == "1":
                try:
                    open_function_page("数学", "思维导图")
                    print("[selftest] 思维导图页构建成功")
                except Exception:
                    print("[selftest] 思维导图页构建失败：")
                    traceback.print_exc()'''

NEW = '''            # 自测钩子：DSH_SMOKE=1 时把主要页面/对话逐个构建一遍，输出 [SMOKE] 结果
            if os.environ.get("DSH_SMOKE") == "1" or os.environ.get("DSH_OPEN_TEST") == "1":
                _smoke_steps = [
                    ("思维导图-数学", lambda: open_function_page("数学", "思维导图")),
                    ("错题本-数学", lambda: open_function_page("数学", "错题本")),
                    ("笔记本-数学", lambda: open_function_page("数学", "笔记本")),
                    ("单词本-英语", lambda: open_function_page("英语", "单词本")),
                    ("金句-英语", lambda: open_function_page("英语", "金句")),
                    ("对话-总AI", lambda: open_chat("总AI")),
                    ("对话-数学", lambda: open_chat("数学")),
                    ("导图页重建", lambda: build_mindmap_page("数学")),
                ]
                _ok = 0
                for _name, _fn in _smoke_steps:
                    try:
                        _fn()
                        print("[SMOKE] OK  ", _name)
                        _ok += 1
                    except Exception:
                        print("[SMOKE] FAIL", _name)
                        traceback.print_exc()
                print(f"[SMOKE] 完成 {_ok}/{len(_smoke_steps)}")'''

assert OLD in t, "自测钩子未匹配"
t = t.replace(OLD, NEW, 1)
io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("巡检钩子已升级")
