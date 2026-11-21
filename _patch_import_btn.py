# -*- coding: utf-8 -*-
"""加「导入化学知识图」按钮：选一个 chem_tree.json，复制到数据目录即生效。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) handler（放在 on_export_md 之前）
ANCHOR = "            def on_export_md(e):"
HANDLER = '''            def on_chem_tree_import(e):
                try:
                    files = getattr(e, "files", None) or []
                    if not files or not getattr(files[0], "path", ""):
                        return
                    import shutil as _sh
                    _sh.copyfile(files[0].path, CHEM_TREE_FILE)
                    tree = load_chem_tree()
                    n = 0
                    for b in (tree or {}).get("books", []):
                        for c in b.get("chapters", []):
                            for s in c.get("sections", []):
                                n += len(s.get("points", []))
                    show_toast(f"✅ 已导入知识图：{n} 个知识点", "green")
                except Exception as _ex:
                    show_toast(f"导入失败：{str(_ex)[:50]}", "red")

'''
assert ANCHOR in t
t = t.replace(ANCHOR, HANDLER + ANCHOR, 1)

# 2) 按钮：放在「批量重打标签」后面
OLD = '''                _row_btn(ft.ElevatedButton("🏷️ 批量重打标签", on_click=lambda e: batch_retag(e),
                                  icon=ft.Icons.LABEL)),'''
NEW = OLD + '''
                _row_btn(ft.ElevatedButton("📚 导入化学知识图", icon=ft.Icons.UPLOAD_FILE,
                                  on_click=lambda e: _use_picker(page, on_chem_tree_import).pick_files(
                                      file_type=ft.FilePickerFileType.CUSTOM,
                                      allowed_extensions=["json"]))),'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("导入按钮已加入")
