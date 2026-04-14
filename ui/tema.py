import flet as ft

# ── Paleta Mavi ───────────────────────────────────────────────────────────────
TEAL = "#00d4b4"
TEAL_DIM = "#00a896"
BG = "#1a1a1a"
BG2 = "#222222"
BG3 = "#2a2a2a"
BORDER = "#333333"
TEXT = "#e8e8e8"
TEXT_MUTED = "#888888"
DANGER = "#e05555"
SUCCESS = "#00d4b4"
WARN = "#e0a030"

# ── Tema do app ───────────────────────────────────────────────────────────────
TEMA = ft.Theme(
    color_scheme_seed=TEAL,
    color_scheme=ft.ColorScheme(
        primary=TEAL,
        background=BG,
        surface=BG2,
        on_primary="#000000",
        on_background=TEXT,
        on_surface=TEXT,
    ),
)

# ── Helpers de estilo ─────────────────────────────────────────────────────────


def titulo_logo(size: int = 42) -> ft.Text:
    return ft.Text(
        "mavi",
        size=size,
        weight=ft.FontWeight.W_800,
        color=TEAL,
        italic=True,
        font_family="Segoe UI",
    )


def rodape() -> ft.Column:
    return ft.Column(
        [
            ft.Text("Copyright © 2025 MaviClick", size=11, color=TEXT_MUTED),
            ft.Text("Versão: v2.0.0", size=11, color=TEXT_MUTED),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=2,
    )


def btn_primario(texto: str, on_click=None, largura: int = 220) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        text=texto,
        on_click=on_click,
        width=largura,
        style=ft.ButtonStyle(
            color={
                ft.ControlState.DEFAULT: "#000000",
                ft.ControlState.HOVERED: "#000000",
            },
            bgcolor={
                ft.ControlState.DEFAULT: TEAL,
                ft.ControlState.HOVERED: TEAL_DIM,
            },
            shape=ft.RoundedRectangleBorder(radius=20),
            padding=ft.padding.symmetric(vertical=12, horizontal=24),
        ),
    )


def btn_outline(texto: str, on_click=None, largura: int = 220) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        text=texto,
        on_click=on_click,
        width=largura,
        style=ft.ButtonStyle(
            color={
                ft.ControlState.DEFAULT: TEAL,
                ft.ControlState.HOVERED: "#000000",
            },
            bgcolor={
                ft.ControlState.DEFAULT: "transparent",
                ft.ControlState.HOVERED: TEAL,
            },
            side=ft.BorderSide(color=TEAL, width=1),
            shape=ft.RoundedRectangleBorder(radius=20),
            padding=ft.padding.symmetric(vertical=12, horizontal=24),
        ),
    )


def campo_texto(label: str, senha: bool = False, valor: str = "") -> ft.TextField:
    return ft.TextField(
        label=label,
        password=senha,
        can_reveal_password=senha,
        value=valor,
        width=320,
        bgcolor=BG3,
        border_color=BORDER,
        focused_border_color=TEAL,
        label_style=ft.TextStyle(color=TEAL, size=12),
        text_style=ft.TextStyle(color=TEXT, size=14),
        border_radius=8,
        content_padding=ft.padding.symmetric(horizontal=14, vertical=12),
    )


def dropdown_estilo(label: str, opcoes: list[str], valor: str = "") -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=valor or None,
        options=[ft.dropdown.Option(o) for o in opcoes],
        width=320,
        bgcolor=BG3,
        border_color=BORDER,
        focused_border_color=TEAL,
        label_style=ft.TextStyle(color=TEAL, size=12),
        text_style=ft.TextStyle(color=TEXT, size=14),
        border_radius=8,
    )


def card(conteudo: list, padding: int = 20) -> ft.Container:
    return ft.Container(
        content=ft.Column(conteudo, spacing=12),
        bgcolor=BG2,
        border=ft.border.all(1, BORDER),
        border_radius=12,
        padding=padding,
    )


def tela_centralizada(conteudo: list) -> ft.Column:
    """Layout padrão das telas centralizadas (login, banco, módulos)."""
    return ft.Column(
        [
            ft.Container(expand=True),
            titulo_logo(),
            ft.Container(height=24),
            *conteudo,
            ft.Container(height=32),
            rodape(),
            ft.Container(expand=True),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )


def snackbar_sucesso(page: ft.Page, msg: str):
    page.snack_bar = ft.SnackBar(
        content=ft.Text(msg, color="#000000"),
        bgcolor=TEAL,
    )
    page.snack_bar.open = True
    page.update()


def snackbar_erro(page: ft.Page, msg: str):
    page.snack_bar = ft.SnackBar(
        content=ft.Text(msg, color=TEXT),
        bgcolor=DANGER,
    )
    page.snack_bar.open = True
    page.update()
