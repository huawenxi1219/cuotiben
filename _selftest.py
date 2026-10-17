# -*- coding: utf-8 -*-
"""main.py 改动功能的快速自检脚本（不启动 GUI）。
用法：在任意临时目录下运行本脚本，DATA_DIR 会指向临时目录，不污染真实数据。
"""
import os, sys, json, tempfile, shutil, time

APP_DIR = r"C:\myapp"
sys.path.insert(0, APP_DIR)

tmp = tempfile.mkdtemp(prefix="chiyu_selftest_")
os.chdir(tmp)

import main

results = []

def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL "), name, detail)

# 1. build_ctx 上下文构建
h = [{"role": "user", "content": "第%d条消息内容" % i} for i in range(50)]
ctx = main.build_ctx(h, max_chars=20000)
check("build_ctx 数量", len(ctx) >= 30, f"got {len(ctx)}")
check("build_ctx 正序", ctx and ctx[0]["content"].startswith("第0条"), ctx[0]["content"][:10] if ctx else "")
cap = main.build_ctx([{"role": "user", "content": "x" * 5000}], per_msg_cap=800)
check("build_ctx 截断", cap and len(cap[0]["content"]) <= 800, f"len={len(cap[0]['content']) if cap else 0}")

# 2. SRS update_word_learning（时间记录 + 精密算法）
vocab = [{"word": "apple", "phonetic": "", "meaning": "苹果", "example": "", "forms": "", "grammar": {}, "phrases": []}]
main.ensure_learning_field(vocab[0])
main.save_jsonl(main.VOCAB_FILE, vocab)
main.update_word_learning("apple", "know")
L = main.load_jsonl(main.VOCAB_FILE)[0]["learning"]
check("首次认识 interval=1", L.get("interval") == 1, f"interval={L.get('interval')}")
check("ease 系数记录", isinstance(L.get("ease"), (int, float)) and L.get("ease") >= 2.5, f"ease={L.get('ease')}")
check("历史记录1条", len(L.get("history", [])) == 1 and L["history"][0]["action"] == "know", str(L.get("history")))
check("选择时间已记录", len(L["history"][0].get("time", "")) == 19, repr(L["history"][0].get("time", "")))
main.update_word_learning("apple", "know")
L = main.load_jsonl(main.VOCAB_FILE)[0]["learning"]
check("第二次认识 interval=3", L.get("interval") == 3, f"interval={L.get('interval')}")
main.update_word_learning("apple", "forget")
L = main.load_jsonl(main.VOCAB_FILE)[0]["learning"]
check("答错 interval 重置=1", L.get("interval") == 1, f"interval={L.get('interval')}")
check("答错 ease 下降", L.get("ease") < 2.7, f"ease={L.get('ease')}")
check("历史记录3条", len(L.get("history", [])) == 3, f"len={len(L.get('history', []))}")

# 3. 图表：extract_chart_block / render / save_svg_chart
text = "下面是结果\n```chart\n{\"type\":\"bar\",\"title\":\"测试\",\"labels\":[\"A\",\"B\"],\"values\":[1,2],\"unit\":\"%\"}\n```\n结束"
clean, svg = main.extract_chart_block(text)
check("extract_chart 提取SVG", svg is not None and "<svg" in svg, f"len={len(svg) if svg else 0}")
check("extract_chart 去块", "chart" not in clean, clean[:30])
p = main.save_svg_chart(svg)
check("save_svg_chart 存文件", p and os.path.exists(p) and os.path.getsize(p) > 50, str(p))
spec = json.loads('{"type":"pie","title":"占比","items":[{"name":"A","value":10},{"name":"B","value":20}]}')
svg2 = main.render_chart_from_spec(spec)
check("render pie 正常", svg2 and "<svg" in svg2, f"len={len(svg2) if svg2 else 0}")

# 4. 手环词表导出 build_band_wordlist
# apple 现状：level=0, interval=1, 明天到期；新增 banana 为新词（应标记为到期优先）
vocab2 = main.load_jsonl(main.VOCAB_FILE)
if not any(w.get("word") == "banana" for w in vocab2):
    vocab2.append({"word": "banana", "meaning": "香蕉"})
main.ensure_learning_field(vocab2[-1])
main.save_jsonl(main.VOCAB_FILE, vocab2)
wl = main.build_band_wordlist("due", 50)
check("词表含2词", len(wl["words"]) == 2, f"len={len(wl['words'])}")
check("词表协议字段", all(k in wl["words"][0] for k in ("w", "m", "e", "i", "lvl", "c", "wc", "next")), str(wl["words"][0].keys()))
nxt_b = [x for x in wl["words"] if x["w"] == "banana"][0]["next"]
now_ms = int(time.time() * 1000)
check("新词导出为到期(3天前)", now_ms - nxt_b > 2 * main.BAND_DAY_MS, f"距今 {(now_ms - nxt_b) / main.BAND_DAY_MS:.1f} 天")
check("due模式到期词排前", wl["words"][0]["w"] == "banana", wl["words"][0]["w"])

# 5. 手环记录回收 merge_band_records
recs = [
    {"word": "apple", "action": "know", "t": "2026-10-18 10:00:00"},
    {"word": "apple", "action": "know", "t": "2026-10-18 10:00:00"},   # 重复 → 应去重
    {"word": "banana", "action": "forget", "t": "2026-10-18 10:05:00"},
    {"word": "banana", "action": "forget", "t": "2026-10-18 10:06:00"},  # 连续错 2 次
]
merged, updated, new_due, bad = main.merge_band_records(recs)
check("回收3条(去重1)", merged == 3, f"merged={merged}")
check("更新2个词", updated == 2, f"updated={updated}")
check("新增待复习计数正常", isinstance(new_due, int) and new_due >= 0, f"new_due={new_due}")
check("连续错词提醒 banana", bad == ["banana"], str(bad))
Lb = [w for w in main.load_jsonl(main.VOCAB_FILE) if w["word"] == "banana"][0]["learning"]
check("合并后 banana 重置学习", Lb.get("status") == "learning" and Lb.get("interval") == 1, f"interval={Lb.get('interval')}")

# 6. 清理临时目录
try:
    shutil.rmtree(tmp, ignore_errors=True)
except Exception:
    pass

fails = [r for r in results if not r[1]]
print("\n==== 结果：%d 通过 / %d 失败 ====" % (len(results) - len(fails), len(fails)))
for f in fails:
    print("FAILED:", f[0], f[2])
sys.exit(1 if fails else 0)
