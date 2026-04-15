import flet as ft
from ui import tema

USUARIOS = {
    "mavi_gabriel": "mavi2025",
    "admin": "admin123",
}


def tela_login(page: ft.Page, on_sucesso):
    inp_usuario = tema.campo_texto("Usuário")
    inp_senha = tema.campo_texto("Senha", senha=True)
    txt_erro = ft.Text("", color=tema.DANGER, size=13, visible=False)
    btn = tema.btn_primario("Entrar", largura=320)

    def entrar(e):
        usuario = inp_usuario.value.strip()
        senha = inp_senha.value

        if not usuario or not senha:
            txt_erro.value = "Preencha usuário e senha."
            txt_erro.visible = True
            page.update()
            return

        if USUARIOS.get(usuario) != senha:
            txt_erro.value = "Usuário ou senha incorretos."
            txt_erro.visible = True
            inp_senha.value = ""
            page.update()
            return

        txt_erro.visible = False
        on_sucesso(usuario)

    btn.on_click = entrar
    inp_usuario.on_submit = entrar
    inp_senha.on_submit = entrar

    return tema.tela_centralizada(
        [
            inp_usuario,
            inp_senha,
            txt_erro,
            ft.Container(height=4),
            btn,
        ]
    )
