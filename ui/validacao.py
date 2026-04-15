import flet as ft
from ui import tema
from engine.conexao import get_conexao
from engine.matcher import vincular_loja_manualmente


def buscar_lojas() -> list[dict]:
    try:
        conn = get_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_loja, nome_loja FROM loja ORDER BY id_loja")
        lojas = cursor.fetchall()
        cursor.close()
        conn.close()
        return lojas
    except Exception:
        return []


def tela_validacao(
    page: ft.Page,
    cod_varejista: int,
    banco: str,
    pendencias: list,
    on_voltar,
):
    lojas = buscar_lojas()

    if not pendencias:
        aviso = ft.Column(
            [
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=44, color=tema.TEAL),
                ft.Text(
                    "Sem pendências",
                    size=18,
                    weight=ft.FontWeight.W_600,
                    color=tema.TEXT,
                ),
                ft.Text(
                    "Nenhuma loja pendente foi encontrada na última base processada.",
                    size=13,
                    color=tema.TEXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=20),
                tema.btn_primario("Voltar ao menu", on_click=lambda e: on_voltar()),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        return ft.Column(
            [
                tema.navbar("Lojas Pendentes", banco, on_voltar=on_voltar),
                ft.Container(
                    content=aviso,
                    expand=True,
                    alignment=ft.alignment.Alignment.CENTER,
                    padding=24,
                ),
            ],
            expand=True,
            spacing=0,
        )

    if not lojas:
        tema.snackbar_erro(page, "Não foi possível carregar a lista de lojas do banco.")

    itens = []
    for pendencia in pendencias:
        dd_lojas = ft.Dropdown(
            options=[
                ft.dropdown.Option(
                    key=str(loja["id_loja"]),
                    text=f"{loja['id_loja']} - {loja['nome_loja']}",
                )
                for loja in lojas
            ],
            width=260,
            bgcolor=tema.BG3,
            border_color=tema.BORDER,
            focused_border_color=tema.TEAL,
            text_style=ft.TextStyle(color=tema.TEXT, size=12),
            border_radius=8,
            dense=True,
        )

        row_container = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                f"ID original: {pendencia.get('id_original', 'NÃO IDENTIFICADO')}",
                                size=12,
                                color=tema.TEXT,
                            ),
                        ]
                    ),
                    ft.Row(
                        [
                            ft.Text(
                                f"Matrícula: {pendencia.get('matricula', '')}",
                                size=12,
                                color=tema.TEXT_MUTED,
                            ),
                            ft.Container(width=20),
                            ft.Text(
                                f"Nome PDV: {pendencia.get('nome_pdv', '')}",
                                size=12,
                                color=tema.TEXT_MUTED,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=10,
                        wrap=True,
                    ),
                    ft.Row(
                        [
                            dd_lojas,
                            tema.btn_primario(
                                "Vincular",
                                on_click=lambda e, pend=pendencia, dd=dd_lojas, cont=row_container: vincular(
                                    e, pend, dd, cont
                                ),
                                largura=120,
                            ),
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                ],
                spacing=10,
            ),
            bgcolor=tema.BG2,
            border=ft.border.all(1, tema.BORDER),
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=14, vertical=14),
            margin=ft.margin.only(bottom=10),
        )

        itens.append(row_container)

    def vincular(e, pend, dd, cont):
        if not dd.value:
            tema.snackbar_erro(page, "Selecione uma loja para vincular.")
            return

        nome_alias = (
            pend.get("nome_pdv") or pend.get("id_original") or pend.get("matricula")
        )
        if not nome_alias:
            tema.snackbar_erro(
                page, "Não há valor de alias disponível para esta pendência."
            )
            return

        try:
            vincular_loja_manualmente(cod_varejista, nome_alias, int(dd.value))
            cont.bgcolor = "#1b431a"
            cont.content.controls[-1].controls[1].disabled = True
            tema.snackbar_sucesso(page, "Vinculação salva com sucesso.")
            page.update()
        except Exception as ex:
            tema.snackbar_erro(page, f"Erro ao vincular loja: {ex}")

    cabecalho = ft.Column(
        [
            ft.Text(
                "Lojas Pendentes", size=20, weight=ft.FontWeight.W_700, color=tema.TEXT
            ),
            ft.Text(
                "Selecione a loja correta e vincule para que ela passe a ser reconhecida automaticamente.",
                size=13,
                color=tema.TEXT_MUTED,
                text_align=ft.TextAlign.LEFT,
            ),
        ],
        spacing=6,
    )

    conteudo = ft.Column(
        [
            cabecalho,
            ft.Container(height=16),
            *itens,
            ft.Container(height=14),
            tema.btn_primario("Voltar ao menu", on_click=lambda e: on_voltar()),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Column(
        [
            tema.navbar("Lojas Pendentes", banco, on_voltar=on_voltar),
            ft.Container(content=conteudo, expand=True, padding=20),
        ],
        expand=True,
        spacing=0,
    )
