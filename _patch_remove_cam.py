# -*- coding: utf-8 -*-
"""清理：
1. 删除无法工作的「相机」按钮（依赖 cv2，安卓上没有、也不值得为它加 60MB）
2. 删除已被新排版页取代的旧导出函数（open_card_options / on_export_cards_week）
"""
import io
import re

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 删相机按钮
cam_block = '''                # —— 相机按钮：直接调用摄像头拍照插入对话（拍不会的题）——
                cam_btn = ft.Container(
                    content=ft.Icon(ft.Icons.PHOTO_CAMERA_OUTLINED, size=20, color="#BBBBBB"),
                    width=38, height=38, border_radius=19,
                    bgcolor="#24283B", border=ft.border.all(1, "#414868"),
                    alignment=ft.alignment.center,
                    on_click=lambda e: pick_chat_camera(),
                    ink=True, tooltip="调用相机拍照（拍题直接问）",
                )

'''
assert cam_block in t, "相机按钮块未匹配"
t = t.replace(cam_block, "", 1)

# 2) 删 pick_chat_camera 函数（从 def 到 threading.Thread 那行结束）
start = t.index("                def pick_chat_camera():")
end = t.index("                    threading.Thread(target=_shot, daemon=True).start()\n", start)
end += len("                    threading.Thread(target=_shot, daemon=True).start()\n")
t = t[:start] + t[end:]

# 3) 若布局里还引用了 cam_btn，去掉
t = re.sub(r"\n\s*cam_btn,\s*\n", "\n", t)

# 4) 删旧的导出选项函数与本周导出（已被 build_cards_page 取代）
for fn_start, fn_end_marker in [
    ("            def on_export_cards_week(e):", "            def on_export_cards(e):"),
]:
    if fn_start in t:
        s = t.index(fn_start)
        e = t.index(fn_end_marker, s)
        t = t[:s] + t[e:]

if "def open_card_options(" in t:
    s = t.index("            def open_card_options(")
    e = t.index("            def on_export_cards(e):", s)
    t = t[:s] + t[e:]

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("相机按钮与旧导出函数已清理")
