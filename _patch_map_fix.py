# -*- coding: utf-8 -*-
"""修复个人思维导图：①节点标题取错（显示「无题目」）②超采样渲染，放大不糊。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 统一的错题标题提取（多字段兜底）
ANCHOR = "CHEM_TREE_FILE = os.path.join(DATA_DIR, \"chem_tree.json\")"
HELPER = '''def _err_title(e):
    """错题标题：兼容不同字段名，取不到就给可读的占位，避免出现「（无题目）」这种废信息。"""
    for k in ("original", "question", "title", "q", "content", "text", "stem"):
        v = e.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    tags = [str(x).strip() for x in (e.get("tags") or []) if str(x).strip()]
    if tags:
        return "（%s）" % tags[0]
    if e.get("image") or e.get("img") or e.get("image_path"):
        return "（图片题，见错题本）"
    ts = e.get("time") or ""
    return "（%s 录入，未填题干）" % (str(ts)[:16] if ts else "较早")


'''
assert ANCHOR in t
if "def _err_title(" not in t:
    t = t.replace(ANCHOR, HELPER + ANCHOR, 1)

# 2) 图谱数据构建：用新函数 + 更高分辨率
OLD = '''                            "errors": [(e.get("original") or e.get("question") or "（无题目）").strip()
                                       for e in data["err"]],'''
NEW = '''                            "errors": [_err_title(e) for e in data["err"]],'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

OLD2 = '''                        png = _render_mindmap(subject, kps)'''
NEW2 = '''                        png = _render_mindmap(subject, kps, scale=2)'''
assert OLD2 in t
t = t.replace(OLD2, NEW2, 1)

OLD3 = '''                            min_scale=0.3, max_scale=6.0,
                            constrained=True, expand=True)'''
NEW3 = '''                            min_scale=0.25, max_scale=4.0,
                            constrained=True, expand=True)'''
assert OLD3 in t
t = t.replace(OLD3, NEW3, 1)

# 3) 笔记标题也兜底
OLD4 = '''                            "notes": [(n.get("content") or "（空笔记）").strip() for n in data["note"]],'''
NEW4 = '''                            "notes": [(str(n.get("content") or n.get("text") or "").strip()
                                       or "（%s）" % ((n.get("tags") or ["空笔记"])[0])) for n in data["note"]],'''
assert OLD4 in t
t = t.replace(OLD4, NEW4, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("思维导图标题与清晰度已修")
