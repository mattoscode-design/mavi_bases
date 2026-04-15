import flet as ft
import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
from ui import tema
from engine.conexao import get_conexao
from engine.processador import processar_base
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

    def abrir_seletor_arquivo():
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        caminho = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls")],
            title="Selecionar base Excel",
        )
        root.destroy()
        return caminho

    def arquivo_selecionado():
        caminho = abrir_seletor_arquivo()
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
        page.update()

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
            if not resultado.get("ok"):
                txt_erro.value = resultado.get("erro", "Erro desconhecido")
                txt_erro.visible = True
                page.update()
                return

            on_resultado(resultado, nome_varejista, cod_varejista)

        except Exception as ex:
            txt_erro.value = f"Erro ao processar: {ex}"
            txt_erro.visible = True
            page.update()
        finally:
            processando[0] = False
            barra_progresso.value = 0
            barra_progresso.visible = False
            btn_processar.disabled = False
            txt_status.visible = False
            page.update()

    btn_processar = tema.btn_primario("Processar base", largura=280)
    btn_processar.on_click = lambda e: threading.Thread(
        target=iniciar_processamento, daemon=True
    ).start()

    area_arquivo = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.UPLOAD_FILE, color=tema.TEAL, size=32),
                ft.Text(
                    "Clique para selecionar arquivo Excel", size=13, color=tema.TEXT
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
                        ft.Container(height=12),
                        area_arquivo,
                        ft.Container(height=8),
                        txt_erro,
                        txt_status,
                        barra_progresso,
                        ft.Container(height=12),
                        btn_processar,
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
