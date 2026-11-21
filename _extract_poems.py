# -*- coding: utf-8 -*-
"""抽取诗歌 + 找出可疑字符（半角标点、日/曰、己/已/巳 等常见错字）。"""
import io, json, re

SRC = r"C:\myapp\_poem\src\pages\poem\poem.ux"
txt = io.open(SRC, encoding="utf-8").read()

start = txt.index("onInit()")
body = txt[start:]

parts = body.split('this.text === "')
poems = []
for seg in parts[1:]:
    title = seg.split('"', 1)[0]
    if "this.poem" not in seg:
        continue
    after = seg.split("this.poem", 1)[1]
    lits = re.findall(r'"((?:[^"\\]|\\.)*)"', after)
    if not lits:
        continue
    text = "".join(lits).replace("\\n", "\n").replace('\\"', '"')
    author = ""
    m = re.search(r'this\.people\s*=\s*"([^"]*)"', seg)
    if m:
        author = m.group(1)
    poems.append({"title": title, "author": author, "text": text})

io.open(r"C:\myapp\_poems.json", "w", encoding="utf-8").write(
    json.dumps(poems, ensure_ascii=False, indent=1))
print("诗歌数:", len(poems), "总字数:", sum(len(p["text"]) for p in poems))
print("空正文:", [p["title"] for p in poems if not p["text"].strip()])

# ---- 可疑点扫描 ----
print("\n=== 半角标点（中文里不该出现） ===")
half = re.compile(r"[,.!?;:]")
for p in poems:
    for i, ch in enumerate(p["text"]):
        if half.match(ch):
            ctx = p["text"][max(0, i - 6):i + 6].replace("\n", " ")
            print(f"  {p['title']}: ...{ctx}...")
            break

print("\n=== 疑似错字（日/曰、己/已/巳、未/末、茶/荼 等） ===")
pairs = [("子日", "子曰"), ("日：", "曰："), ("己经", "已经"), ("以经", "已经"),
         ("未来", "未来"), ("末来", "未来"), ("侯", "候"), ("但", "担")]
for p in poems:
    for bad, good in pairs:
        if bad in p["text"]:
            print(f"  {p['title']}: 含「{bad}」（可能应为「{good}」）")

print("\n=== 重复字符 ===")
for p in poems:
    for m in re.finditer(r"(.)\1", p["text"]):
        ch = m.group(1)
        if ch in "，。！？；：、“”\n ":
            continue
        i = m.start()
        print(f"  {p['title']}: ...{p['text'][max(0,i-5):i+7]}...")
