# -*- coding: utf-8 -*-
"""CI：给 flet build 命令加开屏底色参数。"""
import io

P = r"C:\myapp\.github\workflows\build.yml"
t = io.open(P, encoding="utf-8").read()

if "--splash-color" in t:
    print("已存在，跳过")
    raise SystemExit(0)

OLD = "            if flet build apk \\\n"
NEW = ("            if flet build apk \\\n"
       "              --splash-color \"#FEFCF6\" \\\n"
       "              --splash-dark-color \"#FEFCF6\" \\\n")

assert OLD in t, "找不到 build 命令行"
t = t.replace(OLD, NEW, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("已加入 splash 底色参数")
