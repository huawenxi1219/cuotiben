import flet as ft

def main(page: ft.Page):
    page.title = "测试"
    page.add(ft.Text("✅ 成功启动！", size=30))
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
