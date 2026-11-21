# -*- coding: utf-8 -*-
"""1) 备份改成一键存文件（不再要求选文件夹）
   2) 提示词加"结构化输出"要求，让回答有条理
"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 备份：save_file 一步到位 ----------
OLD_BTN = '''                    ft.ElevatedButton("📤 备份数据",
                                      on_click=lambda e: _use_picker(page, on_backup_result).get_directory_path(),
                                      icon=ft.Icons.BACKUP),'''
NEW_BTN = '''                    ft.ElevatedButton("📤 备份数据",
                                      on_click=lambda e: _use_picker(page, on_backup_result).save_file(
                                          dialog_title="保存备份文件",
                                          file_name="池鱼备份_%s.zip" % time.strftime("%Y%m%d"),
                                          file_type=ft.FilePickerFileType.CUSTOM,
                                          allowed_extensions=["zip"]),
                                      icon=ft.Icons.BACKUP),'''
assert OLD_BTN in t, "备份按钮未匹配"
t = t.replace(OLD_BTN, NEW_BTN, 1)

# 回调：兼容"存成文件"和"选文件夹"两种返回值
OLD_CB = '''                dest_dir = e.path
                backup_status.value = "⏳ 正在打包..."'''
NEW_CB = '''                _sel = e.path
                backup_status.value = "⏳ 正在打包..."'''
assert OLD_CB in t
t = t.replace(OLD_CB, NEW_CB, 1)

OLD_ZIP = '''                        ts = time.strftime("%Y%m%d_%H%M%S")
                        zip_path = os.path.join(dest_dir, f"池鱼Study备份_{ts}.zip")'''
NEW_ZIP = '''                        ts = time.strftime("%Y%m%d_%H%M%S")
                        if str(_sel).lower().endswith(".zip"):
                            zip_path = _sel
                        else:
                            zip_path = os.path.join(_sel, f"池鱼Study备份_{ts}.zip")'''
assert OLD_ZIP in t
t = t.replace(OLD_ZIP, NEW_ZIP, 1)

# ---------- 2) 提示词：结构化输出 ----------
OLD_P = '''【硬性要求】'''
NEW_P = '''【回答要有条理（默认按这个排版）】
- 用 Markdown：先一行结论，再用「## 小标题」分段，必要时用 1. 2. 3. 列步骤
- 关键术语、公式、结论用 **粗体** 标出来
- 每题最多 3 个小标题，别写成一整坨
- 对比类内容用短句分行，别塞成一段

【硬性要求】'''
assert OLD_P in t
t = t.replace(OLD_P, NEW_P, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("备份一步化 + 结构化提示词 已加入")
