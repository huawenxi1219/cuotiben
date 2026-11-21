# -*- coding: utf-8 -*-
"""把 App 里的 72 篇与「高考必背 60 篇」权威文本逐字对比，输出去别报告。"""
import io, json, re, difflib

app = json.load(io.open(r"C:\myapp\_poems.json", encoding="utf-8"))
ref = json.load(io.open(r"C:\myapp\_ref60\poetry.json", encoding="utf-8"))

PUNCT = "，。！？；：、“”‘’《》〈〉（）()【】…—·,.!?;:\"' \n\r\t"

def norm(s):
    s = re.sub(r"\[[^\]]*\]", "", str(s or ""))   # 去注音/夹注
    return "".join(ch for ch in s if ch not in PUNCT)

def key(t):
    t = str(t or "")
    t = t.replace("《", "").replace("》", "")
    t = re.sub(r"（.*?）|\(.*?\)|节选|选段", "", t)
    return t.strip()

refmap = {}
for r in ref:
    refmap[key(r["title"])] = r

matched, unmatched = [], []
for p in app:
    k = key(p["title"])
    r = refmap.get(k)
    if not r:
        # 模糊匹配
        for rk, rv in refmap.items():
            if rk and (rk in k or k in rk):
                r = rv
                break
    if r:
        matched.append((p, r))
    else:
        unmatched.append(p)

print(f"匹配到权威文本: {len(matched)} / {len(app)}")
print("未匹配:", [p["title"] for p in unmatched])

out = []
for p, r in matched:
    a, b = norm(p["text"]), norm(r["content"])
    if a == b:
        continue
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    diffs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        ctx = a[max(0, i1 - 6):i1]
        diffs.append({
            "tag": tag,
            "app": a[i1:i2],
            "ref": b[j1:j2],
            "ctx": ctx,
        })
    out.append({"title": p["title"], "diffs": diffs})

print(f"\n有差异的篇目: {len(out)}")
for o in out:
    print(f"\n### {o['title']}  （{len(o['diffs'])} 处）")
    for d in o["diffs"][:12]:
        print(f"   ...{d['ctx']}[{d['app'] or '∅'}]  vs  [{d['ref'] or '∅'}]")

json.dump([{"title": o["title"], "diffs": o["diffs"]} for o in out],
          io.open(r"C:\myapp\_poem_diff.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
