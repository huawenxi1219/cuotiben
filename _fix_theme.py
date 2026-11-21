# -*- coding: utf-8 -*-
"""修复主题块：用 Flet 0.28 真实存在的 Theme 类与参数，让全局样式真正生效。"""
import io, re

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 定位旧的 page.theme = ft.Theme( ... ) 块（到 page.dark_theme = page.theme 前）
start = t.index("                page.theme = ft.Theme(")
end = t.index("                page.dark_theme = page.theme", start)

NEW = '''                page.theme = ft.Theme(
                    font_family="Segoe UI, -apple-system, Roboto, sans-serif",
                    color_scheme=ft.ColorScheme(
                        primary=C_ACCENT,
                        primary_container=C_SURF2,
                        secondary="#BB9AF7",
                        tertiary="#73DACA",
                        surface=C_SURF,
                        surface_variant=C_SURF2,
                        background=C_BG,
                        on_surface=C_TEXT,
                        on_background=C_TEXT,
                    ),
                    visual_density=ft.VisualDensity.STANDARD,
                    navigation_bar_theme=ft.NavigationBarTheme(
                        bgcolor="#D914141C", indicator_color=C_ACCENT, height=72),
                    elevated_button_theme=ft.ElevatedButtonTheme(style=_shared_btn_style),
                    text_button_theme=ft.TextButtonTheme(style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.Padding(left=16, right=16, top=10, bottom=10))),
                    card_theme=ft.CardTheme(color="#B31A1B26", elevation=6,
                                            shape=ft.RoundedRectangleBorder(radius=18)),
                    dialog_theme=ft.DialogTheme(bgcolor="#F21A1B26", elevation=24,
                                                shape=ft.RoundedRectangleBorder(radius=26)),
                    snackbar_theme=ft.SnackBarTheme(bgcolor="#E61A1B26", elevation=6,
                                                    shape=ft.RoundedRectangleBorder(radius=14)),
                )
'''
t = t[:start] + NEW + t[end:]

# 悬停能力探测：0.28 没有 animate_shadow，直接标记不支持，避免误判
OLD_PROBE = '''            _HOVER_OK = False
            try:
                ft.Container(on_hover=lambda e: None, animate_shadow=ft.Animation(150, ft.AnimationCurve.EASE_OUT))
                _HOVER_OK = True
            except BaseException as _be:
                _diag_log(_be, "L3305")

                _HOVER_OK = False'''
NEW_PROBE = '''            # Flet 0.28 的 Container 没有 animate_shadow，悬停动效不可用，直接关闭
            _HOVER_OK = False'''
if OLD_PROBE in t:
    t = t.replace(OLD_PROBE, NEW_PROBE, 1)
    print("悬停探测已简化")
else:
    print("!! 悬停探测未匹配（继续）")

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("主题块已重写")
