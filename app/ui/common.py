"""Shared pieces for every screen: the session context, safe service calls, messages and dialogs.

The interface never decides who may do what. It only calls the service layer, which checks the
permission, and turns the service's answer into a short message for the user.
"""
from dataclasses import dataclass
from typing import Callable

import flet as ft

GENERIC_ERROR = "Something went wrong. Please try again."
DENIED = "You don't have permission to do that."
SESSION_ENDED = "Your session ended. Please sign in again."


@dataclass
class Ctx:
    """What every screen needs: the page, the service layer, the signed-in token, and logout."""
    page: ft.Page
    svc: object
    token: str
    logout: Callable[[str], None]


def toast(page: ft.Page, message: str) -> None:
    """Show a short message at the bottom of the window."""
    page.show_dialog(ft.SnackBar(ft.Text(message)))


def call(ctx: Ctx, fn, *args, done: str = ""):
    """Run one service call and turn every failure into a short, safe message.

    Returns the service's result, or None when it failed. Details of unexpected errors are never
    shown (no stack traces or table names: requirement S8); the service layer logs them.
    """
    try:
        result = fn(*args)
    except ctx.svc.AuthError:
        ctx.logout(SESSION_ENDED)  # expired token or a user deactivated meanwhile: back to login
        return None
    except ctx.svc.PermissionDenied:
        toast(ctx.page, DENIED)
        return None
    except ValueError as err:  # validation messages from the service are written to be safe to show
        toast(ctx.page, str(err))
        return None
    except Exception:  # fail closed: refuse quietly rather than show internals
        toast(ctx.page, GENERIC_ERROR)
        return None
    if done:
        toast(ctx.page, done)
    return True if result is None else result


def close(page: ft.Page) -> None:
    """Close the open dialog."""
    page.pop_dialog()


def form_dialog(page: ft.Page, title: str, fields: list[ft.Control], on_save: Callable[[], None],
                save_text: str = "Save") -> None:
    """A dialog with some fields and Cancel / Save buttons. on_save reads the fields itself."""
    page.show_dialog(ft.AlertDialog(
        modal=True, title=ft.Text(title),
        content=ft.Column(fields, tight=True, spacing=12, width=420),
        actions=[ft.TextButton("Cancel", on_click=lambda e: close(page)),
                 ft.FilledButton(save_text, on_click=lambda e: on_save())]))


def confirm_with_password(page: ft.Page, title: str, message: str, on_confirm: Callable[[str], None]) -> None:
    """Sensitive actions (role changes, deactivation, password resets) ask for the password again.
    The service checks it; the screen only collects it."""
    password = ft.TextField(label="Your password", password=True, can_reveal_password=True)

    def go():
        close(page)
        on_confirm(password.value or "")
    form_dialog(page, title, [ft.Text(message), password], go, save_text="Confirm")
