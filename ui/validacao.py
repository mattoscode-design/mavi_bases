import flet as ft
import json
import os
from ui import tema
from engine.conexao import get_conexao
from engine.matcher import vincular_loja_manualmente


def carregar_pendencias(cod_varejista: int) -> list:
    pasta_temp = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
    caminho = os.path.join(pasta_temp, f"pendencias_{cod_varejista}.json")
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def buscar_lojas() -> list[dict]:
    try:
        conn = get_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id_loja,
                   COALESCE(NULLIF(TRIM(nome_loja), ''), CONCAT('Loja ', id_loja)) AS nome_loja
            FROM loja ORDER BY nome_loja
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception:
        return []


def tela_validacao(page: ft.Page, cod_varejista: int, banco: str, on_voltar):
    """Tela de vinculação de lojas pendentes."""

    pendencias = carregar_pendencias(cod_varejista)
    lojas = buscar_lojas()

    def voltar(e):
        on_voltar()

    navbar = ft.Row(
        [
            ft.IconButton(
                ft.Icons.ARROW_BACK, icon_color=tema.TEXT_MUTED, on_click=voltar
            ),
            ft.Text(
                "Lojas Pendentes", size=15, weight=ft.FontWeight.W_500, color=tema.TEXT
            ),
            ft.Container(expand=True),
            ft.Text(banco, size=12, color=tema.TEXT_MUTED),
        ],
    )

    if not pendencias:
        corpo = ft.Column(
            [
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=tema.TEAL, size=48),
                ft.Text("Nenhuma loja pendente!", size=16, color=tema.TEAL),
                ft.Container(height=8),
                tema.btn_outline("Voltar", on_click=voltar),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )
    else:
        linhas = []

        for p in pendencias:
            id_original = p.get("id_original", "—")
            nome_pdv = p.get("nome_pdv") or f"Loja {id_original}"
            status_txt = ft.Text("", size=13, color=tema.TEAL, visible=False)

            dd = ft.Dropdown(
                options=[
                    ft.dropdown.Option(
                        key=str(l["id_loja"]), text=f"{l['id_loja']} — {l['nome_loja']}"
                    )
                    for l in lojas
                ],
                hint_text="Selecione a loja...",
                width=260,
                bgcolor=tema.BG3,
                border_color=tema.BORDER,
                focused_border_color=tema.TEAL,
                text_style=ft.TextStyle(color=tema.TEXT, size=13),
                border_radius=8,
                dense=True,
            )

            def salvar(e, pendencia=p, dropdown=dd, status=status_txt):
                if not dropdown.value:
                    tema.snackbar_erro(page, "Selecione uma loja antes de salvar.")
                    return
                try:
                    vincular_loja_manualmente(
                        cod_varejista=cod_varejista,
                        nome_alias=pendencia.get("nome_pdv")
                        or pendencia.get("id_original", ""),
                        id_loja=int(dropdown.value),
                    )
                    status.value = "✅ Salvo"
                    status.visible = True
                    dropdown.disabled = True
                    page.update()
                except Exception as ex:
                    tema.snackbar_erro(page, f"Erro: {ex}")

            btn_salvar = ft.ElevatedButton(
                "Salvar",
                on_click=salvar,
                style=ft.ButtonStyle(
                    bgcolor={ft.ControlState.DEFAULT: tema.TEAL},
                    color={ft.ControlState.DEFAULT: "#000000"},
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                ),
            )

            linha = ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    str(id_original),
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                    color=tema.TEXT,
                                ),
                                ft.Text(nome_pdv, size=12, color=tema.TEXT_MUTED),
                            ],
                            spacing=2,
                            width=140,
                        ),
                        dd,
                        btn_salvar,
                        status_txt,
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=tema.BG2,
                border=ft.border.all(1, tema.BORDER),
                border_radius=8,
                padding=12,
            )
            linhas.append(linha)

        corpo = ft.Column(
            linhas,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )

    return ft.Column(
        [
            ft.Container(
                content=navbar,
                bgcolor=tema.BG2,
                border=ft.border.only(bottom=ft.BorderSide(1, tema.BORDER)),
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
            ),
            ft.Container(
                content=corpo,
                expand=True,
                padding=16,
            ),
        ],
        expand=True,
        spacing=0,
    )
