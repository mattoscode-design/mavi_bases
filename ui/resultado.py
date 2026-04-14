import flet as ft
import os
import subprocess
from ui import tema
from config import PASTA_SAIDA


def tela_resultado(
    page: ft.Page,
    resultado: dict,
    nome_varejista: str,
    cod_varejista: int,
    banco: str,
    on_voltar,
    on_pendencias,
):
    """Tela de resultado após processamento."""

    def voltar(e):
        on_voltar()

    navbar = ft.Row(
        [
            ft.IconButton(
                ft.Icons.ARROW_BACK, icon_color=tema.TEXT_MUTED, on_click=voltar
            ),
            ft.Text("Resultado", size=15, weight=ft.FontWeight.W_500, color=tema.TEXT),
            ft.Container(expand=True),
            ft.Text(banco, size=12, color=tema.TEXT_MUTED),
        ],
    )

    if not resultado.get("ok"):
        corpo = ft.Column(
            [
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=tema.DANGER, size=48),
                ft.Text("Erro no processamento", size=16, color=tema.DANGER),
                ft.Text(resultado.get("erro", ""), size=13, color=tema.TEXT_MUTED),
                ft.Container(height=16),
                tema.btn_outline("Tentar novamente", on_click=voltar),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )
    else:
        total = resultado.get("total_linhas", 0)
        ok = resultado.get("lojas_ok", 0)
        pendentes = len(resultado.get("pendencias", []))

        stats = ft.Row(
            [
                _stat_card("Total de linhas", str(total)),
                _stat_card("Lojas identificadas", str(ok), cor=tema.TEAL),
                _stat_card(
                    "Lojas novas",
                    str(pendentes),
                    cor=tema.WARN if pendentes else tema.TEXT,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
        )

        def abrir_pasta(e):
            subprocess.Popen(f'explorer "{PASTA_SAIDA}"')

        def ver_pendencias(e):
            on_pendencias(cod_varejista)

        botoes = ft.Row(
            [
                tema.btn_primario(
                    "Abrir pasta de saída", on_click=abrir_pasta, largura=220
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
        )

        aviso_pendencias = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER, color=tema.WARN, size=20),
                    ft.Text(
                        f"{pendentes} loja(s) não identificada(s) — clique para vincular",
                        size=13,
                        color=tema.WARN,
                    ),
                ],
                spacing=8,
            ),
            bgcolor="#1e1a0e",
            border=ft.border.all(1, tema.WARN),
            border_radius=8,
            padding=12,
            on_click=ver_pendencias,
            ink=True,
            visible=pendentes > 0,
        )

        arquivo = resultado.get("arquivo_saida", "")
        txt_arq = ft.Text(
            f"✅  {arquivo}",
            size=12,
            color=tema.TEAL,
        )

        corpo = ft.Column(
            [
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=tema.TEAL, size=48),
                ft.Text(
                    f"{nome_varejista.upper()} processado com sucesso",
                    size=15,
                    weight=ft.FontWeight.W_500,
                    color=tema.TEXT,
                ),
                ft.Container(height=8),
                stats,
                ft.Container(height=8),
                txt_arq,
                aviso_pendencias,
                ft.Container(height=8),
                botoes,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
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
                padding=24,
                alignment=ft.alignment.center,
            ),
        ],
        expand=True,
        spacing=0,
    )


def _stat_card(label: str, valor: str, cor: str = None) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    label, size=11, color=tema.TEXT_MUTED, weight=ft.FontWeight.W_500
                ),
                ft.Text(
                    valor, size=26, weight=ft.FontWeight.W_600, color=cor or tema.TEXT
                ),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=tema.BG2,
        border=ft.border.all(1, tema.BORDER),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        width=140,
    )
