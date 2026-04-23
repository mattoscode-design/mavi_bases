import flet as ft
import pandas as pd
import shutil
import os
import threading
import tkinter as tk
from tkinter import filedialog
from ui import tema
from engine.conexao import get_conexao
from engine.grupos import carregar_grupos, excluir_grupo, salvar_grupo
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
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        colunas = {r["coluna_entrada"]: r for r in rows if r["coluna_entrada"]}
        novas = [
            {
                "coluna_saida": r["coluna_saida"],
                "tipo_acao": r["tipo_acao"],
                "formula": r["formula"] or "",
            }
            for r in rows
            if not r["coluna_entrada"]
            and r["tipo_acao"] in ("valor_fixo", "ano_atual", "calcular_quantidade")
        ]
        return {"colunas": colunas, "novas": novas}
    except Exception:
        return {"colunas": {}, "novas": []}


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


def abrir_gerenciador_grupos(page: ft.Page):
    """Abre o dialog de gerenciamento de grupos de varejistas (uso independente)."""
    todos_varejistas = buscar_varejistas()
    grupos_state = [carregar_grupos()]

    inp_nome_g = ft.TextField(
        hint_text="Nome do grupo...",
        width=220,
        dense=True,
        bgcolor=tema.BG3,
        border_color=tema.BORDER,
        focused_border_color=tema.TEAL,
        text_style=ft.TextStyle(color=tema.TEXT, size=12),
        border_radius=6,
    )
    cbs_todos = [
        (
            v["cod_varejista"],
            ft.Checkbox(
                label=v["nome_varejista"],
                value=False,
                active_color=tema.TEAL,
                label_style=ft.TextStyle(color=tema.TEXT, size=12),
            ),
        )
        for v in todos_varejistas
    ]
    grupos_col = ft.Column(spacing=4)
    aviso = ft.Text("", color=tema.DANGER, size=11, visible=False)

    def _render():
        grupos_col.controls.clear()
        for g in grupos_state[0]:
            cods = set(g["varejistas"])
            nomes = [
                v["nome_varejista"]
                for v in todos_varejistas
                if v["cod_varejista"] in cods
            ]
            preview = ", ".join(nomes[:4]) + ("\u2026" if len(nomes) > 4 else "")

            def _del(e, _id=g["id_grupo"]):
                excluir_grupo(_id)
                grupos_state[0] = carregar_grupos()
                _render()
                page.update()

            grupos_col.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        g["nome_grupo"],
                                        size=12,
                                        weight=ft.FontWeight.W_600,
                                        color=tema.TEAL,
                                    ),
                                    ft.Text(
                                        preview or "\u2014",
                                        size=10,
                                        color=tema.TEXT_MUTED,
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE,
                                icon_color=tema.DANGER,
                                icon_size=16,
                                tooltip="Excluir grupo",
                                on_click=_del,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=tema.BG3,
                    border=ft.border.all(1, tema.TEAL),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                )
            )
        if not grupos_state[0]:
            grupos_col.controls.append(
                ft.Text("Nenhum grupo criado.", size=11, color=tema.TEXT_MUTED)
            )
        page.update()

    _render()

    def _criar(e):
        nome = inp_nome_g.value.strip()
        if not nome:
            aviso.value = "Digite um nome para o grupo."
            aviso.visible = True
            page.update()
            return
        sels = [cod for cod, cb in cbs_todos if cb.value]
        if not sels:
            aviso.value = "Selecione ao menos um varejista."
            aviso.visible = True
            page.update()
            return
        aviso.visible = False
        salvar_grupo(nome, sels)
        inp_nome_g.value = ""
        for _, cb in cbs_todos:
            cb.value = False
        grupos_state[0] = carregar_grupos()
        _render()

    dlg = [None]

    def _fechar(e=None):
        dlg[0].open = False
        page.update()

    dlg[0] = ft.AlertDialog(
        title=ft.Text("Grupos de varejistas"),
        content=ft.Column(
            [
                ft.Text("Grupos salvos", size=11, color=tema.TEXT_MUTED),
                grupos_col,
                ft.Divider(color=tema.BORDER),
                ft.Text("Criar novo grupo", size=11, color=tema.TEXT_MUTED),
                inp_nome_g,
                ft.Column(
                    [cb for _, cb in cbs_todos],
                    scroll=ft.ScrollMode.AUTO,
                    height=max(80, min(200, len(cbs_todos) * 38)),
                ),
                aviso,
                ft.FilledButton(
                    "+ Criar grupo",
                    on_click=_criar,
                    style=ft.ButtonStyle(
                        bgcolor=tema.BG3,
                        color=tema.TEAL,
                        shape=ft.RoundedRectangleBorder(radius=6),
                        side=ft.BorderSide(color=tema.TEAL, width=1),
                    ),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            width=420,
            height=540,
            spacing=8,
        ),
        actions=[ft.TextButton("Fechar", on_click=_fechar)],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg[0])
    dlg[0].open = True
    page.update()


def tela_mapeamento(page: ft.Page, banco: str, on_voltar):
    """Tela principal de configuração — seleção de varejista + upload."""
    varejistas = buscar_varejistas()
    cods_destino = []

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

    btn_destinos = ft.OutlinedButton(
        "Aplicar em 1 varejista",
        style=ft.ButtonStyle(
            color=tema.TEAL,
            side=ft.BorderSide(color=tema.TEAL, width=1),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )

    def _atualizar_label_destinos():
        qtd = len(cods_destino)
        btn_destinos.text = (
            f"Aplicar em {qtd} varejista"
            if qtd == 1
            else f"Aplicar em {qtd} varejistas"
        )

    def _on_varejista_change(e):
        cods_destino.clear()
        if e.control.value and e.control.value.isdigit():
            cods_destino.append(int(e.control.value))
        _atualizar_label_destinos()
        page.update()

    dd_varejista.on_change = _on_varejista_change

    def _abrir_picker_destinos(e):
        if not dd_varejista.value or not dd_varejista.value.isdigit():
            tema.snackbar_erro(page, "Selecione primeiro um varejista base.")
            return

        cod_base = int(dd_varejista.value)
        selecionados = set(cods_destino) if cods_destino else {cod_base}
        selecionados.add(cod_base)

        checkboxes = [
            (
                v["cod_varejista"],
                ft.Checkbox(
                    label=v["nome_varejista"],
                    value=v["cod_varejista"] in selecionados,
                    active_color=tema.TEAL,
                ),
            )
            for v in varejistas
        ]

        for cod, cb in checkboxes:
            if cod == cod_base:
                cb.value = True
                cb.disabled = True

        dlg = [None]

        def _fechar():
            dlg[0].open = False
            page.update()

        def _confirmar(_ev):
            novos = [cod for cod, cb in checkboxes if cb.value]
            if cod_base not in novos:
                novos.append(cod_base)
            cods_destino[:] = sorted(set(novos))
            _atualizar_label_destinos()
            _fechar()

        dlg[0] = ft.AlertDialog(
            title=ft.Text("Selecionar varejistas de destino"),
            content=ft.Column(
                [
                    ft.Text(
                        "A configuração será salva para todos selecionados.",
                        size=11,
                        color=tema.TEXT_MUTED,
                    ),
                    ft.Column(
                        [cb for _, cb in checkboxes],
                        scroll=ft.ScrollMode.AUTO,
                        height=max(120, min(260, len(checkboxes) * 38)),
                    ),
                ],
                width=420,
                spacing=8,
            ),
            actions=[
                ft.TextButton("Confirmar", on_click=_confirmar),
                ft.TextButton("Cancelar", on_click=lambda _ev: _fechar()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg[0])
        dlg[0].open = True
        page.update()

    btn_destinos.on_click = _abrir_picker_destinos

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
            if cod_var not in cods_destino:
                cods_destino[:] = [cod_var]
                _atualizar_label_destinos()

            nome_var = next(
                o.text for o in dd_varejista.options if o.key == dd_varejista.value
            )
            nomes_destino = [
                o.text for o in dd_varejista.options if int(o.key) in set(cods_destino)
            ]
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
                cods_destino,
                nomes_destino,
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
                        ft.Container(height=4),
                        btn_destinos,
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
    cods_destino,
    nomes_destino,
    on_voltar_principal,
):
    """Tela de configuração das colunas."""

    todos_varejistas = buscar_varejistas()
    controles_col = []  # (col, dd_acao, inp_saida, inp_formula, btn_varejistas)
    novas_colunas = []  # colunas novas adicionadas pelo usuário
    novas_salvas = mapeamento_salvo.get("novas", [])

    def _abrir_picker_varejistas(inp_formula_ref, btn_ref):
        cod_selecionados = {
            int(x)
            for x in (inp_formula_ref.value or "").split("|")
            if x.strip().isdigit()
        }

        # ── checkboxes individuais ─────────────────────────────────────────
        checkboxes = [
            (
                v["cod_varejista"],
                ft.Checkbox(
                    label=v["nome_varejista"],
                    value=v["cod_varejista"] in cod_selecionados,
                    active_color=tema.TEAL,
                ),
            )
            for v in todos_varejistas
        ]
        cb_by_cod = {cod: cb for cod, cb in checkboxes}

        # ── grupos existentes ──────────────────────────────────────────────
        grupos_state = [carregar_grupos()]  # mutável para recarregar

        grupos_col = ft.Column(spacing=4)
        inp_novo_grupo = ft.TextField(
            hint_text="Nome do grupo...",
            width=180,
            dense=True,
            bgcolor=tema.BG3,
            border_color=tema.BORDER,
            focused_border_color=tema.TEAL,
            text_style=ft.TextStyle(color=tema.TEXT, size=12),
            border_radius=6,
        )

        def _render_grupos():
            grupos_col.controls.clear()
            for g in grupos_state[0]:
                cods = set(g["varejistas"])
                nomes = [
                    v["nome_varejista"]
                    for v in todos_varejistas
                    if v["cod_varejista"] in cods
                ]
                preview = ", ".join(nomes[:4]) + ("…" if len(nomes) > 4 else "")

                def _aplicar_grupo(e, _cods=cods):
                    for cod, cb in checkboxes:
                        cb.value = cod in _cods
                    page.update()

                def _excluir_grupo(e, _id=g["id_grupo"]):
                    excluir_grupo(_id)
                    grupos_state[0] = carregar_grupos()
                    _render_grupos()
                    page.update()

                grupos_col.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            g["nome_grupo"],
                                            size=12,
                                            weight=ft.FontWeight.W_600,
                                            color=tema.TEAL,
                                        ),
                                        ft.Text(
                                            preview or "—",
                                            size=10,
                                            color=tema.TEXT_MUTED,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.TextButton(
                                    "Aplicar",
                                    on_click=_aplicar_grupo,
                                    style=ft.ButtonStyle(color=tema.TEAL),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    icon_color=tema.DANGER,
                                    icon_size=16,
                                    tooltip="Excluir grupo",
                                    on_click=_excluir_grupo,
                                ),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=tema.BG3,
                        border=ft.border.all(1, tema.TEAL),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    )
                )

        _render_grupos()

        def _criar_grupo(e):
            nome = inp_novo_grupo.value.strip()
            if not nome:
                return
            selecionados = [cod for cod, cb in checkboxes if cb.value]
            if not selecionados:
                tema.snackbar_erro(
                    page, "Selecione ao menos um varejista para o grupo."
                )
                return
            salvar_grupo(nome, selecionados)
            inp_novo_grupo.value = ""
            grupos_state[0] = carregar_grupos()
            _render_grupos()
            page.update()

        dlg = [None]

        def _fechar_dlg():
            dlg[0].open = False
            page.update()

        def _confirmar(e):
            sels = "|".join(str(cod) for cod, cb in checkboxes if cb.value)
            inp_formula_ref.value = sels
            n = sum(1 for _, cb in checkboxes if cb.value)
            btn_ref.text = f"🏬 {n} var." if n else "🏬 Varejistas"
            _fechar_dlg()

        def _cancelar(e):
            _fechar_dlg()

        dlg[0] = ft.AlertDialog(
            title=ft.Text("Varejistas permitidos"),
            content=ft.Column(
                [
                    # ── Grupos ──────────────────────────────────────────────
                    ft.Text("Grupos salvos", size=11, color=tema.TEXT_MUTED),
                    grupos_col,
                    ft.Row(
                        [
                            inp_novo_grupo,
                            ft.FilledButton(
                                "+ Criar grupo",
                                on_click=_criar_grupo,
                                style=ft.ButtonStyle(
                                    bgcolor=tema.BG3,
                                    color=tema.TEAL,
                                    shape=ft.RoundedRectangleBorder(radius=6),
                                    side=ft.BorderSide(color=tema.TEAL, width=1),
                                ),
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Divider(color=tema.BORDER),
                    # ── Checkboxes individuais ───────────────────────────────
                    ft.Text(
                        "Varejistas individuais (vazio = todos)",
                        size=11,
                        color=tema.TEXT_MUTED,
                    ),
                    ft.Column(
                        [cb for _, cb in checkboxes],
                        scroll=ft.ScrollMode.AUTO,
                        height=max(80, min(220, len(checkboxes) * 40)),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                width=420,
                height=520,
                spacing=8,
            ),
            actions=[
                ft.TextButton("Confirmar", on_click=_confirmar),
                ft.TextButton("Cancelar", on_click=_cancelar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg[0])
        dlg[0].open = True
        page.update()

    # ── Gerenciador independente de grupos ─────────────────────────────────────
    def _abrir_gerenciador_grupos(e=None):
        grupos_state2 = [carregar_grupos()]
        inp_nome_g = ft.TextField(
            hint_text="Nome do grupo...",
            width=220,
            dense=True,
            bgcolor=tema.BG3,
            border_color=tema.BORDER,
            focused_border_color=tema.TEAL,
            text_style=ft.TextStyle(color=tema.TEXT, size=12),
            border_radius=6,
        )
        cbs_todos = [
            (
                v["cod_varejista"],
                ft.Checkbox(
                    label=v["nome_varejista"],
                    value=False,
                    active_color=tema.TEAL,
                    label_style=ft.TextStyle(color=tema.TEXT, size=12),
                ),
            )
            for v in todos_varejistas
        ]
        grupos_col2 = ft.Column(spacing=4)
        aviso2 = ft.Text("", color=tema.DANGER, size=11, visible=False)

        def _render2():
            grupos_col2.controls.clear()
            for g in grupos_state2[0]:
                cods = set(g["varejistas"])
                nomes = [
                    v["nome_varejista"]
                    for v in todos_varejistas
                    if v["cod_varejista"] in cods
                ]
                preview = ", ".join(nomes[:4]) + ("…" if len(nomes) > 4 else "")

                def _del(e, _id=g["id_grupo"]):
                    excluir_grupo(_id)
                    grupos_state2[0] = carregar_grupos()
                    _render2()
                    page.update()

                grupos_col2.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            g["nome_grupo"],
                                            size=12,
                                            weight=ft.FontWeight.W_600,
                                            color=tema.TEAL,
                                        ),
                                        ft.Text(
                                            preview or "—",
                                            size=10,
                                            color=tema.TEXT_MUTED,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    icon_color=tema.DANGER,
                                    icon_size=16,
                                    tooltip="Excluir grupo",
                                    on_click=_del,
                                ),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor=tema.BG3,
                        border=ft.border.all(1, tema.TEAL),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    )
                )
            if not grupos_state2[0]:
                grupos_col2.controls.append(
                    ft.Text("Nenhum grupo criado.", size=11, color=tema.TEXT_MUTED)
                )
            page.update()

        _render2()

        def _criar2(e):
            nome = inp_nome_g.value.strip()
            if not nome:
                aviso2.value = "Digite um nome para o grupo."
                aviso2.visible = True
                page.update()
                return
            sels = [cod for cod, cb in cbs_todos if cb.value]
            if not sels:
                aviso2.value = "Selecione ao menos um varejista."
                aviso2.visible = True
                page.update()
                return
            aviso2.visible = False
            salvar_grupo(nome, sels)
            inp_nome_g.value = ""
            for _, cb in cbs_todos:
                cb.value = False
            grupos_state2[0] = carregar_grupos()
            _render2()

        dlg2 = [None]

        def _fechar2(e=None):
            dlg2[0].open = False
            page.update()

        dlg2[0] = ft.AlertDialog(
            title=ft.Text("Gerenciar grupos de varejistas"),
            content=ft.Column(
                [
                    ft.Text("Grupos salvos", size=11, color=tema.TEXT_MUTED),
                    grupos_col2,
                    ft.Divider(color=tema.BORDER),
                    ft.Text("Criar novo grupo", size=11, color=tema.TEXT_MUTED),
                    inp_nome_g,
                    ft.Column(
                        [cb for _, cb in cbs_todos],
                        scroll=ft.ScrollMode.AUTO,
                        height=max(80, min(200, len(cbs_todos) * 38)),
                    ),
                    aviso2,
                    ft.FilledButton(
                        "+ Criar grupo",
                        on_click=_criar2,
                        style=ft.ButtonStyle(
                            bgcolor=tema.BG3,
                            color=tema.TEAL,
                            shape=ft.RoundedRectangleBorder(radius=6),
                            side=ft.BorderSide(color=tema.TEAL, width=1),
                        ),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                width=420,
                height=540,
                spacing=8,
            ),
            actions=[
                ft.TextButton("Fechar", on_click=_fechar2),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg2[0])
        dlg2[0].open = True
        page.update()

    btn_grupos = ft.OutlinedButton(
        "📂 Gerenciar grupos de varejistas",
        on_click=_abrir_gerenciador_grupos,
        style=ft.ButtonStyle(
            color=tema.TEAL,
            side=ft.BorderSide(color=tema.TEAL, width=1),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )

    # ── Linhas de colunas existentes ─────────────────────────────────────────
    linhas_cols = []
    for idx, col in enumerate(colunas):
        salvo = mapeamento_salvo.get("colunas", {}).get(col, {})
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
                if not (inp.value or "").strip():
                    inp.value = "MÊS|ANO"
            elif e.control.value == "cruzar_ean":
                inp.hint_text = "ex: SETOR_PRODUTO"
                if not (inp.value or "").strip():
                    inp.value = "SETOR_PRODUTO"
            elif e.control.value == "calcular_quantidade":
                inp.hint_text = "ex: QUANTIDADE"
                formula_inp.hint_text = "ex: VALOR/Preco Unit"
                if not (inp.value or "").strip():
                    inp.value = "QUANTIDADE"
            elif e.control.value == "cruzar_varejista":
                inp.hint_text = "ex: VAREJISTA_BANCO"
                if not (inp.value or "").strip():
                    inp.value = "VAREJISTA_BANCO"
            elif e.control.value == "renomear":
                inp.hint_text = "novo nome..."
                if not (inp.value or "").strip():
                    inp.value = col
            else:
                inp.hint_text = "novo nome..."
            page.update()
            if e.control.value == "renomear":
                inp.focus()

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
            ft.dropdown.Option(key="valor_fixo", text="Valor fixo"),
            ft.dropdown.Option(key="ano_atual", text="Ano atual"),
            ft.dropdown.Option(key="calcular_quantidade", text="Calcular QUANTIDADE"),
        ],
        value="valor_fixo",
        width=200,
        bgcolor=tema.BG3,
        border_color=tema.BORDER,
        focused_border_color=tema.TEAL,
        text_style=ft.TextStyle(color=tema.TEXT, size=13),
        border_radius=6,
        dense=True,
    )
    inp_nova_formula = ft.TextField(
        hint_text="Valor a preencher nas células...",
        width=200,
        bgcolor=tema.BG3,
        border_color=tema.BORDER,
        focused_border_color=tema.TEAL,
        text_style=ft.TextStyle(color=tema.TEXT, size=13),
        border_radius=6,
        dense=True,
        visible=True,
    )
    _col_opts = [ft.dropdown.Option(key=c, text=c) for c in colunas]

    lista_novas = ft.Column(spacing=6)

    def nova_tipo_change(e):
        v = e.control.value
        inp_nova_formula.visible = v == "valor_fixo"
        page.update()

    dd_nova_tipo.on_change = nova_tipo_change

    def _abrir_dlg_calc(nome, pre_valor=None, pre_divisor=None, on_confirm=None):
        dd_v = ft.Dropdown(
            label="Coluna VALOR (numerador)",
            options=_col_opts,
            value=pre_valor,
            width=260,
            bgcolor=tema.BG3,
            border_color=tema.BORDER,
            focused_border_color=tema.TEAL,
            text_style=ft.TextStyle(color=tema.TEXT, size=13),
            label_style=ft.TextStyle(color=tema.TEXT_MUTED, size=11),
            border_radius=6,
        )
        dd_d = ft.Dropdown(
            label="Coluna PREÇO/UN (divisor)",
            options=_col_opts,
            value=pre_divisor,
            width=260,
            bgcolor=tema.BG3,
            border_color=tema.BORDER,
            focused_border_color=tema.TEAL,
            text_style=ft.TextStyle(color=tema.TEXT, size=13),
            label_style=ft.TextStyle(color=tema.TEXT_MUTED, size=11),
            border_radius=6,
        )
        err_txt = ft.Text("", color=tema.DANGER, size=12, visible=False)

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=tema.BG2,
            title=ft.Text(
                f"Calcular QUANTIDADE — {nome}",
                size=14,
                weight=ft.FontWeight.W_600,
                color=tema.TEXT,
            ),
            content=ft.Column(
                [
                    ft.Text(
                        "Resultado = VALOR ÷ PREÇO/UN",
                        size=12,
                        color=tema.TEXT_MUTED,
                    ),
                    ft.Container(height=8),
                    dd_v,
                    ft.Container(height=6),
                    dd_d,
                    err_txt,
                ],
                tight=True,
                spacing=0,
                width=300,
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=tema.TEXT_MUTED),
                    on_click=lambda e: _fechar_dlg(dlg),
                ),
                ft.FilledButton(
                    "Confirmar",
                    style=ft.ButtonStyle(
                        bgcolor=tema.TEAL,
                        color=tema.BG,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda e: _confirmar_calc(
                        dlg, dd_v, dd_d, err_txt, on_confirm
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _fechar_dlg(dlg):
        dlg.open = False
        page.update()

    def _confirmar_calc(dlg, dd_v, dd_d, err_txt, on_confirm):
        col_v = dd_v.value or ""
        col_d = dd_d.value or ""
        if not col_v or not col_d:
            err_txt.value = "Selecione as duas colunas."
            err_txt.visible = True
            page.update()
            return
        dlg.open = False
        page.update()
        if on_confirm:
            on_confirm(col_v, col_d)

    def adicionar_nova(e):
        nome = inp_nova_nome.value.strip()
        if not nome:
            tema.snackbar_erro(page, "Digite o nome da coluna.")
            return
        tipo = dd_nova_tipo.value
        if tipo == "calcular_quantidade":

            def _on_confirm_calc(col_v, col_d):
                formula = f"{col_v}/{col_d}"
                _finalizar_nova(nome, tipo, formula)

            _abrir_dlg_calc(nome, on_confirm=_on_confirm_calc)
            return
        else:
            formula = inp_nova_formula.value.strip()
        _finalizar_nova(nome, tipo, formula)

    def _finalizar_nova(nome, tipo, formula):
        entry = {"coluna_saida": nome, "tipo_acao": tipo, "formula": formula}
        novas_colunas.append(entry)

        preview = {"ano_atual": "(ano atual)", "valor_fixo": formula or "—"}.get(
            tipo, formula
        )
        container = [None]

        def _excluir(e, _entry=entry, _c=container):
            novas_colunas.remove(_entry)
            lista_novas.controls.remove(_c[0])
            page.update()

        def _editar(e, _entry=entry, _c=container):
            novas_colunas.remove(_entry)
            lista_novas.controls.remove(_c[0])
            inp_nova_nome.value = _entry["coluna_saida"]
            dd_nova_tipo.value = _entry["tipo_acao"]
            inp_nova_formula.visible = _entry["tipo_acao"] == "valor_fixo"
            if _entry["tipo_acao"] == "calcular_quantidade":
                partes = (
                    _entry["formula"].split("/", 1)
                    if "/" in _entry["formula"]
                    else ["", ""]
                )
                pre_v = partes[0].strip()
                pre_d = partes[1].strip() if len(partes) > 1 else ""
                page.update()

                def _on_edit_confirm(
                    col_v,
                    col_d,
                    _nome=_entry["coluna_saida"],
                    _tipo=_entry["tipo_acao"],
                ):
                    _finalizar_nova(_nome, _tipo, f"{col_v}/{col_d}")

                _abrir_dlg_calc(
                    _entry["coluna_saida"],
                    pre_valor=pre_v,
                    pre_divisor=pre_d,
                    on_confirm=_on_edit_confirm,
                )
            else:
                inp_nova_formula.value = _entry["formula"]
                page.update()

        container[0] = ft.Container(
            content=ft.Row(
                [
                    ft.Text(nome, size=13, color=tema.TEAL, width=150),
                    ft.Text(tipo, size=12, color=tema.TEXT_MUTED, expand=True),
                    ft.Text(preview, size=12, color=tema.TEXT_MUTED, width=120),
                    ft.IconButton(
                        ft.Icons.EDIT_OUTLINED,
                        icon_color=tema.TEXT_MUTED,
                        icon_size=16,
                        tooltip="Editar",
                        on_click=_editar,
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_color=tema.DANGER,
                        icon_size=16,
                        tooltip="Excluir",
                        on_click=_excluir,
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=tema.BG2,
            border=ft.border.all(1, tema.TEAL),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
        )
        lista_novas.controls.append(container[0])
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

    # ── Pré-popula novas colunas salvas anteriormente ─────────────────────────
    for _nova_salva in novas_salvas:
        _finalizar_nova(
            _nova_salva["coluna_saida"],
            _nova_salva["tipo_acao"],
            _nova_salva["formula"],
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
            destinos = sorted(set(cods_destino or [cod_varejista]))
            for cod_destino in destinos:
                salvar_mapeamento(cod_destino, colunas_payload)

            if len(destinos) > 1:
                txt_salvo.value = (
                    f"✅ Configuração salva para {len(destinos)} varejistas!"
                )
            else:
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
            ft.Row(
                [
                    ft.Text(
                        f"Varejista: {nome_varejista}",
                        size=13,
                        color=tema.TEXT_MUTED,
                        weight=ft.FontWeight.W_500,
                        expand=True,
                    ),
                    ft.Text(
                        f"Destinos: {len(cods_destino or [cod_varejista])}",
                        size=12,
                        color=tema.TEXT_MUTED,
                    ),
                    btn_grupos,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=8),
            *linhas_cols,
            ft.Divider(color=tema.BORDER),
            ft.Text("Adicionar coluna nova", size=13, color=tema.TEXT_MUTED),
            ft.Row(
                [
                    inp_nova_nome,
                    dd_nova_tipo,
                    inp_nova_formula,
                    btn_adicionar,
                ],
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
