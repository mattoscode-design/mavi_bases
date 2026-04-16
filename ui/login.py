import flet as ft
import hashlib
import hmac
import json
from pathlib import Path
from ui import tema

_USUARIOS_PATH = Path(__file__).parent.parent / "security" / "usuarios.json"
_SALT = "mavi_salt_2026"


def _verificar_senha(usuario: str, senha: str) -> bool:
    """Verifica senha usando PBKDF2-SHA256. Nunca compara texto puro."""
    try:
        dados = json.loads(_USUARIOS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return False
    hash_salvo = dados.get(usuario)
    if not hash_salvo:
        return False
    hash_tentativa = hashlib.pbkdf2_hmac(
        "sha256", senha.encode(), _SALT.encode(), 100_000
    ).hex()
    # comparação em tempo constante para evitar timing attack
    return hmac.compare_digest(hash_tentativa, hash_salvo)


def adicionar_usuario(usuario: str, senha: str):
    """Adiciona ou atualiza um usuário no arquivo de credenciais."""
    try:
        dados = json.loads(_USUARIOS_PATH.read_text(encoding="utf-8"))
    except Exception:
        dados = {}
    dados[usuario] = hashlib.pbkdf2_hmac(
        "sha256", senha.encode(), _SALT.encode(), 100_000
    ).hex()
    _USUARIOS_PATH.write_text(
        json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
    )


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

        if not _verificar_senha(usuario, senha):
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
