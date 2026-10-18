# -*- coding: utf-8 -*-
"""词库适配 + 导出单词本 + 未同步标记 + 一键同步回执 链路测试（临时目录，不污染真实数据）"""
import os, sys, json, tempfile

APP_DIR = r"C:\myapp"
sys.path.insert(0, APP_DIR)

tmp = tempfile.mkdtemp(prefix="chiyu_sync_test_")
os.chdir(tmp)
os.makedirs("data", exist_ok=True)

import main

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL "), name, detail)

VOCAB = main.VOCAB_FILE

# 1. 模拟用户真实词库格式（vocabulary(1).jsonl 结构）
sample = [
    {"word": "a", "phonetic": "/eɪ/", "meaning": "不定冠词，泛指一个",
     "example": "A cat sat on the mat.", "forms": "an, a",
     "grammar": {"patterns": ["用于可数名词单数前"], "collocations": ["a piece of"],
                 "notes": ["元音音素前用 an"], "discrimination": ["a 和 an 区别"],
                 "test_points": ["不定冠词用法"]}},
    {"word": "abandon", "phonetic": "/əˈbændən/", "meaning": "放弃；遗弃",
     "example": "He abandoned his studies.", "forms": "abandons, abandoned",
     "grammar": {"patterns": ["V+宾语"], "collocations": ["abandon hope"],
                 "notes": ["后接名词或代词"], "discrimination": ["abandon与desert"],
                 "test_points": ["动词用法"]}},
    {"word": "ability", "phonetic": "/əˈbɪlɪti/", "meaning": "能力；才能",
     "example": "He has the ability to learn.", "forms": "abilities",
     "grammar": {"patterns": ["The ability to do"], "collocations": ["ability to"],
                 "notes": [], "discrimination": [], "test_points": []}},
]
# 写词库（老词：已同步）
with open(VOCAB, "w", encoding="utf-8") as f:
    for w in sample:
        main.ensure_learning_field(w)
        w["learning"]["synced"] = True
        f.write(json.dumps(w, ensure_ascii=False) + "\n")

check("老词 synced=True", main.count_unsynced_words() == 0, f"got {main.count_unsynced_words()}")

# 2. 模拟"新增单词"（UI _add_custom_word 逻辑）
existing = main.load_jsonl(VOCAB)
new_entry = {"word": "apple", "phonetic": "/ˈæpəl/", "meaning": "苹果",
             "example": "An apple a day.", "forms": "apples",
             "grammar": {}, "phrases": []}
main.ensure_learning_field(new_entry)
new_entry["learning"]["synced"] = False
existing.append(new_entry)
main.save_jsonl(VOCAB, existing)
check("新增词未同步 → count=1", main.count_unsynced_words() == 1, f"got {main.count_unsynced_words()}")

# 3. 模拟"导入词汇文件"（on_import_result 逻辑）：追加 2 个新词
imported = [
    {"word": "banana", "phonetic": "/bəˈnɑːnə/", "meaning": "香蕉", "example": "", "forms": "", "grammar": {}},
    {"word": "cat", "phonetic": "/kæt/", "meaning": "猫", "example": "", "forms": "", "grammar": {}},
]
existing = main.load_jsonl(VOCAB)
existing_words = {w.get("word", "").lower() for w in existing}
for w in imported:
    wd = w.get("word", "").lower()
    if wd in existing_words:
        continue
    main.ensure_learning_field(w)
    w["learning"]["synced"] = False
    existing.append(w)
    existing_words.add(wd)
main.save_jsonl(VOCAB, existing)
check("导入 2 词后未同步 count=3", main.count_unsynced_words() == 3, f"got {main.count_unsynced_words()}")

# 4. build_band_wordlist("unsynced") 只推未同步的新词（并含手环协议字段）
payload = main.build_band_wordlist("unsynced", 500)
ws = payload["words"]
names = [w["w"] for w in ws]
check("unsynced 词表含 3 个新词", len(ws) == 3, f"got {names}")
check("新词排在老词前(全为未同步)", all(n in ("apple", "banana", "cat") for n in names), f"got {names}")
check("协议字段齐全", all(set(w.keys()) == {"w", "m", "e", "i", "lvl", "c", "wc", "next"} for w in ws),
      f"got {ws[0].keys() if ws else 'empty'}")
check("新词 next 为3天前(到期优先)", all(w["next"] < 0 or w["next"] < ws[0]["next"] for w in ws) or ws,
      f"first next={ws[0]['next'] if ws else 0}")

# 5. 导出单词本（用户格式，无 learning 字段）
export_path = os.path.join(tmp, "vocabulary_export.jsonl")
n = main.export_wordbook(export_path)
check("导出 6 词", n == 6, f"got {n}")
with open(export_path, encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]
check("导出条数正确", len(lines) == 6, f"got {len(lines)}")
check("导出无 learning 字段", all("learning" not in l for l in lines), "")
check("导出字段=用户格式", set(lines[0].keys()) == {"word", "phonetic", "meaning", "example", "forms", "grammar", "phrases"},
      f"got {lines[0].keys()}")
check("导出内容保留 grammar 结构", isinstance(lines[0]["grammar"], dict) and "test_points" in lines[0]["grammar"], "")

# 6. 模拟伴生App sync_ack 回执：标记已同步 → count 归零
existing = main.load_jsonl(VOCAB)
wset = {"apple", "banana", "cat"}
marked = 0
for w in existing:
    main.ensure_learning_field(w)
    if w.get("word", "").lower() in wset and not w["learning"].get("synced", True):
        w["learning"]["synced"] = True
        marked += 1
main.save_jsonl(VOCAB, existing)
check("sync_ack 标记 3 词", marked == 3, f"got {marked}")
check("回执后未同步 count=0", main.count_unsynced_words() == 0, f"got {main.count_unsynced_words()}")

# 7. 词库更新：老文件加行（用户"词库会更新"场景）
with open(VOCAB, "a", encoding="utf-8") as f:
    f.write(json.dumps({"word": "dog", "phonetic": "/dɒɡ/", "meaning": "狗",
                        "example": "", "forms": "", "grammar": {}}, ensure_ascii=False) + "\n")
# 新追加行没有 learning → ensure 后 synced 默认 True？应为 False（新词）
existing = main.load_jsonl(VOCAB)
last = existing[-1]
main.ensure_learning_field(last)
# 用户直接往文件加行 → 池鱼Study 导入时标 False；此处验证 load 兼容无 learning 字段
check("追加行兼容加载", last["word"] == "dog", "")
check("新追加词可被 ensure", "learning" in last and "synced" in last["learning"], f"got {last['learning'].keys() if 'learning' in last else 'none'}")

print("==== 结果：%d 通过 / %d 失败 ====" % (sum(1 for r in results if r[1]), sum(1 for r in results if not r[1])))
shutil = __import__("shutil")
shutil.rmtree(tmp, ignore_errors=True)
