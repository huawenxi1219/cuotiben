# -*- coding: utf-8 -*-
"""出错不再"静默打不开"：页面/聊天构建失败时把错误直接显示在屏幕上。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# 1) 功能页构建加兜底
OLD = """                _builder = func_pages.get(function_name)
                func_content = _builder() if _builder else None"""
NEW = """                _builder = func_pages.get(function_name)
                try:
                    func_content = _builder() if _builder else None
                except Exception as _ex:
                    _tb = traceback.format_exc()
                    try:
                        with open(os.path.join(DATA_DIR, "crash.log"), "a", encoding="utf-8") as _lf:
                            _lf.write(f"\\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 打开 {function_name} 失败\\n{_tb}\\n")
                    except BaseException:
                        pass
                    func_content = ft.Column([
                        ft.Text(f"⚠️ 打开「{function_name}」失败", size=16, color="#EF5350",
                                weight=ft.FontWeight.BOLD),
                        ft.Text(str(_ex)[:300], size=13, color="#EF5350", selectable=True),
                        ft.Divider(),
                        ft.Text("把下面这段发给开发者即可定位：", size=12, color="#888888"),
                        ft.Text(_tb[-1200:], size=10, color="#9E9E9E", selectable=True),
                    ], spacing=8, scroll=ft.ScrollMode.AUTO)"""
assert OLD in t, "功能页构建未匹配"
t = t.replace(OLD, NEW, 1)

# 2) 聊天窗构建加兜底
OLD2 = """                chat_dialog.content = build_chat_window(subject, initial_message, auto_send)"""
NEW2 = """                try:
                    chat_dialog.content = build_chat_window(subject, initial_message, auto_send)
                except Exception as _ex:
                    _tb = traceback.format_exc()
                    try:
                        with open(os.path.join(DATA_DIR, "crash.log"), "a", encoding="utf-8") as _lf:
                            _lf.write(f"\\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 打开聊天 {subject} 失败\\n{_tb}\\n")
                    except BaseException:
                        pass
                    chat_dialog.content = ft.Column([
                        ft.Text(f"⚠️ 打开「{subject}」对话失败", size=16, color="#EF5350",
                                weight=ft.FontWeight.BOLD),
                        ft.Text(str(_ex)[:300], size=13, color="#EF5350", selectable=True),
                        ft.Text(_tb[-1200:], size=10, color="#9E9E9E", selectable=True),
                    ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)"""
assert OLD2 in t, "聊天窗构建未匹配"
t = t.replace(OLD2, NEW2, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("错误兜底已加")
