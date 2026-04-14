import flet as ft
import threading
import shutil
import os
from ui import tema
from engine.conexao import get_conexao
from config import PASTA_ENTRADA


def buscar_varejistas() -> list[dict]:
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


def tela_upload(page: ft.Page, usuario: str, banco: str, on_voltar, on_resultado):
    """
    Tela de upload de base Excel.
    on_resultado(resultado: dict, varejista: str, cod_varejista: int) chamado após processamento.
    """
    varejistas = buscar_varejistas()
    arquivo_path = [None]

    # ── Componentes ───────────────────────────────────────────────────────────
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

    txt_arquivo = ft.Text(
        "Nenhum arquivo selecionado",
        size=13,
        color=tema.TEXT_MUTED,
    )

    icone_arquivo = ft.Icon(ft.Icons.UPLOAD_FILE, color=tema.TEAL, size=32)

    area_arquivo = ft.Container(
        content=ft.Column(
            [
                icone_arquivo,
                ft.Text("Clique para selecionar o arquivo", size=14, color=tema.TEXT),
                ft.Text(".xlsx ou .xls", size=12, color=tema.TEXT_MUTED),
                txt_arquivo,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        width=400,
        height=140,
        bgcolor=tema.BG3,
        border=ft.border.all(1.5, tema.BORDER),
        border_radius=12,
        alignment=ft.alignment.center,
        on_click=lambda e: file_picker.pick_files(
            allowed_extensions=["xlsx", "xls"],
            dialog_title="Selecionar base Excel",
        ),
        ink=True,
    )

    txt_erro = ft.Text("", color=tema.DANGER, size=13, visible=False)
    progresso = ft.ProgressBar(
        width=400, visible=False, color=tema.TEAL, bgcolor=tema.BG3
    )
    txt_status = ft.Text("", size=13, color=tema.TEXT_MUTED, visible=False)
    btn_proc = tema.btn_primario("Processar Base", largura=400)

    # ── File picker ───────────────────────────────────────────────────────────
    def arquivo_selecionado(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            arquivo_path[0] = f.path
            txt_arquivo.value = f.name
            txt_arquivo.color = tema.TEAL
            area_arquivo.border = ft.border.all(1.5, tema.TEAL)
            page.update()

    file_picker = ft.FilePicker(on_result=arquivo_selecionado)
    page.overlay.append(file_picker)

    # ── Processar ─────────────────────────────────────────────────────────────
    def processar(e):
        if not dd_varejista.value:
            txt_erro.value = "Selecione um varejista."
            txt_erro.visible = True
            page.update()
            return

        if not arquivo_path[0]:
            txt_erro.value = "Selecione um arquivo Excel."
            txt_erro.visible = True
            page.update()
            return

        txt_erro.visible = False
        progresso.visible = True
        txt_status.value = "Processando..."
        txt_status.visible = True
        btn_proc.disabled = True
        page.update()

        def rodar():
            try:
                cod_var = int(dd_varejista.value)
                nome_var = dd_varejista.options[
                    [o.key for o in dd_varejista.options].index(dd_varejista.value)
                ].text.lower()

                nome_arq = f"{nome_var}_{os.path.basename(arquivo_path[0])}"
                destino = os.path.join(PASTA_ENTRADA, nome_arq)
                shutil.copy2(arquivo_path[0], destino)

                from engine.processador import processar_base

                resultado = processar_base(destino, cod_var, nome_var)

                # salva pendências
                if resultado.get("ok") and resultado.get("pendencias"):
                    import json

                    pasta_temp = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)), "temp"
                    )
                    os.makedirs(pasta_temp, exist_ok=True)
                    with open(
                        os.path.join(pasta_temp, f"pendencias_{cod_var}.json"),
                        "w",
                        encoding="utf-8",
                    ) as f:
                        json.dump(resultado["pendencias"], f, ensure_ascii=False)

                progresso.visible = False
                btn_proc.disabled = False
                txt_status.visible = False
                page.update()
                on_resultado(resultado, nome_var, cod_var)

            except Exception as ex:
                progresso.visible = False
                btn_proc.disabled = False
                txt_status.visible = False
                txt_erro.value = f"Erro: {ex}"
                txt_erro.visible = True
                page.update()

        threading.Thread(target=rodar, daemon=True).start()

    btn_proc.on_click = processar

    # ── Layout ────────────────────────────────────────────────────────────────
    def voltar(e):
        on_voltar()

    navbar = ft.Row(
        [
            ft.IconButton(
                ft.Icons.ARROW_BACK, icon_color=tema.TEXT_MUTED, on_click=voltar
            ),
            ft.Text(
                "Tratamento de Bases",
                size=15,
                weight=ft.FontWeight.W_500,
                color=tema.TEXT,
            ),
            ft.Container(expand=True),
            ft.Text(banco, size=12, color=tema.TEXT_MUTED),
        ],
        alignment=ft.MainAxisAlignment.START,
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
                content=ft.Column(
                    [
                        ft.Container(height=16),
                        dd_varejista,
                        ft.Container(height=8),
                        area_arquivo,
                        txt_erro,
                        progresso,
                        txt_status,
                        ft.Container(height=8),
                        btn_proc,
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
