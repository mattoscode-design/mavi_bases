import flet as ft
from ui import tema
from engine.conexao import get_conexao
from engine.matcher import vincular_loja_manualmente
from engine import pendencias_store


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


def buscar_aliases(cod_varejista: int) -> list[dict]:
    try:
        conn = get_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT nome_alias, id_loja FROM aliases_loja"
            " WHERE cod_varejista = %s ORDER BY nome_alias",
            (cod_varejista,),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception:
        return []


def remover_alias(cod_varejista: int, nome_alias: str):
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM aliases_loja WHERE cod_varejista = %s AND nome_alias = %s",
        (cod_varejista, nome_alias),
    )
    conn.commit()
    cursor.close()
    conn.close()


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

    # ── Agrupar pendências por varejista ──────────────────────────────────────
    grupos: dict[str, list] = {}
    for pend in pendencias:
        nome_var = pend.get("nome_varejista") or "Outros"
        grupos.setdefault(nome_var, []).append(pend)

    nomes_varejistas = list(grupos.keys())

    def _build_card(pendencia):
        selecionado = {"id": None}

        inp_busca = ft.TextField(
            hint_text="Buscar loja (id ou nome)...",
            bgcolor=tema.BG3,
            border_color=tema.BORDER,
            focused_border_color=tema.TEAL,
            text_style=ft.TextStyle(color=tema.TEXT, size=12),
            hint_style=ft.TextStyle(color=tema.TEXT_MUTED, size=12),
            border_radius=8,
            dense=True,
            width=320,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
        )

        lista_resultados = ft.Column(spacing=2, visible=False)

        label_selecionado = ft.Text("", size=12, color=tema.TEAL, italic=True)

        btn_row = ft.Row(spacing=10, wrap=True)
        row_container = ft.Container()

        def _filtrar(
            e,
            busca_ctrl=inp_busca,
            lista=lista_resultados,
            sel=selecionado,
            lbl=label_selecionado,
        ):
            termo = busca_ctrl.value.strip().lower()
            lista.controls.clear()
            if not termo:
                lista.visible = False
                busca_ctrl.page.update()
                return
            filtradas = [
                l
                for l in lojas
                if termo in str(l["id_loja"]).lower() or termo in l["nome_loja"].lower()
            ][:15]
            for loja in filtradas:
                texto = f"{loja['id_loja']} — {loja['nome_loja']}"
                lista.controls.append(
                    ft.Container(
                        content=ft.Text(texto, size=12, color=tema.TEXT),
                        bgcolor=tema.BG3,
                        border=ft.border.all(1, tema.BORDER),
                        border_radius=6,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                        on_click=lambda ev, l=loja, bc=busca_ctrl, ls=lista, s=sel, lb=lbl: _selecionar(
                            l, bc, ls, s, lb
                        ),
                        ink=True,
                    )
                )
            lista.visible = bool(filtradas)
            busca_ctrl.page.update()

        def _selecionar(loja, busca_ctrl, lista, sel, lbl):
            sel["id"] = loja["id_loja"]
            busca_ctrl.value = f"{loja['id_loja']} — {loja['nome_loja']}"
            lbl.value = f"✔ Selecionado: {loja['id_loja']} — {loja['nome_loja']}"
            lista.visible = False
            busca_ctrl.page.update()

        inp_busca.on_change = _filtrar

        btn_vincular = tema.btn_primario(
            "Vincular",
            on_click=lambda e, pend=pendencia, sel=selecionado, cont=row_container: _vincular(
                e, pend, sel, cont
            ),
            largura=120,
        )
        btn_row.controls.extend([inp_busca, btn_vincular])

        row_container.content = ft.Column(
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
                btn_row,
                lista_resultados,
                label_selecionado,
            ],
            spacing=10,
        )
        row_container.bgcolor = tema.BG2
        row_container.border = ft.border.all(1, tema.BORDER)
        row_container.border_radius = 12
        row_container.padding = ft.padding.symmetric(horizontal=14, vertical=14)
        row_container.margin = ft.margin.only(bottom=10)
        return row_container

    def _vincular(e, pend, sel, cont):
        if not sel.get("id"):
            tema.snackbar_erro(page, "Selecione uma loja antes de vincular.")
            return

        nome_alias = (
            pend.get("nome_pdv") or pend.get("id_original") or pend.get("matricula")
        )
        if not nome_alias:
            tema.snackbar_erro(
                page, "Não há valor de alias disponível para esta pendência."
            )
            return

        pend_cod_var = pend.get("cod_varejista") or cod_varejista
        try:
            vincular_loja_manualmente(pend_cod_var, nome_alias, int(sel["id"]))
            cont.bgcolor = "#1b431a"
            cont.content.controls[-3].controls[1].disabled = True
            cont.content.controls[-3].controls[1].text = "✅ Vinculado"
            chave = pend.get("chave")
            restantes = [
                p for p in pendencias_store.carregar(banco) if p.get("chave") != chave
            ]
            pendencias_store.salvar(banco, restantes)
            tema.snackbar_sucesso(page, "Vinculação salva com sucesso.")
            page.update()
        except Exception as ex:
            tema.snackbar_erro(page, f"Erro ao vincular loja: {ex}")

    # ── Seções por varejista ───────────────────────────────────────────────────
    group_sections: dict[str, ft.Container] = {}
    secoes_lista = []
    for nome_var, pends in grupos.items():
        cards = [_build_card(p) for p in pends]
        qtd = len(pends)
        secao = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(
                            f"🏷  {nome_var}  —  {qtd} pendência{'s' if qtd != 1 else ''}",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=tema.TEAL,
                        ),
                        bgcolor=tema.BG3,
                        border=ft.border.all(1, tema.TEAL),
                        border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=6),
                        margin=ft.margin.only(bottom=8),
                    ),
                    *cards,
                ],
                spacing=4,
            ),
            visible=True,
        )
        group_sections[nome_var] = secao
        secoes_lista.append(secao)

    # ── Chips de filtro (só aparece se há mais de 1 varejista) ────────────────
    filtro_ativo = [None]
    chips_row = ft.Container(visible=False)
    if len(nomes_varejistas) > 1:
        chip_controls = []

        def _make_chip(nome):
            def _on_click(e, n=nome):
                if filtro_ativo[0] == n:
                    filtro_ativo[0] = None
                    for sec in group_sections.values():
                        sec.visible = True
                else:
                    filtro_ativo[0] = n
                    for vn, sec in group_sections.items():
                        sec.visible = vn == n
                for chip in chip_controls:
                    chip.bgcolor = (
                        tema.TEAL if chip.data == filtro_ativo[0] else tema.BG3
                    )
                    chip.content.color = (
                        "#000000" if chip.data == filtro_ativo[0] else tema.TEXT
                    )
                page.update()

            chip = ft.Container(
                content=ft.Text(nome, size=12, color=tema.TEXT),
                bgcolor=tema.BG3,
                border=ft.border.all(1, tema.BORDER),
                border_radius=16,
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                on_click=_on_click,
                ink=True,
                data=nome,
            )
            return chip

        for nv in nomes_varejistas:
            chip_controls.append(_make_chip(nv))

        chips_row = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Filtrar por varejista:", size=12, color=tema.TEXT_MUTED),
                    ft.Row(chip_controls, wrap=True, spacing=8),
                ],
                spacing=6,
            ),
            margin=ft.margin.only(bottom=12),
            visible=True,
        )

    # ── Histórico de aliases ──────────────────────────────────────────────────
    aliases_col = ft.Column(spacing=4, visible=False)
    aliases_expandido = [False]

    def _carregar_aliases():
        aliases_col.controls.clear()
        aliases = buscar_aliases(cod_varejista)
        if not aliases:
            aliases_col.controls.append(
                ft.Text(
                    "Nenhum alias vinculado para este varejista.",
                    size=12,
                    color=tema.TEXT_MUTED,
                )
            )
        else:
            for al in aliases:

                def _del(e, alias=al["nome_alias"]):
                    try:
                        remover_alias(cod_varejista, alias)
                        _carregar_aliases()
                        page.update()
                    except Exception as ex:
                        tema.snackbar_erro(page, f"Erro ao remover: {ex}")

                aliases_col.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(
                                    al["nome_alias"],
                                    size=12,
                                    color=tema.TEXT,
                                    expand=True,
                                ),
                                ft.Text(
                                    f"→ loja {al['id_loja']}",
                                    size=11,
                                    color=tema.TEXT_MUTED,
                                ),
                                ft.Container(width=8),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE,
                                    icon_color=tema.DANGER,
                                    icon_size=16,
                                    tooltip="Remover alias",
                                    on_click=_del,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        bgcolor=tema.BG3,
                        border=ft.border.all(1, tema.BORDER),
                        border_radius=6,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    )
                )

    btn_aliases = ft.TextButton(
        "▼  Ver aliases vinculados",
        style=ft.ButtonStyle(color=tema.TEXT_MUTED),
    )

    def _toggle_aliases(e):
        aliases_expandido[0] = not aliases_expandido[0]
        if aliases_expandido[0]:
            _carregar_aliases()
            aliases_col.visible = True
            btn_aliases.text = "▲  Ocultar aliases vinculados"
        else:
            aliases_col.visible = False
            btn_aliases.text = "▼  Ver aliases vinculados"
        page.update()

    btn_aliases.on_click = _toggle_aliases

    aliases_section = ft.Container(
        content=ft.Column(
            [
                ft.Divider(color=tema.BORDER),
                btn_aliases,
                aliases_col,
            ],
            spacing=6,
        ),
        margin=ft.margin.only(top=8),
    )

    # ── Layout final ──────────────────────────────────────────────────────────
    total = len(pendencias)
    cabecalho = ft.Column(
        [
            ft.Text(
                "Lojas Pendentes", size=20, weight=ft.FontWeight.W_700, color=tema.TEXT
            ),
            ft.Text(
                f"{total} loja{'s' if total != 1 else ''} aguardando vinculação manual.",
                size=13,
                color=tema.TEXT_MUTED,
            ),
        ],
        spacing=6,
    )

    conteudo = ft.Column(
        [
            cabecalho,
            ft.Container(height=12),
            chips_row,
            *secoes_lista,
            aliases_section,
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
