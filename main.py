import os
import sys
import flet as ft

# ===== 写入启动标记，证明 Python 环境已运行 =====
try:
    with open(os.path.join(os.getcwd(), "startup_log.txt"), "w") as f:
        f.write("Python environment started\n")
except Exception as e:
    # 如果写入失败，尝试写入到外部存储（部分手机可能需要权限）
    try:
        with open("/sdcard/startup_log.txt", "w") as f:
            f.write(f"Python started, but internal write failed: {e}\n")
    except:
        pass

def main(page: ft.Page):
    # ===== 写入 main 函数启动标记 =====
    try:
        with open(os.path.join(os.getcwd(), "main_started.txt"), "w") as f:
            f.write("main() called\n")
    except:
        try:
            with open("/sdcard/main_started.txt", "w") as f:
                f.write("main() called (fallback)\n")
        except:
            pass

    # ===== 显示文字 =====
    page.title = "测试"
    page.add(ft.Text("Hello, 世界！如果你看到这行，说明 App 正常。", size=30))
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
