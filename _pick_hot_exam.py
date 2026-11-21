# -*- coding: utf-8 -*-
"""用高考真题词频重挑「核心 680」：
   1) 数据来自 HK-SHAO/English-Spider 对 43 份真题的统计 (data.csv)
   2) 排除基础虚词，按真题出现频次排序，取 680
   3) 输出 hot.js
"""
import io, json, os, re

VOCAB = r"C:\myapp\data\vocabulary.jsonl"
FREQ = r"C:\myapp\_gk\data.csv"
HOT_JS = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app\src\common\hot.js"
TARGET = 680

# 1) 真题词频
raw = {}
for line in io.open(FREQ, encoding="utf-8"):
    parts = line.strip().split(",")
    if len(parts) >= 2 and parts[0].isalpha():
        raw[parts[0].lower()] = int(parts[1])
print("真题词频条目:", len(raw))

# 2) 基础虚词/超高频词（这些不算"核心词汇"）
BASIC = set("""
a an the of to in on at by for with from as into about over after before
and or but so if because although while when where what which who whom whose why how that this these those
i you he she it we they me him her us them my your his its our their
is am are was were be been being do does did done have has had having will would shall should can could may might must
not no nor none very too also just only even still yet then than there here
one two three four five six seven eight nine ten first second last next
more most much many some any all both each every few little less least
up down out off back again ever never always often sometimes usually
s t d ll re ve m don didn doesn isn aren wasn weren won couldn wouldn shouldn
people time year day way thing man woman child world life hand part place work
new old good bad big small long high low right left same other another such own
get got make made take took come came go went see saw know knew think thought
say said tell told give gave find found put use used want need like look
theirs yours ours hers mine its oneself himself herself itself themselves ourselves yourself
mr mrs ms miss sir madam ok okay yes yeah oh ah well now
""".split())

# 3) 词形还原（粗）：复数/过去式/进行时/比较级
def variants(w):
    out = {w}
    if w.endswith("ies"):
        out.add(w[:-3] + "y")
    if w.endswith("es"):
        out.add(w[:-2])
    if w.endswith("s"):
        out.add(w[:-1])
    if w.endswith("ed"):
        out.add(w[:-2]); out.add(w[:-1])
    if w.endswith("ing"):
        out.add(w[:-3]); out.add(w[:-3] + "e")
    if w.endswith("er"):
        out.add(w[:-2]); out.add(w[:-1])
    if w.endswith("est"):
        out.add(w[:-3])
    return out

SKIP_GEO = {"antarctica", "africa", "african", "america", "american", "asia", "europe",
            "european", "britain", "british", "england", "english", "china", "chinese",
            "india", "canada", "australia", "japan", "japanese", "france", "french",
            "germany", "german", "russia", "london", "paris", "tokyo", "new york", "spain",
            "spanish", "italy", "italian", "swiss", "switzerland", "tibet", "tibetan"}

rows = [json.loads(l) for l in io.open(VOCAB, encoding="utf-8") if l.strip()]
core = [r for r in rows if r.get("core")]
print("核心词:", len(core))

def freq_of(word):
    w = word.strip().lower()
    if " " in w:   # 短语：取各词频次的最小值，避免虚高
        parts = [p for p in w.split() if p]
        fs = [raw.get(p, 0) for p in parts]
        return min(fs) if fs and all(fs) else 0
    best = 0
    for v in variants(w):
        best = max(best, raw.get(v, 0))
    return best

scored = [(freq_of(r["word"]), r["word"]) for r in core]
scored.sort(key=lambda x: -x[0])

# 排除虚词、纯冠词等，取前 680
def stem(w):
    w = w.lower()
    for suf in ("ing", "ed", "es", "s", "er", "est"):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return w[: -len(suf)]
    return w

picked, seen_stems = [], set()
for f, w in scored:
    if w.lower() in BASIC or w.lower() in SKIP_GEO:
        continue
    if f <= 0:
        continue
    st = stem(w)
    # 派生词若词根是基础词（work/think/write/found...），也不算核心
    if st in BASIC:
        continue
    if st in seen_stems and len(w.split()) == 1:
        continue
    seen_stems.add(st)
    picked.append((f, w))
    if len(picked) >= TARGET:
        break

print("入选:", len(picked))
print("样本前 20:", [w for _, w in picked[:20]])
print("样本中段:", [w for _, w in picked[300:315]])
print("样本末 10:", [w for _, w in picked[-10:]])

# 4) 检查高价值词
hs = set(w.lower() for _, w in picked)
must = ["achieve", "opportunity", "suggest", "influence", "contribute", "significant",
        "attitude", "challenge", "consequence", "environment", "experience", "improve"]
print("应含缺失:", [w for w in must if w not in hs] or "无")
print("混入的怪词:", [w for w in ["christmas card", "death", "plus", "thing", "variety"] if w in hs] or "无")

# 5) 写 hot.js
hot_set = set(w for _, w in picked)
flags = "".join("1" if (r.get("core") and r["word"] in hot_set) else "0" for r in rows)
io.open(HOT_JS, "w", encoding="utf-8", newline="\n").write(
    "// 高频核心 680（基于 43 份高考真题词频）\nexport default \"%s\"\n" % flags)
print("hot.js 已更新，hot 数:", flags.count("1"), "长度:", len(flags))
