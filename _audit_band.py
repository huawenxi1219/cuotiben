# -*- coding: utf-8 -*-
"""手表背单词 App 审计：数据一致性、词表合理性。"""
import io, json, os, re

BASE = r"C:\Users\黄\Doubao\chats\2026-10-17\new-chat-1\band-word-app\vela-app\src"
C = os.path.join(BASE, "common")


def js_string(path):
    s = io.open(path, encoding="utf-8").read()
    m = re.search(r'export default\s+"((?:[^"\\]|\\.)*)"', s, re.S)
    return m.group(1) if m else ""


dict_raw = js_string(os.path.join(C, "dict.js"))
dict_raw = dict_raw.replace("\\n", "\n").replace("\\t", "\t")
lines = [x for x in dict_raw.split("\n") if x.strip()]

words, bad = [], []
for ln in lines:
    if "\t" in ln:
        w, m = ln.split("\t", 1)
        words.append((w.strip(), m.strip()))
    else:
        bad.append(ln[:40])

core = js_string(os.path.join(C, "core.js"))
hot = js_string(os.path.join(C, "hot.js"))

print("=== 1) 数据一致性 ===")
print(f"  词条数 {len(words)} | core {len(core)} | hot {len(hot)}")
print(f"  三者一致: {'✅' if len(words) == len(core) == len(hot) else '❌'}")
print(f"  坏行: {len(bad)}")

empty_m = [i for i, (w, m) in enumerate(words) if not m]
print(f"  空释义: {len(empty_m)}")

hot_idx = [i for i, ch in enumerate(hot) if ch == "1"]
core_idx = set(i for i, ch in enumerate(core) if ch == "1")
not_in_core = [i for i in hot_idx if i not in core_idx]
print(f"\n=== 2) hot 与 core ===")
print(f"  hot {len(hot_idx)} | core {len(core_idx)} | hot 越界 {len(not_in_core)} "
      f"{'✅' if not not_in_core else '❌'}")

print("\n=== 3) 680 词抽样（每 40 个取 1）===")
print("  " + " / ".join(words[i][0] for i in hot_idx[::40]))

too_basic = {"the", "of", "and", "to", "in", "a", "is", "are", "was", "were",
             "i", "you", "he", "she", "it", "we", "they", "this", "that", "not"}
hot_words = [words[i][0].lower() for i in hot_idx]
hit = [w for w in hot_words if w in too_basic]
print(f"\n=== 4) 基础虚词混入 ===")
print(f"  {hit if hit else '无 ✅'}")

should_have = ["achieve", "environment", "opportunity", "experience", "improve",
               "knowledge", "consider", "develop", "increase", "require", "suggest",
               "influence", "contribute", "significant", "evidence", "approach",
               "attitude", "benefit", "challenge", "consequence"]
hs = set(hot_words)
miss = [w for w in should_have if w not in hs]
print(f"\n=== 5) 应含高频实词缺失 ===")
print(f"  {miss if miss else '无 ✅'}")
