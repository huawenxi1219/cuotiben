# -*- coding: utf-8 -*-
"""提取诗歌（修正边界）+ 修补已知错字/标点，生成修订后的 poem.ux。"""
import io, json, re

SRC = r"C:\myapp\_poem\src\pages\poem\poem.ux"
raw = io.open(SRC, encoding="utf-8").read()

# ---------- 1) 正确提取 ----------
body = raw[raw.index("onInit()"):]
parts = body.split('this.text === "')
poems = []
for seg in parts[1:]:
    title = seg.split('"', 1)[0]
    if "this.poem" not in seg:
        continue
    after = seg.split("this.poem", 1)[1]
    # 到下一个 else if / const / 收尾 为止
    cut = len(after)
    for marker in ("\n    const ", "\n    else if", "\n  }", "\n    updateTime"):
        k = after.find(marker)
        if k != -1:
            cut = min(cut, k)
    chunk = after[:cut]
    lits = re.findall(r'"((?:[^"\\]|\\.)*)"', chunk)
    text = "".join(lits).replace("\\n", "\n")
    author = ""
    m = re.search(r'this\.people\s*=\s*"([^"]*)"', seg)
    if m:
        author = m.group(1)
    poems.append({"title": title, "author": author, "text": text})

print("诗歌数:", len(poems), "总字数:", sum(len(p["text"]) for p in poems))
io.open(r"C:\myapp\_poems.json", "w", encoding="utf-8").write(
    json.dumps(poems, ensure_ascii=False, indent=1))

# ---------- 2) 修补 ----------
FIXES = [
    # 错字
    ("子曰：“朝闻道，夕死可矣.”", "子曰：“朝闻道，夕死可矣。”"),
    ("子日：", "子曰："),
    # 半角标点
    ("何也?夫在殷忧", "何也？夫在殷忧"),
    ("嗟乎!师道之不传", "嗟乎！师道之不传"),
    ("难矣!古之圣人", "难矣！古之圣人"),
    ("自矜者不长.", "自矜者不长。"),
    ("固拙于用大矣!宋人", "固拙于用大矣！宋人"),
    ("闷杀人也么哥?", "闷杀人也么哥？"),
]

patched = raw
applied = []
for old, new in FIXES:
    if old in patched:
        patched = patched.replace(old, new)
        applied.append(new[:14])

print("应用修补:", len(applied), applied)

io.open(SRC, "w", encoding="utf-8", newline="\n").write(patched)
print("poem.ux 已更新，长度", len(patched))
