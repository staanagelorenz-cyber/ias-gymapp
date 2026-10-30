"""Entry point.

    python -m app.main            the real app (needs app/services.py from the backend member)
    python -m app.main --preview  the screens with in-memory preview data (tests/fake_services.py)
"""
import sys

import flet as ft

from app.ui.login import login_view
from app.ui.shell import shell_view


def load_services(preview: bool):
    """The real service layer, or the preview stub while the backend is being written."""
    if preview:
        from tests.fake_services import FakeServices
        return FakeServices()
    from app import services  # written by the backend member
    return services


def build(page: ft.Page, svc) -> None:
    """Show the sign-in screen, and swap to the signed-in window after a successful login."""
    page.title = "AWXCEND Gym Access"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)

    def show_login(notice: str = ""):
        page.controls[:] = [login_view(svc, show_shell, notice)]
        page.update()

    def show_shell(token: str):
        page.controls[:] = [shell_view(page, svc, token, show_login)]
        page.update()

    show_login()


if __name__ == "__main__":
    services = load_services("--preview" in sys.argv)
    ft.run(lambda page: build(page, services))
