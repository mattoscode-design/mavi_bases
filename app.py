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

    limpeza.limpar_entradas_antigas(PASTA_ENTRADA, horas=24)
    limpeza.limpar_saidas_antigas(PASTA_SAIDA, dias=30)

    sessao = {
        "usuario": "",
        "banco": "",
        "cod_varejista": None,
        "resultado": None,
        "nome_varejista": "",
        "pendencias": [],
    }

    def ir_para(tela_fn):
        page.controls.clear()
        page.controls.append(tela_fn())
        page.update()

    def para_login():
        ir_para(lambda: tela_login(page, on_login))

    def on_login(usuario: str):
        sessao["usuario"] = usuario
        audit.registrar(usuario=usuario, acao="LOGIN")
        ir_para(lambda: tela_banco(page, usuario, on_banco))

    def on_banco(banco: str):
        if banco == "__voltar__":
            para_login()
            return
        sessao["banco"] = banco
        audit.registrar(
            usuario=sessao["usuario"], acao="BANCO_SELECIONADO", banco=banco
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
                    sessao.get("pendencias", []),
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

        novas_pendencias = resultado.get("pendencias", [])
        existentes = {p.get("chave") for p in sessao.get("pendencias", [])}
        sessao["pendencias"] = [
            *sessao.get("pendencias", []),
            *[p for p in novas_pendencias if p.get("chave") not in existentes],
        ]

        audit.registrar(
            usuario=sessao["usuario"],
            acao="BASE_PROCESSADA",
            varejista=nome_varejista,
            banco=sessao["banco"],
            detalhe=(
                f"linhas={resultado.get('total_linhas',0)} "
                f"lojas_ok={resultado.get('lojas_ok',0)} "
                f"pendencias={len(novas_pendencias)}"
            ),
        )

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
    ft.run(main)
