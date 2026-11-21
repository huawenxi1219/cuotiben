# -*- coding: utf-8 -*-
"""删除残留的手环同步函数（界面上已无入口，属于死代码）。"""
import io
import re

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

TARGETS = ["on_band_sync_new_words", "on_band_quick_push", "on_band_export_click",
           "on_band_export_result", "on_band_records_click", "on_band_records_result",
           "band_do_save"]

# 这些函数只被手环逻辑使用，整体删除
def cut_function(src, name):
    pat = re.compile(r"\n(\s*)def " + re.escape(name) + r"\(")
    m = pat.search(src)
    if not m:
        return src, False
    indent = m.group(1)
    start = m.start() + 1
    # 找下一个同缩进的 def/注释块
    rest = src[start:]
    nxt = None
    for mm in re.finditer(r"\n" + indent + r"(def |# ----------|@|class )", rest):
        nxt = mm.start()
        break
    end = start + (nxt if nxt is not None else len(rest))
    return src[:start] + src[end:], True


for name in TARGETS:
    t, ok = cut_function(t, name)
    print(("删除 " if ok else "未找到 ") + name)

# 若还有 do_save 残留引用 band_ 变量，把那个 do_save 也删掉
m = re.search(r"\n(\s*)def do_save\(", t)
if m:
    indent = m.group(1)
    start = m.start() + 1
    rest = t[start:]
    nxt = None
    for mm in re.finditer(r"\n" + indent + r"(def |# ----------|@|class )", rest):
        nxt = mm.start()
        break
    end = start + (nxt if nxt is not None else len(rest))
    body = t[start:end]
    if "band_" in body and "band_" not in t.replace(body, ""):
        t = t[:start] + t[end:]
        print("删除孤立 do_save")

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("清理完成")
