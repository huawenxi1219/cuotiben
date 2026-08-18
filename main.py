import flet as ft

def main(page: ft.Page):
    page.add(ft.Text("Hello World - 如果看到这行，说明框架正常"))

ft.app(target=main)