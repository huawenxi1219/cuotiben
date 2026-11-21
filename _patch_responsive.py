# -*- coding: utf-8 -*-
"""全局适配修复：弹窗宽度按屏幕收窄；多按钮行允许换行。"""
import io, re

SRC = r"C:\myapp\main.py"
src = io.open(SRC, encoding="utf-8").read()

# ---------- 1) 宽度钳制工具 ----------
HELPER = r'''
def _dlg_w(page, want=420, margin=56):
    """弹窗内容宽度：不超过屏幕宽度 - 边距（手机 360dp 也不会溢出）"""
    try:
        pw = page.width or (page.window.width if page.window else None) or 360
    except BaseException:
        pw = 360
    try:
        return max(220, min(int(want), int(pw) - margin))
    except BaseException:
        return int(want)


'''
anchor = "def load_vocab_settings():"
assert anchor in src
src = src.replace(anchor, HELPER.lstrip("\n") + anchor, 1)

# ---------- 2) 弹窗容器宽度：写死 → 按屏幕钳制 ----------
before = src
src = re.sub(r"width=(3\d{2}|4\d{2}|5\d{2}), height=",
             lambda m: f"width=_dlg_w(page, {m.group(1)}), height=", src)
changed_w = len(re.findall(r"_dlg_w\(page, \d+\)", src))

# ---------- 3) 多按钮行加 wrap=True ----------
lines = src.split("\n")
out = []
i = 0
added = 0
while i < len(lines):
    ln = lines[i]
    if "ft.Row(" in ln:
        depth = 0
        started = False
        j = i
        while j < len(lines):
            for ch in lines[j]:
                if ch in "([{":
                    depth += 1; started = True
                elif ch in ")]}":
                    depth -= 1
            if started and depth <= 0:
                break
            j += 1
        block = "\n".join(lines[i:j + 1])
        n_btn = len(re.findall(r"ft\.(?:ElevatedButton|TextButton|OutlinedButton|IconButton)\(", block))
        if n_btn >= 3 and "wrap=True" not in block:
            # 在 Row 的右括号前插入 wrap=True
            last = lines[j]
            idx = last.rfind(")")
            if idx >= 0:
                lines[j] = last[:idx] + ", wrap=True" + last[idx:]
                added += 1
    i += 1

src = "\n".join(lines)
io.open(SRC, "w", encoding="utf-8", newline="\n").write(src)
print(f"宽度钳制点: {changed_w} 处；按钮行加 wrap: {added} 处")
