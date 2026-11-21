# -*- coding: utf-8 -*-
"""第二轮适配：剩下的固定宽度 + 弹窗高度也按屏幕钳制。"""
import io, re

SRC = r"C:\myapp\main.py"
src = io.open(SRC, encoding="utf-8").read()

# 高度工具
if "_dlg_h(" not in src:
    HELPER = r'''
def _dlg_h(page, want=480, margin=150):
    """弹窗内容高度：不超过屏幕高度 - 边距"""
    try:
        ph = page.height or (page.window.height if page.window else None) or 640
    except BaseException:
        ph = 640
    try:
        return max(200, min(int(want), int(ph) - margin))
    except BaseException:
        return int(want)


'''
    anchor = "def load_vocab_settings():"
    src = src.replace(anchor, HELPER.lstrip("\n") + anchor, 1)

# 1) 高度钳制（只处理 height=NNN, padding= 这种弹窗内容）
src = re.sub(r"height=(3\d{2}|4\d{2}|5\d{2}), padding=",
             lambda m: f"height=_dlg_h(page, {m.group(1)}), padding=", src)

# 2) 剩下的 Column/Container 固定宽度
src = re.sub(r"(,\s*)width=(3\d{2})\)", lambda m: f"{m.group(1)}width=_dlg_w(page, {m.group(2)}))", src)
src = re.sub(r"(,\s*)width=(3\d{2}), spacing=", lambda m: f"{m.group(1)}width=_dlg_w(page, {m.group(2)}), spacing=", src)
src = re.sub(r"width=(3\d{2}), padding=2\)", lambda m: f"width=_dlg_w(page, {m.group(1)}), padding=2)", src)

io.open(SRC, "w", encoding="utf-8", newline="\n").write(src)
print("剩余宽度/高度已钳制")
