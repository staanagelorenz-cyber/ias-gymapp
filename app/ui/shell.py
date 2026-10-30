"""The signed-in window: a side menu with only the sections this user may open, and the open section."""
from typing import Callable

import flet as ft

from app.ui.audit import audit_view
from app.ui.common import Ctx, SESSION_ENDED
from app.ui.records import records_view
from app.ui.users import users_view

# (label, icon, permission needed to see it, how to build it)
SECTIONS = [
    ("Members", ft.Icons.PEOPLE, "member:read", lambda ctx: records_view(ctx, "members")),
    ("Payments", ft.Icons.PAYMENTS, "payment:read", lambda ctx: records_view(ctx, "payments")),
    ("Training plans", ft.Icons.FITNESS_CENTER, "plan:read", lambda ctx: records_view(ctx, "plans")),
    ("Users", ft.Icons.ADMIN_PANEL_SETTINGS, "user:manage", users_view),
    ("Audit log", ft.Icons.RECEIPT_LONG, "audit:read", audit_view),
]


def shell_view(page: ft.Page, svc, token: str, on_logout: Callable[[str], None]) -> ft.Control:
    """Builds the menu from the service's answers. If the session is no longer valid, back to login."""
    try:
        me = svc.whoami(token)
    except svc.AuthError:
        on_logout(SESSION_ENDED)
        return ft.Container()

    def logout(message=""):
        try:
            svc.logout(token)
        finally:
            on_logout(message)

    ctx = Ctx(page, svc, token, logout)
    visible = [s for s in SECTIONS if svc.can(token, s[2])]
    content = ft.Container(expand=True, padding=20)

    def open_section(index):
        content.content = visible[index][3](ctx) if visible else ft.Text("Your account has no sections yet.")
        page.update()

    rail = ft.NavigationRail(
        selected_index=0, label_type=ft.NavigationRailLabelType.ALL, min_width=100,
        destinations=[ft.NavigationRailDestination(icon=icon, label=label) for label, icon, _, _ in visible],
        on_change=lambda e: open_section(e.control.selected_index),
        trailing=ft.Column([
            ft.Text(me["username"], size=12),
            ft.Text(", ".join(me["roles"]), size=11, color=ft.Colors.GREY_400),
            ft.TextButton("Sign out", icon=ft.Icons.LOGOUT, on_click=lambda e: logout()),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4))

    open_section(0)
    return ft.Row([rail, ft.VerticalDivider(width=1), content], expand=True)
