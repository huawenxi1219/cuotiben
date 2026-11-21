# -*- coding: utf-8 -*-
"""修两个空壳 + 加学习档案导出(Markdown)。按真实缩进插入。"""
import io, re

MAIN = r"C:\myapp\main.py"
src = io.open(MAIN, encoding="utf-8").read()
lines = src.split("\n")

# ---------- 1) 删除 → 先进回收站 ----------
out = []
i = 0
patched = 0
while i < len(lines):
    line = lines[i]
    out.append(line)
    if line.strip() == "def delete_item(e):":
        # 找这个函数体里第一行 all_items = load_jsonl(XXX_FILE)
        j = i + 1
        while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith("all_items = load_jsonl"):
            out.append(lines[j]); j += 1
        if j < len(lines):
            body_indent = re.match(r"^(\s*)", lines[j]).group(1)
            file_var = "ERRORS_FILE" if "ERRORS_FILE" in lines[j] else "NOTES_FILE"
            out.append(lines[j])          # all_items = load_jsonl(...)
            out.append(body_indent + "# 先放进回收站，再从列表移除（之前直接删，回收站永远是空的）")
            out.append(body_indent + "for _d in all_items:")
            out.append(body_indent + "    if _same_item(_d):")
            out.append(body_indent + "        try:")
            out.append(body_indent + "            move_to_recycle(_d)")
            out.append(body_indent + "        except BaseException:")
            out.append(body_indent + "            pass")
            patched += 1
            i = j + 1
            continue
    i += 1
lines = out
src = "\n".join(lines)

# 提示文案
src = src.replace('show_toast("🗑️ 已删除", "green")', 'show_toast("🗑️ 已删除（可在回收站找回）", "green")')

# ---------- 2) 导出函数 ----------
EXPORT_FN = r'''
def build_study_export_md():
    """把错题、笔记、画像、单词进度导出成一份 Markdown"""
    errs = load_jsonl(ERRORS_FILE)
    notes = load_jsonl(NOTES_FILE)
    prof = load_user_profile()
    vocab = load_jsonl(VOCAB_FILE)

    L = ["# 池鱼学习档案", "", f"导出时间：{time.strftime('%Y-%m-%d %H:%M')}", "",
         f"- 错题 **{len(errs)}** 道",
         f"- 笔记 **{len(notes)}** 条",
         f"- 词库 **{len(vocab)}** 词", ""]

    wk = sorted((prof.get("weak_knowledge") or {}).items(), key=lambda x: -x[1])[:12]
    if wk:
        L += ["## 薄弱知识点", ""]
        for k, v in wk:
            bar = "█" * max(1, min(10, int(float(v) * 20)))
            L.append(f"- **{k}**  {bar}  ({round(float(v), 2)})")
        L.append("")

    by_subject = {}
    for e in errs:
        by_subject.setdefault(e.get("subject", "未分类"), []).append(e)
    if by_subject:
        L += ["## 错题本", ""]
        for subj in sorted(by_subject):
            items = sorted(by_subject[subj], key=lambda x: x.get("timestamp", 0), reverse=True)
            L += [f"### {subj}（{len(items)} 道）", ""]
            for i, e in enumerate(items, 1):
                q = (e.get("original") or e.get("question") or "").strip()
                m = (e.get("mistake") or "").strip()
                a = (e.get("answer") or "").strip()
                tags = "、".join(str(x) for x in (e.get("tags") or [])[:6])
                L.append(f"**{i}. {q[:200] or '（无题目内容）'}**")
                if tags:
                    L.append(f"标签：{tags}")
                if m:
                    L.append(f"> 错因：{m[:200]}")
                if a:
                    L.append(f"> 答案：{a[:300]}")
                L.append("")

    if notes:
        L += ["## 笔记本", ""]
        for n in sorted(notes, key=lambda x: str(x.get("time", "")), reverse=True):
            body = (n.get("content") or "").strip()
            if not body:
                continue
            tags = "、".join(str(x) for x in (n.get("tags") or [])[:5])
            L.append(f"### {n.get('subject','')} · {n.get('time','')}" + (f"（{tags}）" if tags else ""))
            L.append("")
            L.append(body[:1200])
            L.append("")

    L += ["---", "由「池鱼Study」自动生成。"]
    return "\n".join(L)


'''
anchor = "def extract_chart_block(text):"
assert anchor in src
src = src.replace(anchor, EXPORT_FN.lstrip("\n") + anchor, 1)

# ---------- 3) 我的页面加两个按钮 ----------
m = re.search(r"^(\s*)ft\.ElevatedButton\(\"🏷️ 批量重打标签\"", src, re.M)
assert m, "找不到批量重打标签按钮"
ind = m.group(1)
block = (
    f'{ind}ft.ElevatedButton("📊 知识框架", on_click=lambda e: show_knowledge_framework(e),\n'
    f'{ind}                  icon=ft.Icons.INSIGHTS),\n'
    f'{ind}ft.ElevatedButton("📄 导出学习档案(.md)", icon=ft.Icons.DOWNLOAD,\n'
    f'{ind}                  on_click=lambda e: _use_picker(page, on_export_md).save_file(\n'
    f'{ind}                      dialog_title="导出学习档案",\n'
    f'{ind}                      file_name="池鱼学习档案.md",\n'
    f'{ind}                      file_type=ft.FilePickerFileType.CUSTOM,\n'
    f'{ind}                      allowed_extensions=["md"])),\n'
)
src = src[:m.start()] + block + src[m.start():]

# ---------- 4) 导出回调 ----------
m2 = re.search(r"^(\s*)def switch_page\(index\):", src, re.M)
assert m2, "找不到 switch_page"
ind2 = m2.group(1)
cb = (
    f'{ind2}def on_export_md(e):\n'
    f'{ind2}    if not getattr(e, "path", ""):\n'
    f'{ind2}        return\n'
    f'{ind2}    _p = e.path if str(e.path).lower().endswith(".md") else str(e.path) + ".md"\n'
    f'{ind2}    try:\n'
    f'{ind2}        with open(_p, "w", encoding="utf-8") as _f:\n'
    f'{ind2}            _f.write(build_study_export_md())\n'
    f'{ind2}        show_toast(f"✅ 已导出：{{os.path.basename(_p)}}", "green")\n'
    f'{ind2}    except Exception as _ex:\n'
    f'{ind2}        show_toast(f"❌ 导出失败：{{str(_ex)[:40]}}", "red")\n\n'
)
src = src[:m2.start()] + cb + src[m2.start():]

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(src)
print("删除进回收站：", patched, "处；导出已接入")
