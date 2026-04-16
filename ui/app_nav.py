import flet as ft


def ir_para_controle(page: ft.Page, controle):
    """Substitui o conteúdo da página por um novo controle."""
    page.controls.clear()
    page.controls.append(controle)
    page.update()
