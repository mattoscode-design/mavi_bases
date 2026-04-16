import flet as ft
from ui import tema


def tela_modulos(page: ft.Page, usuario: str, banco: str, on_modulo):
    def _abrir_grupos(e):
        from ui.mapeamento import abrir_gerenciador_grupos

        abrir_gerenciador_grupos(page)

    botoes = [
        tema.btn_outline(
            "Tratamento de Bases", on_click=lambda e: on_modulo("upload"), largura=320
        ),
        tema.btn_outline(
            "Configurar Mapeamento",
            on_click=lambda e: on_modulo("mapeamento"),
            largura=320,
        ),
        tema.btn_outline(
            "Lojas Pendentes", on_click=lambda e: on_modulo("validacao"), largura=320
        ),
        tema.btn_outline(
            "📂 Grupos de Varejistas", on_click=_abrir_grupos, largura=320
        ),
    ]

    info = ft.Column(
        [
            ft.Text(
                f"Banco de Dados: {banco}",
                size=12,
                color=tema.TEXT_MUTED,
                weight=ft.FontWeight.W_500,
            ),
            ft.Text(f"Usuário: {usuario}", size=12, color=tema.TEXT_MUTED),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=2,
    )

    return ft.Column(
        [
            ft.Row(
                [
                    ft.IconButton(
                        ft.Icons.ARROW_BACK,
                        icon_color=tema.TEXT_MUTED,
                        on_click=lambda e: on_modulo("banco"),
                        tooltip="Trocar banco",
                    )
                ],
            ),
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
