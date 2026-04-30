import flet as ft
from ui import tema
import mysql.connector
from config import DB_CONFIG, ENV_CONFIGURADO, ENV_AUSENTE


def listar_bancos() -> list:
    if not ENV_CONFIGURADO:
        return []
    try:
        cfg = {k: v for k, v in DB_CONFIG.items() if k != "database"}
        conn = mysql.connector.connect(**cfg)
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        ignorar = {"information_schema", "performance_schema", "mysql", "sys"}
        bancos = sorted([r[0] for r in cursor.fetchall() if r[0] not in ignorar])
        cursor.close()
        conn.close()
        return bancos
    except Exception:
        return []


def tela_banco(page: ft.Page, usuario: str, on_sucesso):
    if not ENV_CONFIGURADO:
        msg = (
            "Arquivo .env não encontrado."
            if ENV_AUSENTE
            else "Credenciais do banco não configuradas no .env."
        )
        return ft.Column(
            [
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=tema.DANGER, size=48),
                ft.Text("Configuração ausente", size=16, color=tema.DANGER),
                ft.Text(msg, size=13, color=tema.TEXT_MUTED),
                ft.Container(height=8),
                ft.Text(
                    "Crie um arquivo .env na raiz do projeto com:\n"
                    "DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD",
                    size=12,
                    color=tema.TEXT_MUTED,
                    selectable=True,
                ),
                ft.Container(height=4),
                ft.Text(
                    "Veja o arquivo .env.example como modelo.",
                    size=12,
                    color=tema.TEXT_MUTED,
                    italic=True,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )

    bancos = listar_bancos()
    dropdown = tema.dropdown_estilo("Selecione um banco", bancos)
    txt_erro = ft.Text("", color=tema.DANGER, size=13, visible=False)
    txt_conexao = ft.Text("", size=12, color=tema.TEAL, visible=False)
    btn = tema.btn_primario("Conectar", largura=320)

    def _testar_conexao(e):
        if not dropdown.value:
            txt_conexao.visible = False
            page.update()
            return
        txt_conexao.value = "⏳ Testando conexão..."
        txt_conexao.color = tema.TEXT_MUTED
        txt_conexao.visible = True
        page.update()

        def _run():
            from engine.conexao import configurar_banco, get_conexao

            try:
                configurar_banco(dropdown.value)
                conn = get_conexao()
                conn.close()
                txt_conexao.value = "✅ Conexão bem-sucedida"
                txt_conexao.color = tema.TEAL
            except Exception:
                txt_conexao.value = "❌ Falha na conexão — verifique as credenciais"
                txt_conexao.color = tema.DANGER
            txt_conexao.visible = True
            page.update()

        import threading

        threading.Thread(target=_run, daemon=True).start()

    dropdown.on_change = _testar_conexao

    def conectar(e):
        banco = dropdown.value
        if not banco:
            txt_erro.value = "Selecione um banco antes de continuar."
            txt_erro.visible = True
            page.update()
            return
        txt_erro.visible = False
        on_sucesso(banco)

    btn.on_click = conectar

    return ft.Column(
        [
            ft.Row(
                [
                    ft.IconButton(
                        ft.Icons.ARROW_BACK,
                        icon_color=tema.TEXT_MUTED,
                        on_click=lambda e: on_sucesso("__voltar__"),
                        tooltip="Voltar",
                    )
                ],
            ),
            ft.Column(
                [
                    ft.Container(expand=True),
                    tema.titulo_logo(),
                    ft.Container(height=24),
                    dropdown,
                    txt_conexao,
                    txt_erro,
                    ft.Container(height=4),
                    btn,
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
