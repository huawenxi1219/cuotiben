# -*- coding: utf-8 -*-
"""1) 新版知识页：知识点 → 笔记全文 + 错题（精准、内容全）
   2) 砍掉「我的」里的手环背单词区块
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 新版知识页 ----------
FN = r'''
            def build_knowledge_page(subject):
                """知识点 → 笔记全文 / 错题。追求好用、精准、信息完整，不做花哨动效。"""
                import json as _json
                errs = [e for e in load_jsonl(ERRORS_FILE) if e.get("subject") == subject]
                notes = [n for n in load_jsonl(NOTES_FILE) if n.get("subject") == subject]

                buckets = {}   # 知识点 -> {"err": [...], "note": [...]}
                for e in errs:
                    tags = [str(x) for x in (e.get("tags") or []) if str(x).strip()]
                    kp = (e.get("kp") or (tags[0] if tags else "未分类")).strip() or "未分类"
                    buckets.setdefault(kp, {"err": [], "note": []})["err"].append(e)
                for n in notes:
                    tags = [str(x) for x in (n.get("tags") or []) if str(x).strip()] or ["未分类"]
                    for tg in tags:
                        buckets.setdefault(tg.strip(), {"err": [], "note": []})["note"].append(n)

                kp_total = len(buckets)
                note_total = len(notes)
                err_total = len(errs)

                search = ft.TextField(label="搜索知识点 / 笔记内容", dense=True, expand=True)
                body = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

                def _note_card(n):
                    txt = (n.get("content") or "").strip()
                    if not txt and n.get("media"):
                        txt = f"（{len(n.get('media') or [])} 张图片笔记）"
                    kids = [ft.Text(txt or "（空笔记）", size=14, color="#D7DBEA", selectable=True)]
                    if n.get("media"):
                        kids.append(ft.Text(f"📎 {len(n['media'])} 张图", size=11, color="#7AA2F7"))
                    kids.append(ft.Text(str(n.get("time", ""))[:16], size=10, color="#6B7280"))
                    return ft.Container(content=ft.Column(kids, spacing=4),
                                        padding=10, border_radius=10, bgcolor="#1B1F2E",
                                        margin=ft.margin.only(bottom=6))

                def _err_card(e):
                    q = (e.get("original") or e.get("question") or "").strip()
                    m = (e.get("mistake") or "").strip()
                    a = (e.get("answer") or "").strip()
                    kids = [ft.Text(q[:200] or "（无题目）", size=14, color="#F2F4FA",
                                    weight=ft.FontWeight.W_500, selectable=True)]
                    if m:
                        kids.append(ft.Text("错因：" + m[:150], size=12, color="#F7768E", selectable=True))
                    if a:
                        kids.append(ft.Text("答案：" + a[:150], size=12, color="#9ECE6A", selectable=True))
                    kids.append(ft.Text(str(e.get("time", ""))[:16], size=10, color="#6B7280"))
                    return ft.Container(content=ft.Column(kids, spacing=4),
                                        padding=10, border_radius=10, bgcolor="#241A1E",
                                        margin=ft.margin.only(bottom=6))

                def render(kw=""):
                    kw = (kw or "").strip()
                    body.controls.clear()
                    shown = 0
                    for kp in sorted(buckets.keys()):
                        data = buckets[kp]
                        if kw:
                            hay = kp + "".join((n.get("content") or "") for n in data["note"]) + \
                                  "".join((e.get("original") or "") for e in data["err"])
                            if kw not in hay:
                                continue
                        shown += 1
                        detail = ft.Column(spacing=6, visible=False)
                        if data["note"]:
                            detail.controls.append(ft.Text(f"📓 笔记（{len(data['note'])}）", size=12, color="#4DB6AC"))
                            for n in data["note"]:
                                detail.controls.append(_note_card(n))
                        if data["err"]:
                            detail.controls.append(ft.Text(f"📕 错题（{len(data['err'])}）", size=12, color="#F7768E"))
                            for e in data["err"]:
                                detail.controls.append(_err_card(e))

                        head = ft.Container(
                            content=ft.Row([
                                ft.Text(kp, size=16, weight=ft.FontWeight.W_600, color="#E8EBF5", expand=True),
                                ft.Text(f"记 {len(data['note'])} · 错 {len(data['err'])}", size=11, color="#8B93A7"),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color="#6B7280"),
                            ], spacing=8),
                            padding=12, border_radius=12, bgcolor="#151824",
                            border=ft.border.all(1, "#262B3D"), ink=True,
                            on_click=lambda e, d=detail: (_toggle(d), page.update()))

                        body.controls.append(ft.Column([head, detail], spacing=4))

                    if shown == 0:
                        body.controls.append(u_empty("🧠", "这个科目还没有知识点",
                                                     "录错题或记笔记后，这里会自动长出来"))

                def _toggle(d):
                    d.visible = not d.visible

                def on_search(e):
                    render(search.value)

                search.on_change = on_search
                render()

                return ft.Column([
                    ft.Row([
                        ft.Text(f"{subject} · 知识点", size=18, weight=ft.FontWeight.W_600, color="#E8EBF5"),
                        ft.Container(expand=True),
                        ft.Text(f"{kp_total} 个知识点 · {note_total} 条笔记 · {err_total} 道错题",
                                size=11, color="#8B93A7"),
                    ]),
                    search,
                    ft.Divider(height=1, color="#262B3D"),
                    body,
                ], spacing=10, expand=True)

'''
anchor = "            def build_subject_left_panel(subj):"
assert anchor in t
t = t.replace(anchor, FN.lstrip("\n") + anchor, 1)

# 卡片入口 "思维导图" 改指向新页面
OLD_MAP = '                    "思维导图": lambda: build_mindmap_page(subject, highlight_kp=_mm_hl),'
NEW_MAP = '                    "思维导图": lambda: build_knowledge_page(subject),'
assert OLD_MAP in t
t = t.replace(OLD_MAP, NEW_MAP, 1)

# ---------- 2) 砍掉手环区块 ----------
OLD_BAND = '''                ft.Divider(),
                ft.Text("⌚ 手环背单词", size=20),
                band_sync_status,
                band_http_btn,
                band_http_status,
                ft.Row([band_scope, band_count_field]),
                ft.Row([
                    ft.ElevatedButton("🔄 一键同步新词", icon=ft.Icons.SYNC,
                                      on_click=on_band_sync_new_words),
                    ft.ElevatedButton("🚀 一键推送", icon=ft.Icons.SEND,
                                      on_click=on_band_quick_push),
                    ft.ElevatedButton("📤 存为文件", icon=ft.Icons.UPLOAD_FILE,
                                      on_click=on_band_export_click),
                    ft.ElevatedButton("📥 导入记录", icon=ft.Icons.DOWNLOAD_DONE,
                                      on_click=on_band_records_click),
                ], wrap=True),
                band_status,
                ft.Divider(),
'''
assert OLD_BAND in t, "手环区块未匹配"
t = t.replace(OLD_BAND, '''                ft.Divider(),
''', 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("知识页已替换，手环区块已移除")
