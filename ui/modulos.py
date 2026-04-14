import flet as ft
from ui import tema


def tela_modulos(page: ft.Page, usuario: str, banco: str, on_modulo):
    """
    Tela de seleção de módulo.
    on_modulo(modulo: str) é chamado com 'upload' ou 'mapeamento'.
    """

    def voltar(e):
        on_modulo("banco")

    btn_voltar = ft.IconButton(
        icon=ft.Icons.ARROW_BACK,
        icon_color=tema.TEXT_MUTED,
        on_click=voltar,
        tooltip="Voltar",
    )

    modulos = [
        ("Tratamento de Bases", "upload"),
        ("Configurar Mapeamento", "mapeamento"),
        ("Lojas Pendentes", "validacao"),
    ]

    botoes = [
        tema.btn_outline(
            nome,
            on_click=lambda e, m=modulo: on_modulo(m),
            largura=320,
        )
        for nome, modulo in modulos
    ]

    info = ft.Column(
        [
            ft.Text(
                f"Banco de Dados: {banco}",
                size=12,
                color=tema.TEXT_MUTED,
                weight=ft.FontWeight.W_500,
            ),
            ft.Text(
                f"Usuário: {usuario}",
                size=12,
                color=tema.TEXT_MUTED,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=2,
    )

    return ft.Column(
        [
            ft.Row([btn_voltar], alignment=ft.MainAxisAlignment.START),
            ft.Column(
                [
                    ft.Container(expand=True),
                    tema.titulo_logo(),
                    ft.Container(height=32),
                    *botoes,
                    ft.Container(height=24),
                    info,
                    ft.Container(height=24),
                    tema.rodape(),
                    ft.Container(expand=True),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
                spacing=10,
            ),
        ],
        expand=True,
        spacing=0,
    )
