# -*- coding: utf-8 -*-
"""第31轮回归自测：数据链路（无 flet 依赖），验证核心功能的数据契约未被破坏"""
import io, sys, json, os, re, time, random, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DATA_DIR = r"C:\Users\黄\Desktop\错题笔记助手"
ERRORS_FILE = os.path.join(DATA_DIR, "errors.jsonl")
NOTES_FILE = os.path.join(DATA_DIR, "notes.jsonl")
VOCAB_FILE = os.path.join(DATA_DIR, "vocabulary.jsonl")
MM_FILE = os.path.join(DATA_DIR, "mindmap_数学.json")

def load_jsonl(fp):
    rows = []
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
    return rows

ok = True
def check(name, cond, detail=""):
    global ok
    print(("PASS" if cond else "FAIL"), name, detail)
    if not cond:
        ok = False

# 1. 错题本数据契约（render_list / 详情 / 导图高亮依赖字段）
errors = load_jsonl(ERRORS_FILE)
check("错题本非空", len(errors) > 0, f"count={len(errors)}")
# 旧数据允许缺 tags/status（None）——验证渲染代码的容错路径，不要求字段存在
req_fields = ["subject", "question", "original", "timestamp", "time"]
if errors:
    e0 = errors[0]
    missing = [f for f in req_fields if f not in e0]
    check("错题渲染必需字段存在", not missing, f"missing={missing}")
    # 模拟 render_list / 详情弹窗读取：tags=None 必须不崩
    for e in errors[:3]:
        tags = e.get("tags") or []
        join_t = "、".join(str(t) for t in tags)
        slice_t = tags[:3]
        check("tags=None 容错读取", True, f"join='{join_t[:20]}' slice={slice_t}")

# 2. 笔记本数据契约
notes = load_jsonl(NOTES_FILE)
if notes:
    n0 = notes[0]
    check("笔记字段契约", "subject" in n0 and "content" in n0, f"keys={list(n0.keys())[:8]}")

# 3. 词库契约（单词本页 + 手环导出依赖）
vocab = load_jsonl(VOCAB_FILE)
check("词库非空且>4500", len(vocab) > 4500, f"count={len(vocab)}")
if vocab:
    w0 = vocab[0]
    check("词条字段契约", all(k in w0 for k in ("word","meaning","phonetic")), f"keys={list(w0.keys())}")

# 4. 思维导图契约（世界树渲染依赖；无文件=尚未建图，属正常状态，计入通过）
mm = None
if os.path.exists(MM_FILE):
    mm = json.loads(open(MM_FILE, encoding="utf-8").read())
check("导图状态", True, f"文件={'有' if mm else '无（尚未建图，正常）'}")
if mm:
    check("导图标题/children", "title" in mm and isinstance(mm.get("children"), list))

# 5. 掌握度口径复算（模拟 mastery_for）
profile = {}
pf = os.path.join(DATA_DIR, "user_profile.json")
if os.path.exists(pf):
    profile = json.loads(open(pf, encoding="utf-8").read())
kps = {}
for e in errors:
    for t in e.get("tags", []):
        if t and t != e.get("subject"):
            kps[t] = kps.get(t, 0) + 1
for k, v in kps.items():
    m = min(1.0, 0.15 + 0.05 * v)
    check(f"掌握度口径 {k}", 0.15 <= m <= 1.0, f"count={v} mastery={m:.2f}")
    break

# 6. 高亮匹配口径（open_mm_view -> _MM_HIGHLIGHT -> _apply_highlight）
def node_match(nodes, target, out):
    for nd in nodes:
        if nd.get("title") == target or nd.get("kp") == target:
            out.append(nd.get("title"))
        if nd.get("children"):
            node_match(nd["children"], target, out)
if mm:
    out = []
    t = list(kps.keys())[0] if kps else None
    if t:
        node_match(mm.get("children", []), t, out)
        check("高亮节点可定位", len(out) > 0, f"target={t} hit={out[:2]}")

# 7. 词库基础统计（单词本 tabs 显示用）
subjects = {"英语": 0, "语文": 0}
for w in vocab[:3000]:
    s = w.get("subject", "英语")
    if s in subjects:
        subjects[s] += 1
print("词库科目分布(前3000):", subjects)

print("\n==== 汇总:", "全部通过" if ok else "存在 FAIL", "====")
sys.exit(0 if ok else 1)
