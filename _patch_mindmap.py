# -*- coding: utf-8 -*-
"""思维导图改成「商城导航」式分层：不会的 / 记过的 / 其他，每组下面才是知识点。"""
import io, re

MAIN = r"C:\myapp\main.py"
src = io.open(MAIN, encoding="utf-8").read()

NEW_FN = r'''def build_mindmap(subject):
    """按「掌握情况」分成三组再往下钻，像商场楼层导航：
       学科 → ⚠️我不会的 / 📓我记过的 / 📚其他知识点 → 知识点 → 笔记·错题
    同名知识点只出现在一个组里，不会出现"两个节点同名打架"。"""
    errors = load_jsonl(ERRORS_FILE)
    subj_errors = [e for e in errors if e.get("subject") == subject]

    kp_err = {}          # 知识点 -> 错题数
    for e in subj_errors:
        tags = [str(t) for t in (e.get("tags") or []) if str(t).strip()] or ["未分类"]
        kp = (e.get("kp") or tags[0]).strip()
        kp_err[kp] = kp_err.get(kp, 0) + 1

    kp_note = {}         # 知识点 -> 笔记数
    try:
        for _n in load_jsonl(NOTES_FILE):
            if _n.get("subject") != subject:
                continue
            for _tg in (_n.get("tags") or []):
                _s = str(_tg).strip()
                if _s:
                    kp_note[_s] = kp_note.get(_s, 0) + 1
    except BaseException as _be:
        _diag_log(_be, "L1990")
        pass

    # 画像里的薄弱点也算"我不会的"
    try:
        _wk = (load_user_profile().get("weak_knowledge") or {})
    except BaseException:
        _wk = {}

    def _mk_node(kp, cnt_err, cnt_note):
        nd = {"title": kp, "kp": kp, "count": cnt_err,
              "children": [
                  {"title": "📓 笔记", "kind": "notes", "kp": kp},
                  {"title": "📕 错题", "kind": "errors", "kp": kp},
              ]}
        if cnt_note:
            nd["count"] = cnt_err + cnt_note
        return nd

    weak_nodes, note_nodes, other_nodes = [], [], []
    all_kps = set(kp_err) | set(kp_note) | set(_wk)
    for kp in sorted(all_kps):
        if not kp:
            continue
        ce, cn = kp_err.get(kp, 0), kp_note.get(kp, 0)
        nd = _mk_node(kp, ce, cn)
        if ce > 0 or kp in _wk:
            weak_nodes.append(nd)
        elif cn > 0:
            note_nodes.append(nd)
        else:
            other_nodes.append(nd)

    # 手动添加过、但现在既没错题也没笔记的知识点，收进"其他"，别丢
    try:
        old = load_mindmap(subject) or {}
        _known = all_kps
        for c in (old.get("children") or []):
            t = c.get("title")
            # 兼容旧结构（扁平知识点）和新结构（分组）
            if c.get("children") and all((x.get("title") or "").startswith(("📓", "📕", "📚", "📝", "⚠️"))
                                         for x in c["children"]):
                continue
            if t and t not in _known and t != subject and not t.startswith(("📚", "📓", "⚠️")):
                other_nodes.append(_mk_node(t, 0, 0))
    except BaseException as _be:
        _diag_log(_be, "L2030")
        pass

    groups = []
    if weak_nodes:
        groups.append({"title": f"⚠️ 我不会的（{len(weak_nodes)}）", "kind": "group",
                       "children": weak_nodes, "count": len(weak_nodes)})
    if note_nodes:
        groups.append({"title": f"📓 我记过的（{len(note_nodes)}）", "kind": "group",
                       "children": note_nodes, "count": len(note_nodes)})
    if other_nodes:
        groups.append({"title": f"📚 其他知识点（{len(other_nodes)}）", "kind": "group",
                       "children": other_nodes, "count": len(other_nodes)})

    tree = {"title": subject, "children": groups}
    save_mindmap(subject, tree)
    return tree


'''

# 用新函数整体替换旧 build_mindmap
m = re.search(r"def build_mindmap\(subject\):.*?(?=\n@retry_request|\ndef generate_word_info)", src, re.S)
assert m, "找不到 build_mindmap 原始函数"
src = src[:m.start()] + NEW_FN + src[m.end():]

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(src)
print("build_mindmap 已改为三层分组")
