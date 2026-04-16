import flet as ft
import os
import re
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog
from ui import tema


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
        mes_ref = resultado.get("mes_ref", "")
        coluna_varejista_saida = resultado.get("coluna_varejista_saida", "")

        arquivo_state = [arquivo]  # mutável — None após remoção

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

        # ── Linha 1: lojas ────────────────────────────────────────────────────
        stats_row1 = ft.Row(
            [
                _stat_card("Linhas processadas", fmt_num(total_linhas)),
                _stat_card("Lojas identificadas", str(lojas_ok), cor=tema.TEAL),
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

        # ── Linha 2: valores ──────────────────────────────────────────────────
        stats_row2 = ft.Row(
            [
                _stat_card(
                    "Total VALOR",
                    fmt_valor(total_valor) if total_valor else "—",
                    cor=tema.TEAL,
                ),
                _stat_card(
                    "Total QUANTIDADE",
                    fmt_num(total_quantidade) if total_quantidade else "—",
                    cor=tema.TEAL,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )

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
                    for s in setores[:12]
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

        # ── Avisos ────────────────────────────────────────────────────────────
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

        aviso_lojas = ft.Container(
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

        # ── Botões salvar ─────────────────────────────────────────────────────
        txt_salvo = ft.Text("", size=12, color=tema.TEAL, visible=False)

        def _escolher_pasta():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            pasta = filedialog.askdirectory(title="Selecionar pasta de destino")
            root.destroy()
            return pasta

        def salvar_base(e):
            if not arquivo_state[0] or not os.path.exists(arquivo_state[0]):
                txt_salvo.value = "Arquivo temporário já foi removido."
                txt_salvo.visible = True
                page.update()
                return
            pasta = _escolher_pasta()
            if not pasta:
                return
            pasta_base = os.path.join(pasta, "BASE")
            os.makedirs(pasta_base, exist_ok=True)
            var_safe = re.sub(r"[^\w]", "_", nome_varejista)
            nome_dest = (
                f"{var_safe}_{mes_ref}.xlsx" if mes_ref else f"{var_safe}_BASE.xlsx"
            )
            dst = os.path.join(pasta_base, nome_dest)
            try:
                shutil.copy2(arquivo_state[0], dst)
                try:
                    os.remove(arquivo_state[0])
                    arquivo_state[0] = None
                except Exception:
                    pass
                txt_salvo.value = f"✅ Salvo em BASE/{nome_dest}"
                txt_salvo.visible = True
                page.update()
                subprocess.Popen(["explorer", os.path.normpath(pasta_base)])
            except Exception as ex:
                txt_salvo.value = f"Erro ao salvar: {ex}"
                txt_salvo.visible = True
                page.update()

        def salvar_por_varejista(e):
            if not arquivo_state[0] or not os.path.exists(arquivo_state[0]):
                txt_salvo.value = "Arquivo temporário já foi removido."
                txt_salvo.visible = True
                page.update()
                return
            pasta = _escolher_pasta()
            if not pasta:
                return
            pasta_base = os.path.join(pasta, "BASE")
            os.makedirs(pasta_base, exist_ok=True)
            try:
                import pandas as pd

                # Lê sem dtype=str para preservar colunas numéricas como float
                # (evita converter 1234.56 → string "1234.56" com ponto)
                df_out = pd.read_excel(arquivo_state[0], sheet_name="BASE_TRATADA")
                col = coluna_varejista_saida
                if not col or col not in df_out.columns:
                    txt_salvo.value = "Coluna de varejista não encontrada no arquivo."
                    txt_salvo.visible = True
                    page.update()
                    return
                valores = [
                    v
                    for v in df_out[col].dropna().unique()
                    if str(v).strip() not in ("", "NÃO ENCONTRADO", "nan")
                ]
                if not valores:
                    txt_salvo.value = "Nenhum varejista encontrado para separar."
                    txt_salvo.visible = True
                    page.update()
                    return
                salvos = []
                for var in valores:
                    var_safe = re.sub(r"[^\w]", "_", str(var))
                    nome_dest = (
                        f"{var_safe}_{mes_ref}.xlsx"
                        if mes_ref
                        else f"{var_safe}_BASE.xlsx"
                    )
                    dst = os.path.join(pasta_base, nome_dest)
                    df_var = df_out[df_out[col] == var]
                    df_var.to_excel(dst, index=False)
                    salvos.append(nome_dest)
                try:
                    os.remove(arquivo_state[0])
                    arquivo_state[0] = None
                except Exception:
                    pass
                txt_salvo.value = f"✅ {len(salvos)} arquivo(s) salvos em BASE/"
                txt_salvo.visible = True
                page.update()
                subprocess.Popen(["explorer", os.path.normpath(pasta_base)])
            except Exception as ex:
                txt_salvo.value = f"Erro ao salvar: {ex}"
                txt_salvo.visible = True
                page.update()

        btn_salvar = tema.btn_primario(
            "💾 Salvar base tratada",
            on_click=salvar_base,
            largura=240,
        )

        btn_salvar_por_var = ft.OutlinedButton(
            "🏬 Baixar por varejista",
            on_click=salvar_por_varejista,
            visible=bool(coluna_varejista_saida),
            style=ft.ButtonStyle(
                color=tema.TEAL,
                side=ft.BorderSide(color=tema.TEAL, width=1),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
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
                setores_widget,
                aviso_varejistas,
                aviso_lojas,
                ft.Container(height=4),
                ft.Row(
                    [btn_salvar, btn_salvar_por_var],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                    wrap=True,
                ),
                txt_salvo,
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
                alignment=ft.alignment.Alignment.CENTER,
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
