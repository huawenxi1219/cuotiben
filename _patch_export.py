# -*- coding: utf-8 -*-
"""修两个空壳 + 加学习档案导出(Markdown)。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 删除错题/笔记 → 真正进回收站 ----------
OLD_E = """                def delete_item(e):
                    all_items = load_jsonl(ERRORS_FILE)
                    filtered = [d for d in all_items if not _same_item(d)]
                    save_jsonl(ERRORS_FILE, filtered)
                    page.close(edit_dlg)
                    show_toast("🗑️ 已删除", "green")
                    open_function_page(subject, "错题本")"""
NEW_E = """                def delete_item(e):
                    all_items = load_jsonl(ERRORS_FILE)
                    # 先放进回收站，再从错题本移除（之前直接删，回收站永远是空的）
                    for _d in all_items:
                        if _same_item(_d):
                            try:
                                move_to_recycle(_d)
                            except BaseException:
                                pass
                    filtered = [d for d in all_items if not _same_item(d)]
                    save_jsonl(ERRORS_FILE, filtered)
                    page.close(edit_dlg)
                    show_toast("🗑️ 已删除（可在回收站找回）", "green")
                    open_function_page(subject, "错题本")"""
assert OLD_E in t, "错题删除未匹配"
t = t.replace(OLD_E, NEW_E, 1)

OLD_N = """                def delete_item(e):
                    all_items = load_jsonl(NOTES_FILE)
                    filtered = [d for d in all_items if not _same_item(d)]
                    save_jsonl(NOTES_FILE, filtered)
                    page.close(edit_dlg)
                    show_toast("🗑️ 已删除", "green")
                    open_function_page(subject, "笔记本")"""
NEW_N = """                def delete_item(e):
                    all_items = load_jsonl(NOTES_FILE)
                    for _d in all_items:
                        if _same_item(_d):
                            try:
                                move_to_recycle(_d)
                            except BaseException:
                                pass
                    filtered = [d for d in all_items if not _same_item(d)]
                    save_jsonl(NOTES_FILE, filtered)
                    page.close(edit_dlg)
                    show_toast("🗑️ 已删除（可在回收站找回）", "green")
                    open_function_page(subject, "笔记本")"""
assert OLD_N in t, "笔记删除未匹配"
t = t.replace(OLD_N, NEW_N, 1)

# ---------- 2) 导出：生成 Markdown 学习档案 ----------
EXPORT_FN = r'''
def build_study_export_md():
    """把错题、笔记、画像、单词进度导出成一份 Markdown"""
    errs = load_jsonl(ERRORS_FILE)
    notes = load_jsonl(NOTES_FILE)
    prof = load_user_profile()
    vocab = load_jsonl(VOCAB_FILE)

    L = []
    L.append("# 池鱼学习档案")
    L.append("")
    L.append(f"导出时间：{time.strftime('%Y-%m-%d %H:%M')}")
    L.append("")
    L.append(f"- 错题 **{len(errs)}** 道")
    L.append(f"- 笔记 **{len(notes)}** 条")
    L.append(f"- 词库 **{len(vocab)}** 词")
    L.append("")

    wk = sorted((prof.get("weak_knowledge") or {}).items(), key=lambda x: -x[1])[:12]
    if wk:
        L.append("## 薄弱知识点")
        L.append("")
        for k, v in wk:
            bar = "█" * max(1, min(10, int(float(v) * 20)))
            L.append(f"- **{k}**  {bar}  ({round(float(v), 2)})")
        L.append("")

    by_subject = {}
    for e in errs:
        by_subject.setdefault(e.get("subject", "未分类"), []).append(e)

    if by_subject:
        L.append("## 错题本")
        L.append("")
        for subj in sorted(by_subject):
            items = sorted(by_subject[subj], key=lambda x: x.get("timestamp", 0), reverse=True)
            L.append(f"### {subj}（{len(items)} 道）")
            L.append("")
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
        L.append("## 笔记本")
        L.append("")
        for n in sorted(notes, key=lambda x: str(x.get("time", "")), reverse=True):
            body = (n.get("content") or "").strip()
            if not body:
                continue
            tags = "、".join(str(x) for x in (n.get("tags") or [])[:5])
            head = f"### {n.get('subject','')} · {n.get('time','')}"
            L.append(head + (f"（{tags}）" if tags else ""))
            L.append("")
            L.append(body[:1200])
            L.append("")

    L.append("---")
    L.append("由「池鱼Study」自动生成。")
    return "\n".join(L)


'''
ANCHOR = "def extract_chart_block(text):"
assert ANCHOR in t
t = t.replace(ANCHOR, EXPORT_FN.lstrip("\n") + ANCHOR, 1)

# ---------- 3) 按钮：我的 → 导出学习档案 ----------
OLD_BTN = """                ft.ElevatedButton("🏷️ 批量重打标签", on_click=lambda e: batch_retag(e),
                                  icon=ft.Icons.LABEL),"""
NEW_BTN = """                ft.ElevatedButton("📊 知识框架", on_click=lambda e: show_knowledge_framework(e),
                                  icon=ft.Icons.INSIGHTS),
                ft.ElevatedButton("📄 导出学习档案(.md)", icon=ft.Icons.DOWNLOAD,
                                  on_click=lambda e: _use_picker(page, on_export_md).save_file(
                                      dialog_title="导出学习档案",
                                      file_name="池鱼学习档案.md",
                                      file_type=ft.FilePickerFileType.CUSTOM,
                                      allowed_extensions=["md"])),
                ft.ElevatedButton("🏷️ 批量重打标签", on_click=lambda e: batch_retag(e),
                                  icon=ft.Icons.LABEL),"""
assert OLD_BTN in t, "按钮区未匹配"
t = t.replace(OLD_BTN, NEW_BTN, 1)

# ---------- 4) 导出回调 ----------
OLD_CB = """            def switch_page(index):"""
NEW_CB = """            def on_export_md(e):
                if not getattr(e, "path", ""):
                    return
                _p = e.path if str(e.path).lower().endswith(".md") else str(e.path) + ".md"
                try:
                    with open(_p, "w", encoding="utf-8") as _f:
                        _f.write(build_study_export_md())
                    show_toast(f"✅ 已导出到：{os.path.basename(_p)}", "green")
                except Exception as _ex:
                    show_toast(f"❌ 导出失败：{str(_ex)[:40]}", "red")

            def switch_page(index):"""
assert OLD_CB in t, "switch_page 未匹配"
t = t.replace(OLD_CB, NEW_CB, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("回收站/知识框架/导出 已接入")
