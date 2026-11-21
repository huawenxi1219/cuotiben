# -*- coding: utf-8 -*-
"""18 项修复的模块级冒烟测试（UI 闭包内的逻辑无法脱离页面调用，这里覆盖可独立验证的部分）。
用法：在任意临时目录运行本脚本（或直接运行，脚本内部自动切到临时数据目录，不污染真实数据）。"""
import os
import sys
import time
import tempfile

_tmp = tempfile.mkdtemp(prefix="chiyu_smoke18_")
os.chdir(_tmp)
import main  # noqa: E402  (DATA_DIR 将指向临时目录下的 data)

fails = []


def check(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("  [" + str(extra) + "]" if extra else ""))
    if not cond:
        fails.append(name)


# ---- P1-7 DeepSeek 模型名统一（含旧名兜底） ----
check("resolve 默认值", main.resolve_deepseek_model({}) == "deepseek-flash")
check("resolve deepseek-flash 原样", main.resolve_deepseek_model({"deepseek_model": "deepseek-flash"}) == "deepseek-flash")
check("resolve v4-flash 归一化", main.resolve_deepseek_model({"deepseek_model": "deepseek-v4-flash"}) == "deepseek-flash")
check("resolve deepseek-chat 归一化", main.resolve_deepseek_model({"deepseek_model": "deepseek-chat"}) == "deepseek-flash")

# ---- P1-6 高考倒计时非负 + 可配置 ----
dl = main.get_gaokao_days_left()
check("高考倒计时默认非负", isinstance(dl, int) and dl >= 0, dl)
main.save_ai_config({**main.load_ai_config(), "gaokao_date": "2027-06-07"})
dl2 = main.get_gaokao_days_left()
check("高考倒计时读配置日期", isinstance(dl2, int) and dl2 >= 0, dl2)
main.save_ai_config({**main.load_ai_config(), "gaokao_date": "2020-01-01"})
dl3 = main.get_gaokao_days_left()
check("过期日期不回负数", isinstance(dl3, int) and dl3 >= 0, dl3)

# ---- P0-1 copy_file_to_lib 返回相对路径 ----
os.makedirs(main.DATA_DIR, exist_ok=True)
_src = os.path.join(_tmp, "t.png")
with open(_src, "wb") as f:
    f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
_rel = main.copy_file_to_lib(_src, main.IMAGES_DIR, main.IMG_EXTS)
check("copy 返回相对路径", bool(_rel) and not os.path.isabs(_rel), _rel)
_full = os.path.join(main.DATA_DIR, _rel)
check("相对路径能解析到真实文件", os.path.exists(_full))

# ---- P0-4 save_note 补 event_id + 毫秒 timestamp ----
main.save_note("数学", "冒烟测试笔记", [])
_notes = main.load_jsonl(main.NOTES_FILE)
_n = _notes[-1] if _notes else {}
check("笔记带 event_id", bool(_n.get("event_id")))
check("笔记 timestamp 为毫秒级", isinstance(_n.get("timestamp", 0), int) and _n.get("timestamp", 0) > 10 ** 12,
      _n.get("timestamp"))

# ---- P1-10 词库读写锁存在 ----
check("_vocab_rw_lock 已定义", hasattr(main, "_vocab_rw_lock"))

# ---- P1-13 本地加权搜索返回 (有序列表, 索引映射) 可被预筛使用 ----
_errs = [{"original": "求导数 f(x)=x^2", "subject": "数学"},
         {"original": "勾股定理证明", "subject": "数学"},
         {"original": "二次函数图像", "subject": "数学"}]
_ordered, _score = main.weighted_search_errors(_errs, "导数")
check("weighted_search_errors 返回可预筛结构", isinstance(_ordered, list) and len(_ordered) <= len(_errs))

# ---- P0-3 恢复用到的校验函数路径：损坏 jsonl 必须可被识别（模拟 _validate 逻辑） ----
def _validate_jsonl(fp):
    import json
    with open(fp, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                json.loads(line)

_bad = os.path.join(main.DATA_DIR, "bad.jsonl")
with open(_bad, "w", encoding="utf-8") as f:
    f.write('{"a": 1}\n{"broken": }\n')
try:
    _validate_jsonl(_bad)
    check("损坏 jsonl 能被校验拦截", False)
except Exception:
    check("损坏 jsonl 能被校验拦截", True)
_good = os.path.join(main.DATA_DIR, "good.jsonl")
with open(_good, "w", encoding="utf-8") as f:
    f.write('{"a": 1}\n{"b": 2}\n')
try:
    _validate_jsonl(_good)
    check("正常 jsonl 通过校验", True)
except Exception:
    check("正常 jsonl 通过校验", False)

# ---- R2-P1-6 词库写锁并发验证：两线程各写 200 词，结束后词数与学习记录正确 ----
import threading as _th

words = [f"cw{i:03d}" for i in range(400)]
_seed = [{"word": w, "phonetic": "", "meaning": "", "example": "", "forms": "",
          "grammar": {}, "phrases": [], "event_id": main.gen_uid(),
          "learning": main.ensure_learning_field({"learning": {}})["learning"]} for w in words]
main.save_jsonl(main.VOCAB_FILE, _seed)


def _worker(wl):
    for wd in wl:
        main.update_word_learning(wd, "know")


_t1 = _th.Thread(target=_worker, args=(words[:200],))
_t2 = _th.Thread(target=_worker, args=(words[200:],))
_t1.start(); _t2.start(); _t1.join(); _t2.join()
_after = {w.get("word", "").lower(): w for w in main.load_jsonl(main.VOCAB_FILE)}
check("R2-P1-6 并发写词数=400", len(_after) == 400, len(_after))
check("R2-P1-6 并发写无丢失", all(w in _after for w in words))
check("R2-P1-6 并发写学习记录正确",
      all(_after[w].get("learning", {}).get("review_count") == 1 for w in words))

print("")
if fails:
    print(f"==== 结果：{len(fails)} 项失败 / {fails} ====")
    sys.exit(1)
else:
    print("==== 结果：冒烟测试全部通过 ====")
    sys.exit(0)
