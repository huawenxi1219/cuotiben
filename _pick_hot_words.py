# -*- coding: utf-8 -*-
"""生成「高频核心 680」层级：排除虚词/专有名词，按语料词频挑 680 个。
   同时输出手表用的 hot.js（长度与 dict.js 对齐）。"""
import io, json

VOCAB = r"C:\myapp\data\vocabulary.jsonl"
FREQ = r"C:\myapp\_freq.txt"
HOT_JS = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app\src\common\hot.js"
DICT_JS = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app\src\common\dict.js"
TARGET = 680

SKIP = {
    # 月份
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    # 星期
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    # 国家/地名
    "china", "chinese", "america", "american", "england", "english", "britain",
    "british", "india", "canada", "australia", "japan", "japanese", "france",
    "french", "german", "germany", "russia", "london", "paris", "new york",
    "europe", "european", "asia", "africa", "african",
    # 商业/科技杂词
    "customer", "credit", "sale", "corporation", "license", "studio", "rent",
    "remote", "web", "website", "internet", "email", "online", "software",
    "computer", "digital", "phone", "mobile",
}

freq = {}
for rank, line in enumerate(io.open(FREQ, encoding="utf-8"), start=1):
    w = line.strip().lower()
    if w and w not in freq:
        freq[w] = rank


def rank_of(word):
    w = word.strip().lower()
    if w in freq:
        return freq[w]
    parts = [p for p in w.split() if p]
    rs = [freq.get(p) for p in parts]
    return max(rs) if rs and all(r is not None for r in rs) else 10 ** 6


rows = [json.loads(l) for l in io.open(VOCAB + ".bak", encoding="utf-8") if l.strip()]
core = [r for r in rows if r.get("core")]

cand = [r for r in core
        if rank_of(r["word"]) > 400 and r["word"].strip().lower() not in SKIP]
cand.sort(key=lambda r: rank_of(r["word"]))
hot_words = [r["word"] for r in cand[:TARGET]]
hot_set = set(hot_words)

for r in rows:
    r["hot"] = 1 if r["word"] in hot_set else 0

with io.open(VOCAB, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# 校验 dict.js 顺序与 jsonl 一致（取前 3 个词）
dict_head = [l.split("\t")[0] for l in io.open(DICT_JS, encoding="utf-8").read().splitlines()[:3]]
vocab_head = [r["word"] for r in rows[:3]]
print("dict.js 前 3:", dict_head)
print("vocab 前 3 :", vocab_head)
same = dict_head == vocab_head
print("顺序一致:", same)

flags = "".join("1" if r.get("hot") else "0" for r in rows)
io.open(HOT_JS, "w", encoding="utf-8", newline="\n").write(
    "// 高频核心 680 标记：1=是，0=否\nexport default \"%s\"\n" % flags)

print(f"hot 数量: {flags.count('1')} | hot.js 长度: {len(flags)}")
print("样本:", hot_words[:12], "...", hot_words[-6:])
