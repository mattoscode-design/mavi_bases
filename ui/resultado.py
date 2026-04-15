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

    if not resultado.get("ok"):
        corpo = ft.Column(
            [
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=tema.DANGER, size=48),
                ft.Text("Erro no processamento", size=16, color=tema.DANGER),
                ft.Text(resultado.get("erro", ""), size=13, color=tema.TEXT_MUTED),
                ft.Container(height=16),
                tema.btn_outline("Tentar novamente", on_click=lambda e: on_voltar()),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )
    else:
        total_linhas = resultado.get("total_linhas", 0)
        lojas_unicas = resultado.get("lojas_unicas", 0)
        lojas_ok = resultado.get("lojas_ok", 0)
        lojas_novas = resultado.get("lojas_novas", 0)
        total_valor = resultado.get("total_valor", 0.0)
        total_quantidade = resultado.get("total_quantidade", 0.0)
        setores = resultado.get("setores", [])
        varejistas_novos = resultado.get("varejistas_novos", [])
        pendencias = resultado.get("pendencias", [])
        arquivo = resultado.get("arquivo_saida", "")

        # formata valor em R$
        def fmt_valor(v):
            try:
                return (
                    f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
            except Exception:
                return str(v)

        def fmt_num(v):
            try:
                return f"{v:,.0f}".replace(",", ".")
            except Exception:
                return str(v)

        # ── Stats principais ──────────────────────────────────────────────────
        stats_row1 = ft.Row(
            [
                _stat_card("Total de linhas", fmt_num(total_linhas)),
                _stat_card("Lojas únicas", str(lojas_unicas)),
                _stat_card("Identificadas", str(lojas_ok), cor=tema.TEAL),
                _stat_card(
                    "Lojas novas",
                    str(lojas_novas),
                    cor=tema.WARN if lojas_novas else tema.TEXT,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
            wrap=True,
        )

        stats_row2 = ft.Row(
            [
                _stat_card("Total VALOR", fmt_valor(total_valor), cor=tema.TEAL),
                _stat_card(
                    "Total QUANTIDADE", fmt_num(total_quantidade), cor=tema.TEAL
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )

        timings = resultado.get("timings", {})
        sorted_timings = sorted(
            [(name, t) for name, t in timings.items() if t is not None],
            key=lambda x: x[1],
            reverse=True,
        )
        etapa_mais_lenta = sorted_timings[0] if sorted_timings else None
        friendly_names = {
            "load_mapping": "Mapeamento",
            "read_excel": "Leitura",
            "drop_ignored": "Ignorar colunas",
            "separar_mes_ano": "Separar MÊS/ANO",
            "cruzar_loja": "Cruzar lojas",
            "cruzar_ean": "Cruzar EAN",
            "renomear": "Renomear",
            "calcular": "Calcular",
            "adicionar_novas": "Novas colunas",
            "sinalizar_pendencias": "Sinalizar pendências",
            "cruzar_varejista": "Cruzar varejistas",
            "exportar": "Exportar",
            "total": "Total",
        }
        stats_row3 = ft.Row(
            [
                _stat_card(
                    "Tempo total",
                    f"{timings.get('total', 0):.2f}s",
                    cor=tema.TEXT,
                ),
                _stat_card(
                    "Exportação",
                    f"{timings.get('exportar', 0):.2f}s",
                    cor=tema.TEXT,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )

        etapa_mais_lenta_text = ""
        if etapa_mais_lenta:
            nome_f = friendly_names.get(etapa_mais_lenta[0], etapa_mais_lenta[0])
            etapa_mais_lenta_text = (
                f"Etapa mais lenta: {nome_f} ({etapa_mais_lenta[1]:.2f}s)"
            )

        top_timings = []
        for name, t in sorted_timings[:3]:
            top_timings.append(f"{friendly_names.get(name, name)}: {t:.2f}s")
        detalhe_tempo = " | ".join(top_timings)

        # ── Setores ───────────────────────────────────────────────────────────
        setores_widget = ft.Container(visible=False)
        if setores:
            chips = ft.Row(
                [
                    ft.Container(
                        content=ft.Text(s, size=11, color=tema.TEAL),
                        bgcolor=tema.BG3,
                        border=ft.border.all(1, tema.TEAL),
                        border_radius=12,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    )
                    for s in setores[:12]  # mostra no máximo 12
                ],
                wrap=True,
                spacing=6,
            )
            setores_widget = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            f"Setores encontrados ({len(setores)})",
                            size=12,
                            color=tema.TEXT_MUTED,
                        ),
                        chips,
                    ],
                    spacing=6,
                ),
                bgcolor=tema.BG2,
                border=ft.border.all(1, tema.BORDER),
                border_radius=8,
                padding=12,
                width=560,
                visible=True,
            )

        # ── Aviso de lojas novas ──────────────────────────────────────────────
        aviso_varejistas = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.STORE_MALL_DIRECTORY, color=tema.WARN, size=20
                            ),
                            ft.Text(
                                f"{len(varejistas_novos)} varejista(s) não identificado(s) na base",
                                size=13,
                                color=tema.WARN,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        ", ".join(varejistas_novos[:8])
                        + ("…" if len(varejistas_novos) > 8 else ""),
                        size=11,
                        color=tema.TEXT_MUTED,
                    ),
                ],
                spacing=4,
            ),
            bgcolor="#1e1a0e",
            border=ft.border.all(1, tema.WARN),
            border_radius=8,
            padding=12,
            visible=len(varejistas_novos) > 0,
            width=560,
        )

        aviso = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER, color=tema.WARN, size=20),
                    ft.Text(
                        f"{lojas_novas} loja(s) nova(s) não identificada(s) — clique para vincular",
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
            on_click=lambda e: on_pendencias(cod_varejista),
            ink=True,
            visible=lojas_novas > 0,
            width=560,
        )

        corpo = ft.Column(
            [
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=tema.TEAL, size=44),
                ft.Text(
                    f"{nome_varejista.upper()} processado com sucesso",
                    size=15,
                    weight=ft.FontWeight.W_500,
                    color=tema.TEXT,
                ),
                ft.Container(height=4),
                stats_row1,
                stats_row2,
                stats_row3,
                ft.Text(etapa_mais_lenta_text, size=12, color=tema.TEXT_MUTED),
                ft.Text(detalhe_tempo, size=11, color=tema.TEXT_MUTED),
                setores_widget,
                aviso_varejistas,
                aviso,
                ft.Text(f"📄  {arquivo}", size=11, color=tema.TEXT_MUTED),
                ft.Container(height=4),
                tema.btn_primario(
                    "Abrir pasta de saída",
                    on_click=lambda e: subprocess.Popen(f'explorer "{PASTA_SAIDA}"'),
                    largura=240,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )

    return ft.Column(
        [
            tema.navbar("Resultado", banco, on_voltar=lambda e: on_voltar()),
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
                    label,
                    size=10,
                    color=tema.TEXT_MUTED,
                    weight=ft.FontWeight.W_500,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    valor,
                    size=20,
                    weight=ft.FontWeight.W_600,
                    color=cor or tema.TEXT,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=tema.BG2,
        border=ft.border.all(1, tema.BORDER),
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        width=130,
    )
