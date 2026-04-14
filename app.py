import flet as ft
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import tema
from ui.login import tela_login
from ui.banco import tela_banco
from ui.modulos import tela_modulos
from ui.upload import tela_upload
from ui.resultado import tela_resultado
from ui.validacao import tela_validacao
from security import audit, limpeza
from config import PASTA_ENTRADA, PASTA_SAIDA


def main(page: ft.Page):
    page.title = "Mavi Bases"
    page.window.width = 800
    page.window.height = 650
    page.window.min_width = 600
    page.window.min_height = 480
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = tema.BG
    page.padding = 0
    page.theme = tema.TEMA

    # limpa arquivos antigos ao iniciar
    limpeza.limpar_entradas_antigas(PASTA_ENTRADA, horas=24)
    limpeza.limpar_saidas_antigas(PASTA_SAIDA, dias=30)

    sessao = {
        "usuario": "",
        "banco": "",
        "cod_varejista": None,
        "resultado": None,
        "nome_varejista": "",
    }

    def ir_para(tela_fn):
        page.controls.clear()
        page.controls.append(tela_fn())
        page.update()

    # ── Intercepta fechamento da janela ───────────────────────────────────────
    def ao_fechar(e):
        if sessao["usuario"]:
            audit.registrar(
                usuario=sessao["usuario"],
                acao="LOGOUT",
                banco=sessao["banco"],
                detalhe="Janela fechada",
            )
        # limpa arquivos temporários ao sair
        pasta_temp = os.path.join(os.path.dirname(__file__), "temp")
        limpeza.limpar_temp(pasta_temp)

    page.window.on_event = ao_fechar

    # ── Navegação ─────────────────────────────────────────────────────────────

    def para_login():
        ir_para(lambda: tela_login(page, on_login))

    def on_login(usuario: str):
        sessao["usuario"] = usuario
        audit.registrar(usuario=usuario, acao="LOGIN")
        ir_para(lambda: tela_banco(page, usuario, on_banco))

    def on_banco(banco: str):
        sessao["banco"] = banco
        audit.registrar(
            usuario=sessao["usuario"],
            acao="BANCO_SELECIONADO",
            banco=banco,
        )
        ir_para(lambda: tela_modulos(page, sessao["usuario"], banco, on_modulo))

    def on_modulo(modulo: str):
        if modulo == "banco":
            ir_para(lambda: tela_banco(page, sessao["usuario"], on_banco))

        elif modulo == "upload":
            ir_para(
                lambda: tela_upload(
                    page,
                    sessao["usuario"],
                    sessao["banco"],
                    on_voltar=lambda: on_modulo("menu"),
                    on_resultado=on_resultado,
                )
            )

        elif modulo == "mapeamento":
            from ui.mapeamento import tela_mapeamento

            ir_para(
                lambda: tela_mapeamento(
                    page,
                    sessao["banco"],
                    on_voltar=lambda: on_modulo("menu"),
                )
            )

        elif modulo == "validacao":
            ir_para(
                lambda: tela_validacao(
                    page,
                    sessao["cod_varejista"] or 1,
                    sessao["banco"],
                    on_voltar=lambda: on_modulo("menu"),
                )
            )

        elif modulo == "menu":
            ir_para(
                lambda: tela_modulos(
                    page, sessao["usuario"], sessao["banco"], on_modulo
                )
            )

    def on_resultado(resultado: dict, nome_varejista: str, cod_varejista: int):
        sessao["resultado"] = resultado
        sessao["nome_varejista"] = nome_varejista
        sessao["cod_varejista"] = cod_varejista

        # audit log do processamento
        audit.registrar(
            usuario=sessao["usuario"],
            acao="BASE_PROCESSADA",
            varejista=nome_varejista,
            banco=sessao["banco"],
            detalhe=(
                f"linhas={resultado.get('total_linhas', 0)} "
                f"lojas_ok={resultado.get('lojas_ok', 0)} "
                f"pendencias={len(resultado.get('pendencias', []))}"
            ),
        )

        # deleta arquivo de entrada após processar
        from config import PASTA_ENTRADA

        arq_entrada = os.path.join(
            PASTA_ENTRADA,
            f"{nome_varejista}_{resultado.get('arquivo_saida', '').replace('_tratado', '')}",
        )
        limpeza.deletar_arquivo_seguro(arq_entrada)

        ir_para(
            lambda: tela_resultado(
                page,
                resultado,
                nome_varejista,
                cod_varejista,
                sessao["banco"],
                on_voltar=lambda: on_modulo("upload"),
                on_pendencias=lambda cod: on_modulo("validacao"),
            )
        )

    para_login()


if __name__ == "__main__":
    ft.app(target=main)
