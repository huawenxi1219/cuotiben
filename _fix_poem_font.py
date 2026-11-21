# -*- coding: utf-8 -*-
"""古诗词：清除正文里多余的空格、字号加大到 34。"""
import io, re

P = r"C:\myapp\_poem\src\pages\poem\poem.ux"
t = io.open(P, encoding="utf-8").read()

# 1) 只处理 onInit 里的诗歌文本段
start = t.index("onInit()")
end = t.index("const updateTime", start)
seg = t[start:end]

CJK = r"\u4e00-\u9fff\u3000-\u303f\uff00-\uffef“”‘’"
# 空格两侧都是中文/中文标点/换行转义时删掉
pattern = re.compile(r"(?<=[" + CJK + r"])[ \t]+(?=[" + CJK + r"\\]|\n)")
new_seg = pattern.sub("", seg)
# 顺带把「\n空格」这种行首空格去掉
new_seg = re.sub(r"\\n[ \t]+(?=[\u4e00-\u9fff“”])", r"\\n", new_seg)

removed = len(seg) - len(new_seg)
t = t[:start] + new_seg + t[end:]

# 2) 字号加大
t = t.replace(""".b {
  font-size: 30px;
  line-height: 48px;""", """.b {
  font-size: 34px;
  line-height: 54px;
  letter-spacing: 0px;""", 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(t)
print("删除空格字符:", removed, "| 字号 30 → 34")
