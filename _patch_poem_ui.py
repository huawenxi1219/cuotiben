# -*- coding: utf-8 -*-
"""古诗词 App UI 调整：字号整体缩到 80%、角标按钮加大并内移、主界面支持右滑退出。"""
import glob, io, os, re

ROOT = r"C:\myapp\_poem\src\pages"
files = glob.glob(os.path.join(ROOT, "*", "*.ux"))

def scale_font(m):
    n = int(m.group(1))
    return "font-size: %dpx" % max(14, round(n * 0.8))

changed = []
for f in files:
    t = io.open(f, encoding="utf-8").read()
    orig = t
    t = re.sub(r"font-size:\s*(\d+)px", scale_font, t)

    # 角标按钮：内移 + 加大
    t = re.sub(r"(\.(?:back|about)\s*\{[^}]*?)left:\s*6?px", r"\1left: 18px", t, flags=re.S)
    t = re.sub(r"(\.(?:back|about)\s*\{[^}]*?)top:\s*6px", r"\1top: 14px", t, flags=re.S)
    t = re.sub(r"(\.(?:back|about)\s*\{[^}]*?)left:\s*258px", r"\1left: 230px", t, flags=re.S)
    t = re.sub(r"(\.(?:back|about)\s*\{[^}]*?)width:\s*72px", r"\1width: 88px", t, flags=re.S)
    t = re.sub(r"(\.(?:back|about)\s*\{[^}]*?)height:\s*72px", r"\1height: 88px", t, flags=re.S)

    if t != orig:
        io.open(f, "w", encoding="utf-8", newline="\n").write(t)
        changed.append(os.path.basename(f))

print("已调整:", changed)

# 主界面：右滑退出
p = os.path.join(ROOT, "index", "index.ux")
t = io.open(p, encoding="utf-8").read()
old = '''	ban() {
		console.log("ban");
	},'''
new = '''	ban(e) {
		// 右滑退出应用（主界面没有上一页）
		if (e && e.direction === "right") {
			this.$app.exit();
		}
	},'''
if old in t:
    t = t.replace(old, new)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    print("主界面右滑退出：已加入")
else:
    print("!! 未找到 ban()")
