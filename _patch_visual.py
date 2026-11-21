# -*- coding: utf-8 -*-
"""视觉统一：去掉满屏毛玻璃，改成"实色卡片 + 细线 + 轻阴影"，统一字号/圆角/留白。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 设计令牌 ----------
TOKENS = '''
# ===== 设计令牌：全站统一，别处不要再写死颜色 =====
C_BG = "#0E1016"        # 页面底色
C_SURF = "#151824"      # 卡片
C_SURF2 = "#1B1F2E"     # 卡片内的次级块
C_LINE = "#262B3D"      # 分割线/描边
C_TEXT = "#E8EBF5"      # 主文字
C_TEXT2 = "#98A1B8"     # 次文字
C_ACCENT = "#6E8BFF"    # 强调色
R_CARD = 18             # 卡片圆角

'''
anchor = "DEBUG = True"
assert anchor in t
t = t.replace(anchor, anchor + "\n" + TOKENS, 1)

# ---------- 2) 卡片：去掉 blur，改实色 ----------
OLD_CARD = '''                card = ft.Container(
                    content=content,
                    padding=padding,
                    border_radius=radius,
                    bgcolor=bg,
                    blur=ft.Blur(18, 18, ft.BlurTileMode.CLAMP),
                    border=ft.border.all(1, "#33FFFFFF"),
                    shadow=ft.BoxShadow(blur_radius=18, color="#33000000",
                                        offset=ft.Offset(0, 6)),
                    **hover_kw,
                )
                return card'''
NEW_CARD = '''                card = ft.Container(
                    content=content,
                    padding=padding,
                    border_radius=radius,
                    bgcolor=C_SURF if bg == "#CC1A1B26" else bg,
                    border=ft.border.all(1, C_LINE),
                    shadow=ft.BoxShadow(blur_radius=12, color="#22000000",
                                        offset=ft.Offset(0, 4)),
                    **hover_kw,
                )
                return card'''
assert OLD_CARD in t
t = t.replace(OLD_CARD, NEW_CARD, 1)

t = t.replace('def u_card(content, padding=18, radius=22, bg="#CC1A1B26"):',
              'def u_card(content, padding=18, radius=R_CARD, bg=C_SURF):', 1)
t = t.replace('"""苹果风液态玻璃卡片：半透明底色 + 背景模糊 + 细亮边 + 柔和阴影"""',
              '"""统一卡片：实色底 + 1px 细边 + 极轻阴影（不用 blur，省性能也更干净）"""', 1)

# ---------- 3) 分区标题 ----------
OLD_SEC = '''                return ft.Row([
                    ft.Text((icon + "  " if icon else "") + title,
                            size=13, weight=ft.FontWeight.W_600, color="#8E8E93"),
                    ft.Container(expand=True, height=1, bgcolor="#2A2A32"),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)'''
NEW_SEC = '''                return ft.Row([
                    ft.Text((icon + "  " if icon else "") + title,
                            size=12, weight=ft.FontWeight.W_600, color=C_TEXT2),
                    ft.Container(expand=True, height=1, bgcolor=C_LINE),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)'''
assert OLD_SEC in t
t = t.replace(OLD_SEC, NEW_SEC, 1)

# ---------- 4) 主按钮 ----------
OLD_BTN = '''                return ft.ElevatedButton(
                    text, icon=icon, on_click=on_click,
                    bgcolor=color, color="#FFFFFF",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=14),
                        padding=ft.Padding(left=20, right=20, top=14, bottom=14)),
                    expand=True)'''
NEW_BTN = '''                return ft.ElevatedButton(
                    text, icon=icon, on_click=on_click,
                    bgcolor=color, color="#0B0D14", height=52,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=16),
                        padding=ft.Padding(left=20, right=20, top=14, bottom=14),
                        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_600)),
                    expand=True)'''
assert OLD_BTN in t
t = t.replace(OLD_BTN, NEW_BTN, 1)

# ---------- 5) 主题色对齐 ----------
t = t.replace('surface="#1A1B26",', 'surface=C_SURF,', 1)
t = t.replace('surface_variant="#24283B",', 'surface_variant=C_SURF2,', 1)
t = t.replace('background="#16161E",', 'background=C_BG,', 1)
t = t.replace('on_surface="#C0CAF5",', 'on_surface=C_TEXT,', 1)
t = t.replace('on_background="#C0CAF5",', 'on_background=C_TEXT,', 1)
t = t.replace('primary="#7AA2F7",', 'primary=C_ACCENT,', 1)
t = t.replace('fill_color="#CC1F1F26",\n                        border_radius=14, border=ft.border.all(1, "#414868")',
              'fill_color=C_SURF,\n                        border_radius=14, border=ft.border.all(1, C_LINE)', 1)

# ---------- 6) 首页标题层级 ----------
t = t.replace('''                ft.Text("📸 拍照录题", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("拍下题目，AI 自动读取原文并分析错因", size=13, color="#8E8E93"),''',
              '''                ft.Text("拍照录题", size=28, weight=ft.FontWeight.W_700, color=C_TEXT),
                ft.Text("拍下题目，AI 自动读取原文并分析错因", size=13, color=C_TEXT2),''', 1)
t = t.replace('''                ft.Text("📝 记笔记", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("随手记录课堂重点与灵感", size=13, color="#8E8E93"),''',
              '''                ft.Text("记笔记", size=28, weight=ft.FontWeight.W_700, color=C_TEXT),
                ft.Text("随手记录课堂重点与灵感", size=13, color=C_TEXT2),''', 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("视觉统一已应用")
