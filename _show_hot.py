# -*- coding: utf-8 -*-
"""打印新的核心 680 词抽样，供人工判断质量。"""
import io, json, random, re

HOT = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app\src\common\hot.js"
VOCAB = r"C:\myapp\data\vocabulary.jsonl"

hot = re.search(r'export default "([01]+)"', io.open(HOT, encoding="utf-8").read()).group(1)
rows = [json.loads(l) for l in io.open(VOCAB, encoding="utf-8") if l.strip()]
words = [r["word"] for i, r in enumerate(rows) if hot[i] == "1"]
print("核心 680 共", len(words), "个")
random.seed(11)
print("\n随机 60 个：")
print("、".join(random.sample(words, 60)))
print("\n前 40 个（真题频次最高）：")
print("、".join(words[:40]))
