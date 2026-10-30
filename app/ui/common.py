"""Shared pieces for every screen: the session context, safe service calls, messages and dialogs.

The interface never decides who may do what. It only calls the service layer, which checks the
permission, and turns the service's answer into a short message for the user.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

import flet as ft

GENERIC_ERROR = "Something went wrong. Please try again."
DENIED = "You don't have permission to do that."
SESSION_ENDED = "Your session ended. Please sign in again."


@dataclass
class Ctx:
    """What every screen needs: the page, the service layer, the signed-in token, and logout.

    `ended` turns True once the session has ended, so a screen that is still being built knows
    not to put itself on the page after the sign-in screen replaced it.
    """

    page: ft.Page
    svc: object
    token: str
    on_logout: Callable[[str], None]
    ended: bool = field(default=False)

    def logout(self, message: str = "") -> None:
        """End the session once and go back to the sign-in screen."""
        if self.ended:
            return
        self.ended = True
        try:
            self.svc.logout(self.token)
        except Exception:  # the token may already be dead; signing out must still finish
            pass
        self.on_logout(message)


def toast(page: ft.Page, message: str) -> None:
    """Show a short message at the bottom of the window."""
    page.show_dialog(ft.SnackBar(ft.Text(message)))


def call(ctx: Ctx, fn: Callable, *args, done: str = "") -> tuple[bool, object]:
    """Run one service call. Returns (True, result) when it worked, (False, None) when it failed.

    Every failure becomes a short, safe message. Details of unexpected errors are never shown
    (no stack traces or table names: requirement S8); the service layer logs them.
    """
    try:
        result = fn(*args)
    except ctx.svc.AuthError:
        ctx.logout(SESSION_ENDED)  # expired token, or the user was deactivated meanwhile
        return False, None
    except ctx.svc.PermissionDenied:
        toast(ctx.page, DENIED)
        return False, None
    except ValueError as err:  # the service writes validation messages to be safe to show
        toast(ctx.page, str(err))
        return False, None
    except Exception:  # fail closed: refuse quietly rather than show internals
        toast(ctx.page, GENERIC_ERROR)
        return False, None
    if done:
        toast(ctx.page, done)
    return True, result


def can(ctx: Ctx, permission: str) -> bool:
    """Whether to SHOW a button or section. A convenience only: the service checks again."""
    ok, allowed = call(ctx, ctx.svc.can, ctx.token, permission)
    return ok and bool(allowed)


def close(page: ft.Page) -> None:
    """Close the open dialog. A toast also counts as a dialog in Flet, so any toast shown on
    top of it (for example after a rejected save) is closed first."""
    while isinstance(page.pop_dialog(), ft.SnackBar):
        pass


def form_dialog(
    page: ft.Page,
    title: str,
    fields: list[ft.Control],
    on_save: Callable[[], bool],
    save_text: str = "Save",
) -> None:
    """A dialog with fields and Cancel / Save. on_save returns True when the dialog may close,
    so a rejected value keeps everything the user typed."""

    def save(e):
        """Close only after the service accepted the change."""
        if on_save():
            close(page)

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Column(fields, tight=True, spacing=12, width=420),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close(page)),
                ft.FilledButton(save_text, on_click=save),
            ],
        )
    )


def confirm_with_password(
    page: ft.Page, title: str, message: str, on_confirm: Callable[[str], bool]
) -> None:
    """Sensitive actions (role changes, deactivation, password resets) ask for the password
    again. The service checks it; the screen only collects it."""
    password = ft.TextField(label="Your password", password=True, can_reveal_password=True)
    form_dialog(
        page,
        title,
        [ft.Text(message), password],
        lambda: on_confirm(password.value or ""),
        save_text="Confirm",
    )


def screen(title: str, body: ft.Control, *actions: ft.Control) -> ft.Control:
    """A section: a title row with optional buttons, and the body under it."""
    return ft.Column(
        [
            ft.Row(
                [ft.Text(title, size=22, weight=ft.FontWeight.BOLD), *actions],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            body,
        ],
        expand=True,
    )


def scroll_body() -> ft.Column:
    """The scrolling area a section puts its table in."""
    return ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)


def show_table(
    ctx: Ctx,
    body: ft.Column,
    fetch: Callable[[], tuple[bool, object]],
    headers: list[str],
    row: Callable[[dict], list[ft.Control]],
) -> None:
    """Load rows from the service and show them as a table, or "Nothing to show."."""
    if ctx.ended:
        return
    ok, rows = fetch()
    if ctx.ended:  # the call ended the session; the sign-in screen is already showing
        return
    if not ok or not rows:
        body.controls = [ft.Text("Nothing to show.")]
    else:
        body.controls = [
            ft.DataTable(
                columns=[ft.DataColumn(ft.Text(h)) for h in headers],
                rows=[ft.DataRow(cells=[ft.DataCell(c) for c in row(r)]) for r in rows],
            )
        ]
    ctx.page.update()


def dropdown(label: str, choices: list[str], value: str | None = None) -> ft.Dropdown:
    """A dropdown whose keys and labels are the same strings."""
    return ft.Dropdown(
        label=label, value=value, options=[ft.DropdownOption(c, c) for c in choices]
    )
