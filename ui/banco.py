import flet as ft
from ui import tema
import mysql.connector
from config import DB_CONFIG


def listar_bancos() -> list[str]:
    try:
        cfg = {k: v for k, v in DB_CONFIG.items() if k != "database"}
        conn = mysql.connector.connect(**cfg)
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        ignorar = {"information_schema", "performance_schema", "mysql", "sys"}
        bancos = [r[0] for r in cursor.fetchall() if r[0] not in ignorar]
        cursor.close()
        conn.close()
        return sorted(bancos)
    except Exception as e:
        return []


def tela_banco(page: ft.Page, usuario: str, on_sucesso):
    """
    Tela de seleção de banco.
    on_sucesso(banco: str) é chamado quando conectar.
    """
    bancos = listar_bancos()
    dropdown = tema.dropdown_estilo("Selecione um banco", bancos)
    txt_erro = ft.Text("", color=tema.DANGER, size=13, visible=False)

    def conectar(e):
        banco = dropdown.value
        if not banco:
            txt_erro.value = "Selecione um banco antes de continuar."
            txt_erro.visible = True
            page.update()
            return

        import os

        os.environ["DB_NAME"] = banco

        # reinicia pool de conexões com novo banco
        from engine import conexao as cx

        cx._pool = None

        txt_erro.visible = False
        on_sucesso(banco)

    def voltar(e):
        from ui.login import tela_login

        page.session.remove("usuario")
        page.views.clear()
        page.views.append(ft.View("/", [tela_login(page, lambda u: None)]))
        page.update()

    btn_voltar = ft.IconButton(
        icon=ft.Icons.ARROW_BACK,
        icon_color=tema.TEXT_MUTED,
        on_click=voltar,
        tooltip="Voltar",
    )

    conteudo = [
        dropdown,
        txt_erro,
        ft.Container(height=4),
        tema.btn_primario("Conectar", on_click=conectar, largura=320),
    ]

    return ft.Column(
        [
            ft.Row([btn_voltar], alignment=ft.MainAxisAlignment.START),
            ft.Column(
                [
                    ft.Container(expand=True),
                    tema.titulo_logo(),
                    ft.Container(height=24),
                    *conteudo,
                    ft.Container(height=32),
                    tema.rodape(),
                    ft.Container(expand=True),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
        ],
        expand=True,
        spacing=0,
    )
