# -*- coding: utf-8 -*-
"""重做开屏图：奶白背景 + 插画缩小居中（圆角卡片感），避免"突然一张图"。"""
import io
from PIL import Image, ImageDraw, ImageFilter

SRC = r"C:\myapp\assets\splash.png"
BACKUP = r"C:\myapp\assets\splash_original.png"

im = Image.open(SRC).convert("RGB")
W, H = im.size
print("原图:", W, H)

if not io.open(BACKUP, "wb"):
    pass
try:
    Image.open(BACKUP)
except Exception:
    im.save(BACKUP)
    print("已备份原图 ->", BACKUP)

# 取画面底部中央的颜色作为奶白底色
cream = im.getpixel((W // 2, int(H * 0.97)))
print("取样底色:", cream)
# 稍微提亮一点，保证干净
cream = tuple(min(255, int(c * 0.35 + 255 * 0.65)) for c in cream)
print("使用底色:", cream)

canvas = Image.new("RGB", (W, H), cream)

# 插画缩到 76% 高度
scale = 0.76
ih = int(H * scale)
iw = int(ih * W / H)
art = im.resize((iw, ih), Image.LANCZOS)

# 圆角
radius = int(min(iw, ih) * 0.035)
mask = Image.new("L", (iw, ih), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, iw - 1, ih - 1], radius=radius, fill=255)

# 柔和阴影
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sh = Image.new("L", (iw, ih), 0)
ImageDraw.Draw(sh).rounded_rectangle([0, 0, iw - 1, ih - 1], radius=radius, fill=60)
shadow.paste((120, 110, 90, 60), ((W - iw) // 2 + 4, (H - ih) // 2 + 10), sh)
shadow = shadow.filter(ImageFilter.GaussianBlur(18))
canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB")

pos = ((W - iw) // 2, (H - ih) // 2)
canvas.paste(art, pos, mask)
canvas.save(SRC, optimize=True)
print("已生成新开屏图:", SRC, canvas.size)
print("插画尺寸:", (iw, ih), "上下留白:", pos[1], "px")
