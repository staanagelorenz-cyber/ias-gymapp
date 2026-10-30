"""Entry point: python -m app.main

The screens use the real service layer, app/services.py (written by the backend member). To see
the screens with in-memory preview data instead, run python -m tests.preview.
"""

import flet as ft

from app.ui.login import login_view
from app.ui.shell import shell_view


def build(page: ft.Page, svc: object) -> None:
    """Show the sign-in screen, and swap to the signed-in window after a successful login."""
    page.title = "AWXCEND Gym Access"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)

    def show_login(notice: str = "") -> None:
        """Close any open dialog and show the sign-in screen, with an optional notice."""
        while page.pop_dialog():
            pass
        page.controls[:] = [login_view(svc, show_shell, notice)]
        page.update()

    def show_shell(token: str) -> None:
        """Show the signed-in window, unless the session ended while it was being built."""
        window = shell_view(page, svc, token, show_login)
        if window is not None:
            page.controls[:] = [window]
            page.update()

    show_login()


def main() -> None:
    """Start the real app with the real service layer."""
    from app import services  # imported here so the screens can be tested without it

    ft.run(lambda page: build(page, services))


if __name__ == "__main__":
    main()
