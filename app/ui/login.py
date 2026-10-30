"""Sign-in screen."""
from typing import Callable

import flet as ft

from app.ui.common import GENERIC_ERROR


def login_view(svc, on_success: Callable[[str], None], notice: str = "") -> ft.Control:
    """Username and password. Shows exactly the message the service gives for a failed login, which
    is the same for an unknown user, a wrong password, a locked and an inactive account (G2)."""
    username = ft.TextField(label="Username", autofocus=True)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True)
    message = ft.Text(notice, color=ft.Colors.AMBER)

    def submit(e=None):
        try:
            token = svc.login((username.value or "").strip(), password.value or "")
        except svc.AuthError as err:
            message.value = str(err)
        except Exception:  # never show internals on the sign-in screen
            message.value = GENERIC_ERROR
        else:
            on_success(token)
            return
        password.value = ""  # don't leave a wrong password sitting in the box
        message.update()
        password.update()

    password.on_submit = submit
    return ft.Container(
        ft.Column([
            ft.Text("AWXCEND Gym Access", size=26, weight=ft.FontWeight.BOLD),
            ft.Text("Sign in with the account your administrator gave you.", color=ft.Colors.GREY_400),
            username, password, message,
            ft.FilledButton("Sign in", on_click=submit, width=320),
        ], spacing=14, width=320, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        alignment=ft.Alignment.CENTER, expand=True)
