import flet as ft
import pandas as pd
import shutil
import os
import threading
import tkinter as tk
from tkinter import filedialog
from ui import tema
from engine.conexao import get_conexao
from config import PASTA_ENTRADA

TIPOS_ACAO = [
    ("id_loja", "🏪 ID da loja (id_loja)"),
    ("matricula_loja", "🧾 Matrícula / Código da loja"),
    ("nome_loja", "🏷️ Nome do PDV"),
    ("renomear", "✏️  Renomear coluna"),
    ("cruzar_ean", "🔍 Cruzar EAN com banco"),
    ("separar_mes_ano", "📅 Separar MÊS e ANO"),
    ("calcular_quantidade", "🧮 Calcular QUANTIDADE"),
    ("manter", "✅ Manter como está"),
    ("ignorar", "❌ Ignorar coluna"),
    ("cruzar_varejista", "🏬 Cruzar varejista"),
]


def buscar_varejistas() -> list:
    try:
        conn = get_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT cod_varejista, nome_varejista FROM varejista ORDER BY nome_varejista"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception:
        return []


def carregar_mapeamento(cod_varejista: int) -> dict:
    try:
        conn = get_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT coluna_entrada, coluna_saida, tipo_acao, formula FROM mapeamento_colunas "
            "WHERE cod_varejista = %s ORDER BY ordem",
            (cod_varejista,),
        )
        rows = {
            r["coluna_entrada"]: r for r in cursor.fetchall() if r["coluna_entrada"]
        }
        cursor.close()
        conn.close()
        return rows
    except Exception:
        return {}


def salvar_mapeamento(cod_varejista: int, colunas: list):
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM mapeamento_colunas WHERE cod_varejista = %s", (cod_varejista,)
    )
    for ordem, col in enumerate(colunas):
        cursor.execute(
            """INSERT INTO mapeamento_colunas
               (cod_varejista, coluna_entrada, coluna_saida, tipo_acao, formula, ordem)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                cod_varejista,
                col.get("coluna_entrada"),
                col.get("coluna_saida", ""),
                col.get("tipo_acao", "manter"),
                col.get("formula", ""),
                ordem,
            ),
        )
    conn.commit()
    cursor.close()
    conn.close()


def tela_mapeamento(page: ft.Page, banco: str, on_voltar):
    """Tela principal de configuração — seleção de varejista + upload."""
    varejistas = buscar_varejistas()

    dd_varejista = ft.Dropdown(
        label="Varejista",
        options=[
            ft.dropdown.Option(key=str(v["cod_varejista"]), text=v["nome_varejista"])
            for v in varejistas
        ],
        width=400,
        bgcolor=tema.BG3,
        border_color=tema.BORDER,
        focused_border_color=tema.TEAL,
        label_style=ft.TextStyle(color=tema.TEAL, size=12),
        text_style=ft.TextStyle(color=tema.TEXT, size=14),
        border_radius=8,
    )

    txt_arquivo = ft.Text("Nenhum arquivo selecionado", size=13, color=tema.TEXT_MUTED)
    arquivo_path = [None]

    area_arquivo = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.TABLE_CHART, color=tema.TEAL, size=32),
                ft.Text(
                    "Clique para selecionar base de exemplo", size=13, color=tema.TEXT
                ),
                ft.Text(".xlsx ou .xls", size=12, color=tema.TEXT_MUTED),
                txt_arquivo,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        width=400,
        height=130,
        bgcolor=tema.BG3,
        border=ft.border.all(1.5, tema.BORDER),
        border_radius=12,
        alignment=ft.alignment.Alignment.CENTER,
        on_click=lambda e: arquivo_selecionado(),
        ink=True,
    )

    txt_erro = ft.Text("", color=tema.DANGER, size=13, visible=False)
    btn_ler = tema.btn_primario("Ler colunas →", largura=400)

    def abrir_seletor_arquivo():
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        caminho = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls")],
            title="Selecionar base de exemplo",
        )
        root.destroy()
        return caminho

    def arquivo_selecionado():
        caminho = abrir_seletor_arquivo()
        if caminho:
            arquivo_path[0] = caminho
            txt_arquivo.value = os.path.basename(caminho)
            txt_arquivo.color = tema.TEAL
            area_arquivo.border = ft.border.all(1.5, tema.TEAL)
            page.update()

    page.update()

    def ler_colunas(e):
        if not dd_varejista.value:
            txt_erro.value = "Selecione um varejista."
            txt_erro.visible = True
            page.update()
            return
        if not arquivo_path[0]:
            txt_erro.value = "Selecione um arquivo."
            txt_erro.visible = True
            page.update()
            return

        txt_erro.visible = False
        btn_ler.disabled = True
        page.update()

        try:
            cod_var = int(dd_varejista.value)
            nome_var = next(
                o.text for o in dd_varejista.options if o.key == dd_varejista.value
            )
            df = pd.read_excel(arquivo_path[0], nrows=3, dtype=str)
            colunas = list(df.columns.str.strip())
            amostra = df.head(3).fillna("").values.tolist()
            mapeamento_salvo = carregar_mapeamento(cod_var)

            btn_ler.disabled = False
            page.update()

            _abrir_configurador(
                page,
                banco,
                cod_var,
                nome_var,
                colunas,
                amostra,
                mapeamento_salvo,
                on_voltar,
            )
        except Exception as ex:
            txt_erro.value = f"Erro ao ler: {ex}"
            txt_erro.visible = True
            btn_ler.disabled = False
            page.update()

    btn_ler.on_click = ler_colunas

    return ft.Column(
        [
            tema.navbar(
                "Configurar Mapeamento", banco, on_voltar=lambda e: on_voltar()
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=16),
                        dd_varejista,
                        ft.Container(height=8),
                        area_arquivo,
                        txt_erro,
                        ft.Container(height=8),
                        btn_ler,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                expand=True,
                padding=16,
            ),
        ],
        expand=True,
        spacing=0,
    )


def _abrir_configurador(
    page,
    banco,
    cod_varejista,
    nome_varejista,
    colunas,
    amostra,
    mapeamento_salvo,
    on_voltar_principal,
):
    """Tela de configuração das colunas."""

    todos_varejistas = buscar_varejistas()
    controles_col = []  # (col, dd_acao, inp_saida, inp_formula, btn_varejistas)
    novas_colunas = []  # colunas novas adicionadas pelo usuário

    def _abrir_picker_varejistas(inp_formula_ref, btn_ref):
        cod_selecionados = {
            int(x)
            for x in (inp_formula_ref.value or "").split("|")
            if x.strip().isdigit()
        }
        checkboxes = [
            (
                v["cod_varejista"],
                ft.Checkbox(
                    label=v["nome_varejista"],
                    value=v["cod_varejista"] in cod_selecionados,
                ),
            )
            for v in todos_varejistas
        ]
        dlg = [None]

        def _confirmar(e):
            sels = "|".join(str(cod) for cod, cb in checkboxes if cb.value)
            inp_formula_ref.value = sels
            n = sum(1 for _, cb in checkboxes if cb.value)
            btn_ref.text = f"🏬 {n} var." if n else "🏬 Varejistas"
            dlg[0].open = False
            page.update()

        def _cancelar(e):
            dlg[0].open = False
            page.update()

        dlg[0] = ft.AlertDialog(
            title=ft.Text("Varejistas permitidos (vazio = todos)"),
            content=ft.Column(
                [cb for _, cb in checkboxes],
                scroll=ft.ScrollMode.AUTO,
                height=max(80, min(300, len(checkboxes) * 45)),
            ),
            actions=[
                ft.TextButton("Confirmar", on_click=_confirmar),
                ft.TextButton("Cancelar", on_click=_cancelar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dlg[0]
        dlg[0].open = True
        page.update()

    # ── Linhas de colunas existentes ─────────────────────────────────────────
    linhas_cols = []
    for idx, col in enumerate(colunas):
        salvo = mapeamento_salvo.get(col, {})
        amostra_vals = " | ".join(
            str(amostra[r][idx]) for r in range(min(3, len(amostra))) if amostra[r][idx]
        )

        dd_acao = ft.Dropdown(
            value=salvo.get("tipo_acao", "manter"),
            options=[ft.dropdown.Option(key=v, text=l) for v, l in TIPOS_ACAO],
            width=200,
            bgcolor=tema.BG3,
            border_color=tema.BORDER,
            focused_border_color=tema.TEAL,
            text_style=ft.TextStyle(color=tema.TEXT, size=12),
            border_radius=6,
            dense=True,
        )

        inp_saida = ft.TextField(
            value=salvo.get("coluna_saida", ""),
            hint_text="novo nome / MÊS|ANO",
            width=160,
            bgcolor=tema.BG3,
            border_color=tema.BORDER,
            focused_border_color=tema.TEAL,
            text_style=ft.TextStyle(color=tema.TEXT, size=12),
            border_radius=6,
            dense=True,
            visible=salvo.get("tipo_acao")
            in (
                "renomear",
                "separar_mes_ano",
                "cruzar_ean",
                "calcular_quantidade",
                "cruzar_varejista",
            ),
        )

        inp_formula = ft.TextField(
            value=salvo.get("formula", ""),
            hint_text="ex: VALOR/Preco Unit",
            width=180,
            bgcolor=tema.BG3,
            border_color=tema.BORDER,
            focused_border_color=tema.TEAL,
            text_style=ft.TextStyle(color=tema.TEXT, size=12),
            border_radius=6,
            dense=True,
            visible=salvo.get("tipo_acao") == "calcular_quantidade",
        )

        _n_var = sum(
            1 for x in salvo.get("formula", "").split("|") if x.strip().isdigit()
        )
        btn_varejistas = ft.ElevatedButton(
            f"🏬 {_n_var} var." if _n_var else "🏬 Varejistas",
            visible=salvo.get("tipo_acao") == "cruzar_varejista",
            style=ft.ButtonStyle(
                bgcolor=tema.BG3,
                color=tema.TEAL,
                shape=ft.RoundedRectangleBorder(radius=6),
                side=ft.BorderSide(color=tema.TEAL, width=1),
            ),
        )
        btn_varejistas.on_click = (
            lambda e, _i=inp_formula, _b=btn_varejistas: _abrir_picker_varejistas(
                _i, _b
            )
        )

        def on_acao_change(
            e, inp=inp_saida, formula_inp=inp_formula, btn_var=btn_varejistas
        ):
            inp.visible = e.control.value in (
                "renomear",
                "separar_mes_ano",
                "cruzar_ean",
                "calcular_quantidade",
                "cruzar_varejista",
            )
            formula_inp.visible = e.control.value == "calcular_quantidade"
            btn_var.visible = e.control.value == "cruzar_varejista"

            if e.control.value == "separar_mes_ano":
                inp.hint_text = "ex: MÊS|ANO"
            elif e.control.value == "cruzar_ean":
                inp.hint_text = "ex: SETOR_PRODUTO"
            elif e.control.value == "calcular_quantidade":
                inp.hint_text = "ex: QUANTIDADE"
                formula_inp.hint_text = "ex: VALOR/Preco Unit"
            elif e.control.value == "cruzar_varejista":
                inp.hint_text = "ex: VAREJISTA_BANCO"
            else:
                inp.hint_text = "novo nome..."
            page.update()

        dd_acao.on_change = on_acao_change
        controles_col.append((col, dd_acao, inp_saida, inp_formula, btn_varejistas))

        linhas_cols.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    col,
                                    size=13,
                                    weight=ft.FontWeight.W_500,
                                    color=tema.TEXT,
                                ),
                                ft.Text(
                                    amostra_vals or "—", size=11, color=tema.TEXT_MUTED
                                ),
                            ],
                            spacing=2,
                            width=170,
                        ),
                        dd_acao,
                        inp_saida,
                        inp_formula,
                        btn_varejistas,
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=tema.BG2,
                border=ft.border.all(1, tema.BORDER),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            )
        )

    # ── Adicionar coluna nova ─────────────────────────────────────────────────
    inp_nova_nome = ft.TextField(
        hint_text="Nome da coluna...",
        width=180,
        bgcolor=tema.BG3,
        border_color=tema.BORDER,
        focused_border_color=tema.TEAL,
        text_style=ft.TextStyle(color=tema.TEXT, size=13),
        border_radius=6,
        dense=True,
    )
    dd_nova_tipo = ft.Dropdown(
        options=[
            ft.dropdown.Option(key="vazia", text="Coluna vazia"),
            ft.dropdown.Option(key="valor_fixo", text="Valor fixo"),
            ft.dropdown.Option(key="ano_atual", text="Ano atual"),
            ft.dropdown.Option(key="calcular_quantidade", text="Calcular QUANTIDADE"),
        ],
        value="vazia",
        width=200,
        bgcolor=tema.BG3,
        border_color=tema.BORDER,
        focused_border_color=tema.TEAL,
        text_style=ft.TextStyle(color=tema.TEXT, size=13),
        border_radius=6,
        dense=True,
    )
    inp_nova_formula = ft.TextField(
        hint_text="Valor ou fórmula...",
        width=160,
        bgcolor=tema.BG3,
        border_color=tema.BORDER,
        focused_border_color=tema.TEAL,
        text_style=ft.TextStyle(color=tema.TEXT, size=13),
        border_radius=6,
        dense=True,
        visible=False,
    )

    lista_novas = ft.Column(spacing=6)

    def nova_tipo_change(e):
        inp_nova_formula.visible = e.control.value in (
            "valor_fixo",
            "calcular_quantidade",
        )
        page.update()

    dd_nova_tipo.on_change = nova_tipo_change

    def adicionar_nova(e):
        nome = inp_nova_nome.value.strip()
        if not nome:
            tema.snackbar_erro(page, "Digite o nome da coluna.")
            return
        tipo = dd_nova_tipo.value
        formula = inp_nova_formula.value.strip()
        novas_colunas.append(
            {"coluna_saida": nome, "tipo_acao": tipo, "formula": formula}
        )

        preview = {"vazia": "—", "ano_atual": "2026", "valor_fixo": formula or "—"}.get(
            tipo, "calculado"
        )
        lista_novas.controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(nome, size=13, color=tema.TEAL, width=160),
                        ft.Text(tipo, size=12, color=tema.TEXT_MUTED, width=180),
                        ft.Text(preview, size=12, color=tema.TEXT_MUTED),
                    ],
                    spacing=10,
                ),
                bgcolor=tema.BG2,
                border=ft.border.all(1, tema.TEAL),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
            )
        )
        inp_nova_nome.value = ""
        inp_nova_formula.value = ""
        page.update()

    btn_adicionar = ft.FilledButton(
        "+ Adicionar",
        on_click=adicionar_nova,
        style=ft.ButtonStyle(
            bgcolor=tema.BG3,
            color=tema.TEAL,
            shape=ft.RoundedRectangleBorder(radius=8),
            side=ft.BorderSide(color=tema.TEAL, width=1),
        ),
    )

    # ── Salvar ────────────────────────────────────────────────────────────────
    txt_salvo = ft.Text("", size=13, color=tema.TEAL, visible=False)

    def salvar(e):
        colunas_payload = []
        for col, dd, inp, inp_formula, _ in controles_col:
            tipo = dd.value
            payload = {
                "coluna_entrada": col,
                "coluna_saida": inp.value.strip() if inp.visible else col,
                "tipo_acao": tipo,
                "formula": (
                    inp_formula.value.strip()
                    if (inp_formula.visible or tipo == "cruzar_varejista")
                    else ""
                ),
            }
            if tipo == "ignorar":
                payload["coluna_saida"] = ""
                payload["formula"] = ""
            colunas_payload.append(payload)
        for nova in novas_colunas:
            colunas_payload.append(
                {
                    "coluna_entrada": None,
                    **nova,
                }
            )
        try:
            salvar_mapeamento(cod_varejista, colunas_payload)
            txt_salvo.value = "✅ Configuração salva!"
            txt_salvo.visible = True
            page.update()
        except Exception as ex:
            tema.snackbar_erro(page, f"Erro ao salvar: {ex}")

    btn_salvar = tema.btn_primario("💾 Salvar configuração", largura=300)
    btn_salvar.on_click = salvar

    # ── Layout ────────────────────────────────────────────────────────────────
    conteudo = ft.Column(
        [
            ft.Text(
                f"Varejista: {nome_varejista}",
                size=13,
                color=tema.TEXT_MUTED,
                weight=ft.FontWeight.W_500,
            ),
            ft.Container(height=8),
            *linhas_cols,
            ft.Divider(color=tema.BORDER),
            ft.Text("Adicionar coluna nova", size=13, color=tema.TEXT_MUTED),
            ft.Row(
                [inp_nova_nome, dd_nova_tipo, inp_nova_formula, btn_adicionar],
                spacing=8,
                wrap=True,
            ),
            lista_novas,
            ft.Container(height=8),
            ft.Row(
                [btn_salvar, txt_salvo],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
    )

    from ui.app_nav import ir_para_controle

    def voltar_para_mapeamento(e):
        ir_para_controle(page, tela_mapeamento(page, banco, on_voltar_principal))

    ir_para_controle(
        page,
        ft.Column(
            [
                tema.navbar(
                    "Configurar Colunas",
                    banco,
                    on_voltar=voltar_para_mapeamento,
                ),
                ft.Container(content=conteudo, expand=True, padding=16),
            ],
            expand=True,
            spacing=0,
        ),
    )
