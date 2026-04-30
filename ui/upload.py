import flet as ft
import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
from ui import tema
from engine.conexao import get_conexao
from engine.processador import processar_base, preview_base
from engine import mapeamento_loader
from config import PASTA_ENTRADA
from security.sanitizacao import sanitizar_nome_arquivo, validar_extensao_excel


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


def tela_upload(page: ft.Page, usuario: str, banco: str, on_voltar, on_resultado):
    varejistas = buscar_varejistas()
    arquivo_path = [None]
    processando = [False]
    cancelado = threading.Event()

    dd_varejista = ft.Dropdown(
        label="Varejista",
        options=[
            ft.dropdown.Option(key=str(v["cod_varejista"]), text=v["nome_varejista"])
            for v in varejistas
        ],
        width=420,
        bgcolor=tema.BG3,
        border_color=tema.BORDER,
        focused_border_color=tema.TEAL,
        label_style=ft.TextStyle(color=tema.TEAL, size=12),
        text_style=ft.TextStyle(color=tema.TEXT, size=14),
        border_radius=8,
    )

    txt_sem_mapeamento = ft.Text(
        "⚠️  Varejista sem mapeamento — configure antes de processar.",
        size=12,
        color=tema.WARN,
        visible=False,
    )

    def _checar_mapeamento(e):
        if not dd_varejista.value:
            txt_sem_mapeamento.visible = False
            page.update()
            return
        cfg = mapeamento_loader.carregar(int(dd_varejista.value))
        txt_sem_mapeamento.visible = cfg is None
        page.update()

    dd_varejista.on_change = _checar_mapeamento

    txt_arquivo = ft.Text("Nenhum arquivo selecionado", size=13, color=tema.TEXT_MUTED)
    txt_erro = ft.Text("", color=tema.DANGER, size=13, visible=False)
    txt_status = ft.Text("", size=12, color=tema.TEXT_MUTED, visible=False)
    barra_progresso = ft.ProgressBar(
        value=0,
        width=420,
        bar_height=6,
        color=tema.TEAL,
        bgcolor=tema.BG3,
        border_radius=4,
        visible=False,
    )

    def arquivo_selecionado():
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        caminho = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls")],
            title="Selecionar base Excel",
        )
        root.destroy()
        if caminho:
            arquivo_path[0] = caminho
            txt_arquivo.value = os.path.basename(caminho)
            txt_arquivo.color = tema.TEAL
            page.update()

    def atualizar_status(msg: str, progresso: float = None):
        txt_status.value = msg or ""
        txt_status.visible = bool(msg)
        if progresso is not None:
            barra_progresso.value = progresso
        page.update()

    def iniciar_processamento():
        if processando[0]:
            return

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

        if not validar_extensao_excel(arquivo_path[0]):
            txt_erro.value = "Somente arquivos .xlsx e .xls são permitidos."
            txt_erro.visible = True
            page.update()
            return

        processando[0] = True
        txt_erro.visible = False
        barra_progresso.value = 0
        barra_progresso.visible = True
        btn_processar.disabled = True
        btn_cancelar.visible = True
        page.update()

        navegou = [False]
        try:
            cod_varejista = int(dd_varejista.value)
            nome_varejista = next(
                o.text for o in dd_varejista.options if o.key == dd_varejista.value
            )

            arquivo_origem = arquivo_path[0]
            nome_seguro = sanitizar_nome_arquivo(os.path.basename(arquivo_origem))
            destino = os.path.join(
                PASTA_ENTRADA,
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{nome_seguro}",
            )
            shutil.copy(arquivo_origem, destino)

            resultado = processar_base(
                destino,
                cod_varejista,
                nome_varejista,
                on_status=atualizar_status,
            )
            if cancelado.is_set():
                return
            if not resultado.get("ok"):
                txt_erro.value = resultado.get("erro", "Erro desconhecido")
                txt_erro.visible = True
                page.update()
                return

            # Limpa UI antes de navegar para a próxima tela
            processando[0] = False
            barra_progresso.value = 0
            barra_progresso.visible = False
            btn_processar.disabled = False
            txt_status.visible = False
            page.update()
            navegou[0] = True
            on_resultado(resultado, nome_varejista, cod_varejista)

        except Exception as ex:
            print(f"[ERRO] processamento: {ex}")
            import traceback

            traceback.print_exc()
            txt_erro.value = "Ocorreu um erro durante o processamento."
            txt_erro.visible = True
            page.update()
        finally:
            cancelado.clear()
            if not navegou[0]:
                processando[0] = False
                barra_progresso.value = 0
                barra_progresso.visible = False
                btn_processar.disabled = False
                btn_cancelar.visible = False
                txt_status.visible = False
                page.update()

    btn_processar = tema.btn_primario("Processar base", largura=280)
    btn_processar.on_click = lambda e: threading.Thread(
        target=iniciar_processamento, daemon=True
    ).start()

    btn_preview = tema.btn_outline("Pré-visualizar (10 linhas)", largura=280)

    btn_cancelar = ft.OutlinedButton(
        "Cancelar processamento",
        visible=False,
        width=280,
        style=ft.ButtonStyle(
            color=tema.DANGER,
            side=ft.BorderSide(color=tema.DANGER, width=1),
            shape=ft.RoundedRectangleBorder(radius=20),
            padding=ft.padding.symmetric(vertical=12, horizontal=24),
        ),
    )

    def _cancelar(e):
        cancelado.set()
        btn_cancelar.disabled = True
        txt_status.value = "Cancelando após etapa atual..."
        txt_status.visible = True
        page.update()

    btn_cancelar.on_click = _cancelar

    def iniciar_preview(e):
        if not dd_varejista.value:
            txt_erro.value = "Selecione um varejista antes de pré-visualizar."
            txt_erro.visible = True
            page.update()
            return
        if not arquivo_path[0]:
            txt_erro.value = "Selecione um arquivo Excel antes de pré-visualizar."
            txt_erro.visible = True
            page.update()
            return

        txt_erro.visible = False
        txt_status.value = "Gerando pré-visualização..."
        txt_status.visible = True
        btn_preview.disabled = True
        page.update()

        def _run():
            try:
                cod = int(dd_varejista.value)
                res = preview_base(arquivo_path[0], cod)
            except Exception as ex:
                txt_erro.value = f"Erro na pré-visualização: {ex}"
                txt_erro.visible = True
                btn_preview.disabled = False
                txt_status.visible = False
                page.update()
                return

            btn_preview.disabled = False
            txt_status.visible = False

            if not res["ok"]:
                txt_erro.value = f"Erro na pré-visualização: {res['erro']}"
                txt_erro.visible = True
                page.update()
                return

            colunas = res["colunas"]
            linhas = res["linhas"]

            header_cells = [
                ft.DataColumn(
                    ft.Text(c, size=11, color=tema.TEAL, weight=ft.FontWeight.W_600)
                )
                for c in colunas
            ]
            rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(v), size=11, color=tema.TEXT))
                        for v in linha
                    ]
                )
                for linha in linhas
            ]

            tabela = ft.DataTable(
                columns=header_cells,
                rows=rows,
                border=ft.border.all(1, tema.BORDER),
                border_radius=8,
                column_spacing=16,
                data_row_min_height=32,
                heading_row_color={ft.ControlState.DEFAULT: tema.BG3},
            )

            btn_fechar = ft.TextButton(
                "Fechar",
                style=ft.ButtonStyle(color=tema.TEAL),
            )

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    f"Pré-visualização — {len(linhas)} linha(s)",
                    size=15,
                    color=tema.TEXT,
                    weight=ft.FontWeight.W_600,
                ),
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"{len(colunas)} colunas após transformações.",
                                size=12,
                                color=tema.TEXT_MUTED,
                            ),
                            ft.Container(height=8),
                            ft.Row(
                                [tabela],
                                scroll=ft.ScrollMode.ADAPTIVE,
                            ),
                        ],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=700,
                    height=420,
                ),
                actions=[btn_fechar],
                bgcolor=tema.BG2,
                shape=ft.RoundedRectangleBorder(radius=12),
            )

            def _fechar(_ev=None):
                dlg.open = False
                page.update()

            btn_fechar.on_click = _fechar

            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        threading.Thread(target=_run, daemon=True).start()

    btn_preview.on_click = iniciar_preview

    area_arquivo = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.UPLOAD_FILE, color=tema.TEAL, size=32),
                ft.Text(
                    "Clique para selecionar ou solte o arquivo aqui",
                    size=13,
                    color=tema.TEXT,
                ),
                ft.Text(".xlsx ou .xls", size=12, color=tema.TEXT_MUTED),
                txt_arquivo,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        width=420,
        height=140,
        bgcolor=tema.BG3,
        border=ft.border.all(1.5, tema.BORDER),
        border_radius=12,
        alignment=ft.alignment.Alignment.CENTER,
        on_click=lambda e: arquivo_selecionado(),
        ink=True,
    )

    return ft.Column(
        [
            tema.navbar("Tratamento de Bases", banco, on_voltar=on_voltar),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=16),
                        dd_varejista,
                        txt_sem_mapeamento,
                        ft.Container(height=12),
                        area_arquivo,
                        ft.Container(height=8),
                        txt_erro,
                        txt_status,
                        barra_progresso,
                        ft.Container(height=12),
                        btn_processar,
                        btn_cancelar,
                        ft.Container(height=6),
                        btn_preview,
                        ft.Container(expand=True),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                padding=24,
                expand=True,
            ),
        ],
        expand=True,
        spacing=0,
    )
