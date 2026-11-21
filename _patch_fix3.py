# -*- coding: utf-8 -*-
"""修三处：菜单挡板高度、历史气泡动画线程风暴、以及给关键页面加错误兜底。"""
import io, re

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 悬浮菜单：固定高度，别让它铺满屏幕 ----------
OLD = """                contact_panel.left = panel_x
                contact_panel.top = panel_y
                contact_panel.right = None
                contact_panel.bottom = None"""
NEW = """                contact_panel.left = panel_x
                contact_panel.top = panel_y
                contact_panel.width = panel_w
                contact_panel.height = panel_h      # 之前没设高度，Stack 里会撑成一大块半透明挡板
                contact_panel.right = None
                contact_panel.bottom = None"""
assert OLD in t, "菜单定位未匹配"
t = t.replace(OLD, NEW, 1)

# ---------- 2) 气泡动画只用于新消息，历史消息不动画 ----------
t = t.replace("def make_user_bubble(text):", "def make_user_bubble(text, animate=False):", 1)
t = t.replace("def make_ai_bubble(text, can_regenerate=True, content_ref=None):",
              "def make_ai_bubble(text, can_regenerate=True, content_ref=None, animate=False):", 1)

t = t.replace("""                    _pop_in(_row.controls[-1])""",
              """                    if animate:
                        _pop_in(_row.controls[-1])""", 1)
t = t.replace("""                    _pop_in(bubble)""",
              """                    if animate:
                        _pop_in(bubble)""", 1)

# 历史渲染：不加动画（否则几十条消息会同时开线程刷 UI）
t = t.replace("chat_history_display.controls.append(make_user_bubble(msg[\"content\"]))",
              "chat_history_display.controls.append(make_user_bubble(msg[\"content\"], animate=False))", 1)
t = t.replace("bubble_row, content_col = make_ai_bubble(clean_text if clean_text else msg[\"content\"])",
              "bubble_row, content_col = make_ai_bubble(clean_text if clean_text else msg[\"content\"], animate=False)", 1)

# 运行时新消息：加动画
t = t.replace("chat_history_display.controls.append(make_user_bubble(content))",
              "chat_history_display.controls.append(make_user_bubble(content, animate=True))", 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("菜单高度 / 动画范围 已修")
