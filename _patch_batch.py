# -*- coding: utf-8 -*-
"""批量拍题：多选图片 → 逐张识别 → 勾选确认 → 批量入库（附带原图）。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

FN = r'''
            # ================= 批量拍题 =================
            def batch_import(e=None):
                """一次选多张 → 逐张 AI 识别 → 列表勾选 → 批量入库"""
                _results = []

                def _on_files(ev):
                    files = getattr(ev, "files", None) or []
                    if not files:
                        return
                    paths = [f.path for f in files if getattr(f, "path", "")]
                    if not paths:
                        return
                    _run(paths)

                def _run(paths):
                    prog = ft.Text(f"正在识别 0/{len(paths)}...", size=14)
                    dlg = ft.AlertDialog(
                        title=ft.Text("AI 正在识别"),
                        content=ft.Container(content=ft.Column([
                            prog,
                            ft.Text("一张图一道题；识别结果稍后可以逐条勾选、改科目",
                                    size=12, color=C_TEXT2),
                        ], spacing=10), width=_dlg_w(page, 340)),
                        actions=[])
                    page.open(dlg)
                    page.update()

                    def _work():
                        ok = 0
                        for i, p in enumerate(paths):
                            try:
                                prog.value = f"正在识别 {i + 1}/{len(paths)}..."
                                page.update()
                            except BaseException:
                                pass
                            try:
                                r = analyze_single_image(p)
                            except BaseException:
                                r = None
                            if r and (r.get("question") or "").strip():
                                rel = ""
                                try:
                                    rel = copy_file_to_lib(p, IMAGES_DIR, IMG_EXTS) or ""
                                except BaseException:
                                    rel = ""
                                _results.append({
                                    "q": str(r.get("question") or "").strip(),
                                    "a": str(r.get("answer") or "").strip(),
                                    "et": str(r.get("error_type") or "").strip(),
                                    "kp": str(r.get("knowledge_point") or "").strip(),
                                    "media": rel,
                                })
                                ok += 1
                        try:
                            page.close(dlg)
                        except BaseException:
                            pass
                        try:
                            _show_confirm(_results, len(paths), ok)
                        except Exception as _ex:
                            show_toast(f"确认页出错：{str(_ex)[:40]}", "red")

                    threading.Thread(target=_work, daemon=True).start()

                _use_picker(page, _on_files).pick_files(
                    file_type=ft.FilePickerFileType.IMAGE, allow_multiple=True)

            def _show_confirm(results, total, ok):
                if not results:
                    show_toast(f"没有识别到题目（共 {total} 张）", "red")
                    return
                subj_batch = ft.Dropdown(
                    label="这批题的科目",
                    options=[ft.dropdown.Option(s) for s in ["数学", "语文", "英语", "物理", "化学",
                                                             "生物", "历史", "政治", "地理"]],
                    value=subj_dd.value, width=150)
                checks = []
                col = ft.Column([], spacing=2, scroll=ft.ScrollMode.AUTO)
                for i, r in enumerate(results):
                    cb = ft.Checkbox(value=True)
                    checks.append((cb, r))
                    col.controls.append(ft.Row([
                        cb,
                        ft.Column([
                            ft.Text(r["q"][:46].replace("\n", " "), size=13, color=C_TEXT),
                            ft.Text((r["kp"] or "未识别知识点"), size=11, color=C_TEXT2),
                        ], spacing=1, expand=True),
                    ], spacing=6))

                def do_save(ev):
                    picked = [r for cb, r in checks if cb.value]
                    if not picked:
                        show_toast("一道都没选", "red")
                        return
                    subj = subj_batch.value or "数学"
                    n = 0
                    for r in picked:
                        try:
                            save_error(subj, r["q"], [r["media"]] if r["media"] else [],
                                       r["a"], [], r["et"], "", [], r["kp"])
                            n += 1
                        except BaseException:
                            pass
                    page.close(dlg2)
                    show_toast(f"✅ 已入库 {n} 道（{subj}）", "green")

                dlg2 = ft.AlertDialog(
                    title=ft.Text(f"识别到 {ok} 道（共 {total} 张）"),
                    content=ft.Container(content=ft.Column([
                        subj_batch,
                        ft.Text("勾掉不要的，确认后按这个科目入库", size=12, color=C_TEXT2),
                        ft.Container(content=col, height=_dlg_h(page, 320), width=_dlg_w(page, 380)),
                    ], spacing=8), width=_dlg_w(page, 400)),
                    actions=[
                        ft.TextButton("取消", on_click=lambda ev: page.close(dlg2)),
                        ft.ElevatedButton("全部入库", icon=ft.Icons.SAVE, on_click=do_save),
                    ])
                page.open(dlg2)
                page.update()

'''

anchor = "            note_subject_dd = ft.Dropdown("
assert anchor in t
t = t.replace(anchor, FN.lstrip("\n") + anchor, 1)

# 首页加"批量录题"按钮
OLD = '''                u_primary_btn("保存错题", submit_error, ft.Icons.SAVE),'''
NEW = '''                ft.Row([
                    u_primary_btn("保存错题", submit_error, ft.Icons.SAVE),
                    u_primary_btn("批量录题", batch_import, ft.Icons.PHOTO_LIBRARY, color="#9ECE6A"),
                ], spacing=10),'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("批量拍题已加入")
