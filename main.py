import flet as ft
import os

def main(page: ft.Page):
    page.title = "测试"
    page.add(ft.Text("✅ 成功启动！", size=30))
    page.update()
    # 写入成功标记
    try:
        with open("/sdcard/success.txt", "w") as f:
            f.write("App started successfully")
    except:
        pass

if __name__ == "__main__":
    ft.app(target=main)
