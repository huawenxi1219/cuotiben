# -*- coding: utf-8 -*-
"""易用性优化：把「保存错题 / 批量录题」从表单最底部移到科目+题干下方。

理由：录一道题要滑到底才能保存，太慢；放在题干下，填完就能存，补充信息可选。
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

BTN_ROW = '''                ft.Row([
                    u_primary_btn("保存错题", submit_error, ft.Icons.SAVE),
                    u_primary_btn("批量录题", batch_import, ft.Icons.PHOTO_LIBRARY, color="#9ECE6A"),
                ], spacing=10),
'''
if BTN_ROW not in t:
    raise SystemExit("找不到按钮行")

# 1) 先从原位置删掉
t = t.replace(BTN_ROW, "", 1)

# 2) 插到「科目/原题/错因」卡片之后
ANCHOR = '''                    original_input,
                    _mk_sym_bar(),
                    mistake_input,
                ], spacing=12)),
'''
NEW = ANCHOR + '''                ft.Row([
                    u_primary_btn("保存错题", submit_error, ft.Icons.SAVE),
                    u_primary_btn("批量录题", batch_import, ft.Icons.PHOTO_LIBRARY, color="#9ECE6A"),
                ], spacing=10),
'''
assert ANCHOR in t
t = t.replace(ANCHOR, NEW, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("保存按钮已上移")
