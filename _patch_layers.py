# -*- coding: utf-8 -*-
"""层级修复：聊天窗打开时隐藏悬浮球（现在球会盖在对话上面）；关闭时恢复。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 打开聊天 → 隐藏悬浮球
OLD = """                chat_dialog.visible = True"""
NEW = """                chat_dialog.visible = True
                try:
                    ball_container.visible = False   # 层级：聊天窗盖住悬浮球，别让它飘在对话上
                except BaseException:
                    pass"""
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 聊天窗的返回按钮 → 恢复悬浮球
OLD2 = """                                          on_click=lambda e: (_cleanup_pending_chat_imgs(),
                                                              setattr(chat_dialog, 'visible', False),
                                                              page.update())),"""
NEW2 = """                                          on_click=lambda e: (_cleanup_pending_chat_imgs(),
                                                              setattr(chat_dialog, 'visible', False),
                                                              setattr(ball_container, 'visible', True),
                                                              page.update())),"""
assert OLD2 in t, "返回按钮未匹配"
t = t.replace(OLD2, NEW2, 1)

# 3) 切换底部导航时也恢复
OLD3 = """                try:
                    chat_dialog.visible = False
                except BaseException as _be:"""
NEW3 = """                try:
                    chat_dialog.visible = False
                    ball_container.visible = True
                except BaseException as _be:"""
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("层级修复完成")
