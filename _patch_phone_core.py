# -*- coding: utf-8 -*-
"""手机端 v2：词库标注「高考核心 / 扩展」，并在列表与详情里显示。"""
import io, json, os

VOCAB = r"C:\myapp\data\vocabulary.jsonl"
MAIN = r"C:\myapp\main.py"
CORE_MAP = r"C:\myapp\_core_map.json"

# ---------- 1) 数据：给 4678 条加上 core 字段 ----------
data = json.load(open(CORE_MAP, encoding="utf-8"))
core = set(w.lower().strip() for w in data["core"])

rows = []
added = 0
with io.open(VOCAB, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        tag = 1 if (o.get("word", "").lower().strip() in core) else 0
        if "core" not in o:
            added += 1
        o["core"] = tag
        rows.append(o)

with io.open(VOCAB, "w", encoding="utf-8", newline="\n") as f:
    for o in rows:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")

n_core = sum(1 for o in rows if o["core"] == 1)
print("词库条目", len(rows), "核心", n_core, "扩展", len(rows) - n_core, "新增字段", added)

# ---------- 2) 代码：列表与详情显示标记 ----------
t = io.open(MAIN, encoding="utf-8").read()

# 2.1 列表行：标题前加标记，副标题前加范围
OLD = """                            word = w.get("word", "")
                            phonetic = w.get("phonetic", "")
                            meaning_short = w.get("meaning", "")[:50]
                            is_new = word in nw_set"""
NEW = """                            word = w.get("word", "")
                            phonetic = w.get("phonetic", "")
                            meaning_short = w.get("meaning", "")[:50]
                            is_new = word in nw_set
                            _scope = "核心" if w.get("core") == 1 else "扩展\""""
if OLD not in t:
    raise SystemExit("!! 列表段落未匹配")
t = t.replace(OLD, NEW)

OLD = """                                title=ft.Text(f"{word}  {phonetic}", size=15),
                                subtitle=ft.Text(meaning_short, size=12, color=ft.Colors.GREY_400),"""
NEW = """                                title=ft.Text(f"{'◆ ' if w.get('core') == 1 else ''}{word}  {phonetic}", size=15),
                                subtitle=ft.Text(f"[{_scope}] {meaning_short}", size=12,
                                                color="#7AA2F7" if w.get("core") == 1 else ft.Colors.GREY_400),"""
if OLD not in t:
    raise SystemExit("!! 列表行未匹配")
t = t.replace(OLD, NEW)

# 2.2 详情页：标题下加范围标签
OLD = """                content_children.append(ft.Text(f"📖 {word}", size=24, weight=ft.FontWeight.BOLD))
                if phonetic:"""
NEW = """                content_children.append(ft.Text(f"📖 {word}", size=24, weight=ft.FontWeight.BOLD))
                if word_data.get("core") is not None:
                    _is_core = word_data.get("core") == 1
                    content_children.append(ft.Container(
                        content=ft.Text("🎯 高考核心词" if _is_core else "📎 扩展词",
                                        size=13, weight=ft.FontWeight.BOLD,
                                        color="#7AA2F7" if _is_core else "#E0AF68"),
                        padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                        border_radius=10,
                        bgcolor="#1F2A44" if _is_core else "#3A2F22"))
                if phonetic:"""
if OLD not in t:
    raise SystemExit("!! 详情段落未匹配")
t = t.replace(OLD, NEW)

# 2.3 顶部计数加上核心/扩展
OLD = """                    count_text = ft.Text(f"共 {len(all_words)} 词", size=13, color=ft.Colors.GREY_500)"""
NEW = """                    _core_n = sum(1 for w in all_words if w.get("core") == 1)
                    _extra_n = len(all_words) - _core_n
                    _scope_info = f" · 核心 {_core_n} / 扩展 {_extra_n}"
                    count_text = ft.Text(f"共 {len(all_words)} 词{_scope_info}", size=13,
                                         color=ft.Colors.GREY_500)"""
if OLD not in t:
    raise SystemExit("!! 计数未匹配")
t = t.replace(OLD, NEW)

OLD = """                        if total > BATCH:
                            count_text.value = f"共 {total} 词（显示 {offset + 1}-{shown}）"
                        else:
                            count_text.value = f"共 {total} 词\""""
NEW = """                        if total > BATCH:
                            count_text.value = f"共 {total} 词（显示 {offset + 1}-{shown}）{_scope_info}"
                        else:
                            count_text.value = f"共 {total} 词{_scope_info}\""""
if OLD not in t:
    raise SystemExit("!! 计数刷新未匹配")
t = t.replace(OLD, NEW)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("main.py 已更新")
