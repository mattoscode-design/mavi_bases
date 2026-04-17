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

    def _ver_log(e):
        if not _LOG_PATH.exists():
            tema.snackbar_erro(page, "Nenhum log encontrado ainda.")
            return

        # Lê as últimas 100 linhas
        try:
            linhas = _LOG_PATH.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            ultimas = linhas[-100:]
        except Exception as ex:
            tema.snackbar_erro(page, f"Não foi possível ler o log: {ex}")
            return

        conteudo = ft.Column(
            [
                ft.Text(
                    l,
                    size=10,
                    color=(
                        tema.DANGER
                        if "[ERROR" in l
                        else (tema.TEXT_MUTED if "[DEBUG" in l else tema.TEXT)
                    ),
                    selectable=True,
                    font_family="monospace",
                )
                for l in ultimas
            ],
            spacing=1,
            scroll=ft.ScrollMode.AUTO,
        )

        def _abrir_pasta(ev):
            subprocess.Popen(["explorer", os.path.normpath(str(_LOG_PATH.parent))])

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Log de erros (últimas 100 linhas)", size=14, color=tema.TEXT
            ),
            content=ft.Container(content=conteudo, width=680, height=420),
            actions=[
                ft.TextButton(
                    "Abrir pasta",
                    style=ft.ButtonStyle(color=tema.TEXT_MUTED),
                    on_click=_abrir_pasta,
                ),
                ft.TextButton(
                    "Fechar",
                    style=ft.ButtonStyle(color=tema.TEAL),
                    on_click=lambda ev: (page.close(dlg), page.update()),
                ),
            ],
            bgcolor=tema.BG2,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

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
                    ft.Container(height=12),
                    ft.TextButton(
                        "🗒 Ver log de erros",
                        style=ft.ButtonStyle(color=tema.TEXT_MUTED),
                        on_click=_ver_log,
                    ),
                    ft.Container(height=12),
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
