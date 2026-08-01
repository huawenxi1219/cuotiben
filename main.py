import flet as ft

def main(page: ft.Page):
    page.add(ft.Text("Hello World！如果看到这句话，说明环境正常"))
    page.update()

ft.app(target=main)