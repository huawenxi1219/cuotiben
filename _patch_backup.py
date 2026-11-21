# -*- coding: utf-8 -*-
"""备份更透明：打包时写入 manifest，显示包含多少错题/笔记/对话等；按钮文案更明确。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 备份：写入 manifest + 统计
OLD = '''                        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                            for root, dirs, files in os.walk(DATA_DIR):
                                if "_restore_tmp" in root.split(os.sep):
                                    continue
                                for f in files:
                                    if f.startswith("."):
                                        continue
                                    full = os.path.join(root, f)
                                    arc = os.path.relpath(full, DATA_DIR)
                                    zf.write(full, arc)
                        backup_status.value = f"✅ 备份成功：{zip_path}"'''
NEW = '''                        def _cnt(name):
                            try:
                                return len(load_jsonl(os.path.join(DATA_DIR, name)))
                            except BaseException:
                                return 0

                        manifest = {
                            "app": "池鱼Study",
                            "time": ts,
                            "errors": _cnt("errors.jsonl"),
                            "notes": _cnt("notes.jsonl"),
                            "vocab": _cnt("vocabulary.jsonl"),
                            "sentences": _cnt("sentences.jsonl"),
                        }
                        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
                            for root, dirs, files in os.walk(DATA_DIR):
                                if "_restore_tmp" in root.split(os.sep):
                                    continue
                                for f in files:
                                    if f.startswith("."):
                                        continue
                                    full = os.path.join(root, f)
                                    arc = os.path.relpath(full, DATA_DIR)
                                    zf.write(full, arc)
                        backup_status.value = (f"✅ 备份成功：错题 {manifest['errors']} · 笔记 "
                                               f"{manifest['notes']} · 单词 {manifest['vocab']} · "
                                               f"金句 {manifest['sentences']}\\n{zip_path}")'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

# 2) 按钮文案更明确
t = t.replace('ft.ElevatedButton("📤 备份数据",', 'ft.ElevatedButton("📤 完整备份（全部数据）",', 1)
t = t.replace('ft.ElevatedButton("📥 覆盖恢复",', 'ft.ElevatedButton("📥 覆盖恢复（换设备）",', 1)
t = t.replace('ft.ElevatedButton("🔀 合并恢复",', 'ft.ElevatedButton("🔀 合并恢复（多设备合数据）",', 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("备份增强完成")
